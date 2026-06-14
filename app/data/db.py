"""
真实持久化层 —— SQLite(Python 标准库 sqlite3,零新依赖)
取代原 mock_db 的内存字典:报销单、权益余额、家属、审批流水都真写库。

设计要点:
  - 多租户:每条业务数据带 company 字段(sg/my/th/vn/id/hk/cn)
  - 线程安全:check_same_thread=False + 每次操作短连接,适配 uvicorn 多 worker
  - 幂等建表 + 自动播种:首次启动自动建表并灌入种子数据
  - 状态机:报销单 status ∈ {draft, pending, approved, rejected, paid}
"""
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

# ── 数据库文件路径(项目根 / data.db) ──
_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "claimgpt.db")
_LOCK = threading.Lock()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA foreign_keys=ON;")
    return c


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════
# 建表
# ═══════════════════════════════════════════════
_SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id           TEXT PRIMARY KEY,
    company      TEXT NOT NULL,
    name         TEXT NOT NULL,
    name_en      TEXT,
    dept         TEXT,
    level        TEXT,
    annual_quota REAL NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_types (
    code         TEXT NOT NULL,
    company      TEXT NOT NULL,
    name         TEXT NOT NULL,
    name_en      TEXT,
    grp          TEXT,
    limit_amt    REAL NOT NULL DEFAULT 0,
    need_invoice INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (code, company)
);

CREATE TABLE IF NOT EXISTS claims (
    id           TEXT PRIMARY KEY,
    company      TEXT NOT NULL,
    emp_id       TEXT NOT NULL,
    emp_name     TEXT,
    type_code    TEXT,
    type_name    TEXT,
    merchant     TEXT,
    amount       REAL NOT NULL DEFAULT 0,
    currency     TEXT NOT NULL DEFAULT 'CNY',
    amount_base  REAL NOT NULL DEFAULT 0,   -- 换算到公司本位币后的金额
    tax_amount   REAL NOT NULL DEFAULT 0,   -- 可抵扣税额
    invoice_date TEXT,
    tax_no       TEXT,
    note         TEXT,
    risk_score   INTEGER NOT NULL DEFAULT 0,
    risk_level   TEXT NOT NULL DEFAULT '低',
    risk_reasons TEXT,                       -- JSON 数组字符串
    status       TEXT NOT NULL DEFAULT 'pending',
    approver     TEXT,
    decided_at   TEXT,
    created_at   TEXT NOT NULL,
    source       TEXT DEFAULT 'chat',        -- chat / form / batch
    receipt_no   TEXT,                        -- 票据编号 (PM-9 重复票据检测)
    approval_chain TEXT,                       -- 审批链 JSON (workflow 引擎)
    cur_level    INTEGER NOT NULL DEFAULT 0,   -- 当前待审级别 (0=未进流程)
    batch_code   TEXT,                          -- 报销对接薪资批次号
    posted       INTEGER NOT NULL DEFAULT 0,    -- 是否已过账至薪资 (0/1)
    pay_calendar TEXT,                           -- 发薪日历
    posted_at    TEXT                            -- 过账时间
);

CREATE TABLE IF NOT EXISTS family (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id    TEXT NOT NULL,
    company   TEXT NOT NULL,
    relation  TEXT NOT NULL,
    name      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    company   TEXT,
    actor     TEXT,
    action    TEXT,
    target    TEXT,
    detail    TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claims_company ON claims(company);
CREATE INDEX IF NOT EXISTS idx_claims_status  ON claims(company, status);
CREATE INDEX IF NOT EXISTS idx_claims_emp     ON claims(emp_id);

-- ① LLM 平台配置(TokenHot / DeepSeek / Claude ...)
CREATE TABLE IF NOT EXISTS llm_providers (
    id          TEXT PRIMARY KEY,        -- tokenhot / deepseek / claude / custom-xxx
    name        TEXT NOT NULL,           -- 显示名
    kind        TEXT NOT NULL,           -- openai_compatible / anthropic
    base_url    TEXT NOT NULL,           -- API 基址
    api_key_enc TEXT,                    -- 加密后的 Key
    key_tail    TEXT,                    -- 末4位(展示用)
    status      TEXT NOT NULL DEFAULT 'inactive',  -- inactive / verified / active / error
    verify_msg  TEXT,                    -- 最近一次验证信息
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL,
    updated_at  TEXT
);

-- ② 模型清单(从平台拉取并认定的模型)
CREATE TABLE IF NOT EXISTS llm_models (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id  TEXT NOT NULL,
    model_id     TEXT NOT NULL,          -- 平台侧模型标识 deepseek-chat / claude-3-5-sonnet ...
    label        TEXT,                   -- 友好名
    capability   TEXT,                   -- chat / vision / reasoning(逗号分隔)
    enabled      INTEGER NOT NULL DEFAULT 1,   -- 是否认定启用
    is_default   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    UNIQUE(provider_id, model_id)
);

-- ③ Agent ↔ 模型 分发绑定
CREATE TABLE IF NOT EXISTS agent_bindings (
    agent_id     TEXT PRIMARY KEY,       -- ClaimMate / ApprovalCopilot / ... / _intent / _ocr / _policy
    provider_id  TEXT,
    model_id     TEXT,
    note         TEXT,
    updated_at   TEXT
);

-- ④ 通用模块自定义记录(报销组/权益/差旅申请等表格模块的"真新增"行)
--    用 JSON 存一行的所有列,前端按 module_id 渲染。让所有表格模块都能真实增删。
CREATE TABLE IF NOT EXISTS module_records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id  TEXT NOT NULL,            -- claim_group / entitlement / exchange / my_travel_req ...
    company    TEXT NOT NULL,
    payload    TEXT NOT NULL,            -- JSON: {列名: 值, ...}
    created_at TEXT NOT NULL,
    created_by TEXT DEFAULT '当前用户'
);
CREATE INDEX IF NOT EXISTS idx_modrec ON module_records(module_id, company);

-- ⑤ 余额调整流水(增/减/转移 · 必填原因 · 全留痕)
CREATE TABLE IF NOT EXISTS balance_adjust (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    company    TEXT NOT NULL,
    emp_id     TEXT NOT NULL,
    emp_name   TEXT,
    kind       TEXT NOT NULL,           -- 增加 / 减少 / 转移
    amount     REAL NOT NULL,
    reason     TEXT NOT NULL,           -- 必填原因
    to_emp_id  TEXT,                    -- 转移目标
    to_emp_name TEXT,
    operator   TEXT,                    -- 操作人(角色)
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_baladj ON balance_adjust(company);
"""


# ── 各公司默认本位币(用于换算) ──
COMPANY_CURRENCY = {
    "sg": "SGD", "my": "MYR", "th": "THB", "vn": "VND",
    "id": "IDR", "hk": "HKD", "cn": "CNY",
}

# ── 报销类型种子(限额按本位币口径) ──
_SEED_CLAIM_TYPES = [
    ("MEAL", "餐饮费", "Meals", "日常", 200, 1),
    ("TAXI", "交通费", "Transport", "日常", 500, 1),
    ("HOTEL", "住宿费", "Hotel", "差旅", 800, 1),
    ("FLIGHT", "机票", "Flight", "差旅", 5000, 1),
    ("OFFICE", "办公用品", "Office", "日常", 1000, 1),
    ("TRAIN", "高铁/火车", "Train", "差旅", 2000, 1),
]

# ── 员工种子(每公司 3 人) ──
_SEED_EMP_TEMPLATE = [
    ("张伟", "Wei Zhang", "技术部", "P7", 30000, 8600),
    ("李娜", "Na Li", "市场部", "P6", 25000, 19200),
    ("王芳", "Fang Wang", "财务部", "P5", 20000, 3400),
]

# ── 待审批报销单种子(每公司若干) ──
_SEED_CLAIMS_TEMPLATE = [
    ("张伟", "MEAL", "餐饮费", "海底捞火锅", 186, "团队聚餐"),
    ("李娜", "FLIGHT", "机票", "携程机票", 4200, "上海出差"),
    ("王芳", "HOTEL", "住宿费", "全季酒店", 1500, "超标准2晚"),
    ("张伟", "TAXI", "交通费", "滴滴出行", 88, "打车"),
    ("李娜", "MEAL", "餐饮费", "客户宴请", 980, "单笔超限"),
]


def _migrate(c: sqlite3.Connection) -> None:
    """轻量迁移:为老库补充审批流/对接薪资新列 (列已存在则忽略)。"""
    cols = {r["name"] for r in c.execute("PRAGMA table_info(claims)").fetchall()}
    adds = [
        ("receipt_no", "TEXT"), ("approval_chain", "TEXT"),
        ("cur_level", "INTEGER NOT NULL DEFAULT 0"), ("batch_code", "TEXT"),
        ("posted", "INTEGER NOT NULL DEFAULT 0"), ("pay_calendar", "TEXT"),
        ("posted_at", "TEXT"),
    ]
    for name, ddl in adds:
        if name not in cols:
            try:
                c.execute(f"ALTER TABLE claims ADD COLUMN {name} {ddl}")
            except sqlite3.OperationalError:
                pass
    c.commit()


def find_duplicate_receipt(company: str, emp_id: str, receipt_no: str,
                           invoice_date: str, amount: float,
                           type_code: str) -> dict | None:
    """PM-9 重复票据检测: 同员工+票据号+日期+金额+类型 唯一。"""
    if not receipt_no:
        return None
    return _one(
        "SELECT id,amount,invoice_date FROM claims WHERE company=? AND emp_id=? "
        "AND receipt_no=? AND invoice_date=? AND ABS(amount-?)<0.01 AND type_code=? "
        "AND status!='rejected' LIMIT 1",
        (company, emp_id, receipt_no, invoice_date, amount, type_code))


def approved_total(company: str, emp_id: str, type_code: str) -> float:
    """该员工该类型 已批准+待批 的累计金额 (限额上限防护)。"""
    r = _one(
        "SELECT COALESCE(SUM(amount_base),0) AS s FROM claims WHERE company=? "
        "AND emp_id=? AND type_code=? AND status IN ('approved','pending','posted')",
        (company, emp_id, type_code))
    return float(r["s"]) if r else 0.0


def init_db(force_seed: bool = False) -> None:
    """建表 + 首次播种。已存在数据则跳过播种。"""
    with _LOCK:
        c = _conn()
        try:
            c.executescript(_SCHEMA)
            c.commit()
            _migrate(c)   # 老库补列 (审批流 / 报销对接薪资)
            n = c.execute("SELECT COUNT(*) AS n FROM employees").fetchone()["n"]
            if n == 0 or force_seed:
                if force_seed:
                    for tb in ("claims", "family", "claim_types", "employees", "audit_log"):
                        c.execute(f"DELETE FROM {tb}")
                _seed(c)
                c.commit()
        finally:
            c.close()


def _seed(c: sqlite3.Connection) -> None:
    from app.data import calc  # 延迟导入,避免循环
    now = _now()
    for company in COMPANY_CURRENCY:
        cur = COMPANY_CURRENCY[company]
        # 员工
        for i, (name, name_en, dept, lvl, quota, used) in enumerate(_SEED_EMP_TEMPLATE, 1):
            emp_id = f"{company.upper()}{i:03d}"
            c.execute(
                "INSERT OR IGNORE INTO employees(id,company,name,name_en,dept,level,annual_quota,created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (emp_id, company, name, name_en, dept, lvl, quota, now),
            )
        # 报销类型
        for code, name, name_en, grp, limit_amt, need_inv in _SEED_CLAIM_TYPES:
            c.execute(
                "INSERT OR IGNORE INTO claim_types(code,company,name,name_en,grp,limit_amt,need_invoice)"
                " VALUES(?,?,?,?,?,?,?)",
                (code, company, name, name_en, grp, limit_amt, need_inv),
            )
        # 家属(给第一个员工)
        emp1 = f"{company.upper()}001"
        c.execute("INSERT INTO family(emp_id,company,relation,name) VALUES(?,?,?,?)",
                  (emp1, company, "配偶", "刘敏"))
        c.execute("INSERT INTO family(emp_id,company,relation,name) VALUES(?,?,?,?)",
                  (emp1, company, "子女", "张小宝"))
        # 待审批报销单(真实经过计算引擎跑一遍)
        emp_map = {name: f"{company.upper()}{i:03d}" for i, (name, *_rest) in enumerate(_SEED_EMP_TEMPLATE, 1)}
        for j, (emp_name, tcode, tname, merchant, amount, note) in enumerate(_SEED_CLAIMS_TEMPLATE, 1):
            limit_amt = next((t[4] for t in _SEED_CLAIM_TYPES if t[0] == tcode), 0)
            base = calc.to_base_currency(amount, cur, cur)  # 本币种 → 本币种 = 原值
            tax = calc.deductible_tax(base, company)
            risk = calc.risk_score(amount, limit_amt, exceed=amount > limit_amt)
            cid = f"C{company.upper()}{datetime.now().strftime('%Y%m')}{j:03d}"
            c.execute(
                "INSERT OR IGNORE INTO claims(id,company,emp_id,emp_name,type_code,type_name,merchant,"
                "amount,currency,amount_base,tax_amount,invoice_date,note,risk_score,risk_level,"
                "risk_reasons,status,created_at,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, company, emp_map.get(emp_name, emp1), emp_name, tcode, tname, merchant,
                 amount, cur, base, tax, now[:10], note, risk["score"], risk["level"],
                 __import__("json").dumps(risk["reasons"], ensure_ascii=False), "pending", now, "seed"),
            )


# ═══════════════════════════════════════════════
# 通用查询
# ═══════════════════════════════════════════════
def _rows(sql: str, params: tuple = ()) -> list[dict]:
    c = _conn()
    try:
        return [dict(r) for r in c.execute(sql, params).fetchall()]
    finally:
        c.close()


def _one(sql: str, params: tuple = ()) -> dict | None:
    c = _conn()
    try:
        r = c.execute(sql, params).fetchone()
        return dict(r) if r else None
    finally:
        c.close()


def _exec(sql: str, params: tuple = ()) -> int:
    with _LOCK:
        c = _conn()
        try:
            cur = c.execute(sql, params)
            c.commit()
            return cur.lastrowid
        finally:
            c.close()


# ═══════════════════════════════════════════════
# 业务方法
# ═══════════════════════════════════════════════
def get_employee(emp_id: str | None = None, company: str = "sg") -> dict | None:
    if emp_id:
        return _one("SELECT * FROM employees WHERE id=?", (emp_id,))
    return _one("SELECT * FROM employees WHERE company=? ORDER BY id LIMIT 1", (company,))


def get_balance(emp_id: str | None = None, company: str = "sg") -> dict:
    """真实余额 = 年度额度 - 已批准/已支付报销之和。"""
    emp = get_employee(emp_id, company)
    if not emp:
        return {"name": "—", "annual": 0, "used": 0, "remaining": 0, "level": "—", "dept": "—"}
    used_row = _one(
        "SELECT COALESCE(SUM(amount_base),0) AS used FROM claims "
        "WHERE emp_id=? AND status IN('approved','paid')", (emp["id"],))
    used = round(used_row["used"], 2) if used_row else 0
    return {
        "id": emp["id"], "name": emp["name"], "name_en": emp.get("name_en"),
        "dept": emp["dept"], "level": emp["level"],
        "annual": emp["annual_quota"], "used": used,
        "remaining": round(emp["annual_quota"] - used, 2),
        "currency": COMPANY_CURRENCY.get(company, "CNY"),
    }


def get_claim_types(company: str = "sg") -> list[dict]:
    rows = _rows("SELECT * FROM claim_types WHERE company=? ORDER BY code", (company,))
    if not rows:  # 兜底:任意公司模板
        rows = _rows("SELECT * FROM claim_types LIMIT 6")
    return rows


def get_claim_type(code: str, company: str = "sg") -> dict | None:
    if not code:
        return None
    # 精确:code / name / name_en
    hit = (_one("SELECT * FROM claim_types WHERE code=? AND company=?", (code, company))
           or _one("SELECT * FROM claim_types WHERE name=? AND company=?", (code, company))
           or _one("SELECT * FROM claim_types WHERE name_en=? AND company=?", (code, company)))
    if hit:
        return hit
    # 模糊:类别词互含(如 OCR 出"餐饮" 匹配类型"餐饮费"),双向 LIKE
    key = str(code).strip()
    return _one(
        "SELECT * FROM claim_types WHERE company=? AND (name LIKE ? OR ? LIKE '%'||name||'%' "
        "OR name_en LIKE ?) LIMIT 1",
        (company, f"%{key}%", key, f"%{key}%"))


def create_claim_type(company: str, code: str, name: str, name_en: str = "",
                      grp: str = "日常", limit_amt: float = 0,
                      need_invoice: bool = True) -> dict:
    """新增报销类型(真写库)。code 在同公司内唯一。"""
    code = (code or "").strip().upper()
    name = (name or "").strip()
    if not code or not name:
        raise ValueError("编码与名称必填 / code & name required")
    if _one("SELECT 1 FROM claim_types WHERE code=? AND company=?", (code, company)):
        raise ValueError(f"类型编码已存在 / code exists: {code}")
    _exec(
        "INSERT INTO claim_types(code,company,name,name_en,grp,limit_amt,need_invoice)"
        " VALUES(?,?,?,?,?,?,?)",
        (code, company, name, name_en or name, grp or "日常",
         float(limit_amt or 0), 1 if need_invoice else 0))
    log(company, "当前用户", "新增报销类型", code, f"{name} 限额{limit_amt}")
    return get_claim_type(code, company)


def update_claim_type(company: str, code: str, **fields) -> dict | None:
    """更新报销类型部分字段(name/name_en/grp/limit_amt/need_invoice)。"""
    code = (code or "").strip().upper()
    allowed = {"name", "name_en", "grp", "limit_amt", "need_invoice"}
    sets, params = [], []
    for k, v in fields.items():
        if k in allowed and v is not None:
            if k == "need_invoice":
                v = 1 if v else 0
            if k == "limit_amt":
                v = float(v)
            sets.append(f"{k}=?")
            params.append(v)
    if not sets:
        return get_claim_type(code, company)
    params += [code, company]
    _exec(f"UPDATE claim_types SET {','.join(sets)} WHERE code=? AND company=?", tuple(params))
    log(company, "当前用户", "更新报销类型", code, str(fields))
    return get_claim_type(code, company)


def delete_claim_type(company: str, code: str) -> bool:
    """删除报销类型。已被报销单引用则拒绝。"""
    code = (code or "").strip().upper()
    used = _one("SELECT COUNT(*) AS n FROM claims WHERE company=? AND type_code=?", (company, code))
    if used and used["n"] > 0:
        raise ValueError(f"已有 {used['n']} 笔报销引用该类型,不可删除 / referenced by claims")
    _exec("DELETE FROM claim_types WHERE code=? AND company=?", (code, company))
    log(company, "当前用户", "删除报销类型", code, "")
    return True


# ═══════════════════════════════════════════════
# 余额调整(增/减/转移 · 必填原因 · 全留痕)
# ═══════════════════════════════════════════════
def adjust_balance(company: str, emp_id: str | None, kind: str, amount: float,
                   reason: str, to_emp_id: str | None = None,
                   operator: str = "finance") -> dict:
    """调整员工年度额度:增加/减少/转移。写流水留痕。"""
    emp = get_employee(emp_id, company)
    if not emp:
        raise ValueError("员工不存在 / employee not found")
    amount = float(amount)
    quota = float(emp.get("annual_quota", 0))
    to_emp = None
    if kind == "增加":
        new_quota = quota + amount
        _exec("UPDATE employees SET annual_quota=? WHERE id=?", (new_quota, emp["id"]))
    elif kind == "减少":
        if amount > quota:
            raise ValueError(f"减少额 {amount} 超过当前额度 {quota} / exceeds quota")
        new_quota = quota - amount
        _exec("UPDATE employees SET annual_quota=? WHERE id=?", (new_quota, emp["id"]))
    elif kind == "转移":
        to_emp = get_employee(to_emp_id, company)
        if not to_emp:
            raise ValueError("转移目标员工不存在 / target employee not found")
        if amount > quota:
            raise ValueError(f"转移额 {amount} 超过当前额度 {quota} / exceeds quota")
        _exec("UPDATE employees SET annual_quota=? WHERE id=?", (quota - amount, emp["id"]))
        _exec("UPDATE employees SET annual_quota=? WHERE id=?",
              (float(to_emp.get("annual_quota", 0)) + amount, to_emp["id"]))
    else:
        raise ValueError(f"未知调整类型 {kind}")
    _exec(
        "INSERT INTO balance_adjust(company,emp_id,emp_name,kind,amount,reason,"
        "to_emp_id,to_emp_name,operator,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (company, emp["id"], emp.get("name"), kind, amount, reason,
         to_emp_id if to_emp else None, to_emp.get("name") if to_emp else None,
         operator, _now()))
    log(company, operator, f"余额调整·{kind}", emp["id"], f"{amount} | {reason}")
    return {"emp": emp.get("name"), "kind": kind, "amount": amount,
            "balance": get_balance(emp["id"], company),
            "to_emp": to_emp.get("name") if to_emp else None}


def balance_history(company: str = "sg", emp_id: str | None = None) -> list[dict]:
    sql = "SELECT * FROM balance_adjust WHERE company=?"
    params: list[Any] = [company]
    if emp_id:
        sql += " AND emp_id=?"
        params.append(emp_id)
    sql += " ORDER BY id DESC LIMIT 50"
    return _rows(sql, tuple(params))


# ═══════════════════════════════════════════════
# 通用模块自定义记录(让所有表格模块都能真新增/删除)
# ═══════════════════════════════════════════════
def add_module_record(module_id: str, company: str, payload: dict,
                      created_by: str = "当前用户") -> dict:
    rid = _exec(
        "INSERT INTO module_records(module_id,company,payload,created_at,created_by)"
        " VALUES(?,?,?,?,?)",
        (module_id, company, __import__("json").dumps(payload, ensure_ascii=False),
         _now(), created_by))
    log(company, created_by, "新增记录", module_id, str(payload)[:120])
    return {"id": rid, "module_id": module_id, "company": company,
            "payload": payload, "created_at": _now()}


def list_module_records(module_id: str, company: str = "sg") -> list[dict]:
    rows = _rows(
        "SELECT * FROM module_records WHERE module_id=? AND company=? ORDER BY id DESC",
        (module_id, company))
    out = []
    for r in rows:
        try:
            r["payload"] = __import__("json").loads(r["payload"])
        except Exception:
            r["payload"] = {}
        out.append(r)
    return out


def delete_module_record(rid: int, company: str = "sg") -> bool:
    rec = _one("SELECT * FROM module_records WHERE id=? AND company=?", (rid, company))
    if not rec:
        return False
    _exec("DELETE FROM module_records WHERE id=? AND company=?", (rid, company))
    log(company, "当前用户", "删除记录", rec["module_id"], f"#{rid}")
    return True


def list_claims(company: str = "sg", status: str | None = None,
                emp_id: str | None = None, limit: int = 100) -> list[dict]:
    sql = "SELECT * FROM claims WHERE company=?"
    params: list[Any] = [company]
    if status:
        sql += " AND status=?"
        params.append(status)
    if emp_id:
        sql += " AND emp_id=?"
        params.append(emp_id)
    sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
    params.append(limit)
    return _rows(sql, tuple(params))


def get_claim(claim_id: str) -> dict | None:
    return _one("SELECT * FROM claims WHERE id=?", (claim_id,))


def next_claim_id(company: str) -> str:
    n = _one("SELECT COUNT(*) AS n FROM claims WHERE company=?", (company,))["n"]
    return f"C{company.upper()}{datetime.now().strftime('%Y%m%d')}{n + 1:03d}"


def create_claim(data: dict) -> dict:
    """真实写入一条报销单,返回完整记录。"""
    cid = data.get("id") or next_claim_id(data.get("company", "sg"))
    now = _now()
    _exec(
        "INSERT INTO claims(id,company,emp_id,emp_name,type_code,type_name,merchant,amount,currency,"
        "amount_base,tax_amount,invoice_date,tax_no,note,risk_score,risk_level,risk_reasons,status,"
        "created_at,source,receipt_no,approval_chain,cur_level) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (cid, data.get("company", "sg"), data.get("emp_id", ""), data.get("emp_name", ""),
         data.get("type_code", ""), data.get("type_name", ""), data.get("merchant", ""),
         data.get("amount", 0), data.get("currency", "CNY"), data.get("amount_base", 0),
         data.get("tax_amount", 0), data.get("invoice_date", now[:10]), data.get("tax_no", ""),
         data.get("note", ""), data.get("risk_score", 0), data.get("risk_level", "低"),
         __import__("json").dumps(data.get("risk_reasons", []), ensure_ascii=False),
         data.get("status", "pending"), now, data.get("source", "chat"),
         data.get("receipt_no", ""),
         __import__("json").dumps(data.get("approval_chain", []), ensure_ascii=False),
         data.get("cur_level", 0)),
    )
    log(data.get("company", "sg"), data.get("emp_name", "员工"), "create_claim", cid,
        f"{data.get('type_name','')} {data.get('amount',0)} {data.get('currency','')}")
    return get_claim(cid)


def decide_claim(claim_id: str, status: str, approver: str = "审批副驾") -> dict | None:
    """审批:真改状态 + 留痕。status ∈ approved/rejected/paid"""
    now = _now()
    _exec("UPDATE claims SET status=?, approver=?, decided_at=? WHERE id=?",
          (status, approver, now, claim_id))
    cl = get_claim(claim_id)
    if cl:
        log(cl["company"], approver, f"claim_{status}", claim_id,
            f"{cl.get('type_name','')} {cl.get('amount',0)}")
    return cl


def batch_decide(company: str, status: str, risk_level: str | None = None,
                 approver: str = "审批副驾") -> int:
    """批量审批:把某风险等级的 pending 单据一次改状态,返回影响行数。"""
    now = _now()
    sql = "UPDATE claims SET status=?, approver=?, decided_at=? WHERE company=? AND status='pending'"
    params: list[Any] = [status, approver, now, company]
    if risk_level:
        sql += " AND risk_level=?"
        params.append(risk_level)
    with _LOCK:
        c = _conn()
        try:
            cur = c.execute(sql, tuple(params))
            c.commit()
            n = cur.rowcount
        finally:
            c.close()
    log(company, approver, f"batch_{status}", risk_level or "all", f"{n} 单")
    return n


# ════════════════ 审批流推进 (workflow 引擎落库) ════════════════
def save_chain(claim_id: str, chain: list, cur_level: int, status: str) -> dict | None:
    """把审批链状态机推进结果写回单据。"""
    import json
    now = _now()
    _exec("UPDATE claims SET approval_chain=?, cur_level=?, status=?, decided_at=? WHERE id=?",
          (json.dumps(chain, ensure_ascii=False), cur_level, status, now, claim_id))
    return get_claim(claim_id)


def advance_claim(claim_id: str, decision: str, by: str, comment: str = "") -> dict | None:
    """
    按 workflow 状态机推进一笔报销的审批链。
    decision ∈ approved | rejected | returned
    返回: {claim, overall, current_level, summary}
    """
    import json
    from app.core import workflow
    cl = get_claim(claim_id)
    if not cl:
        return None
    chain = json.loads(cl.get("approval_chain") or "[]")
    if not chain:
        # 老单据无链 → 即时构建一条 (按金额条件路由)
        chain = workflow.build_chain("claim", {"amount_base": cl.get("amount_base", 0)})
    res = workflow.advance(chain, decision, by, comment)
    overall = res["overall"]
    status = {"approved": "approved", "rejected": "rejected",
              "returned": "returned", "in_review": "pending"}[overall]
    cur_level = res["current_level"] or 0
    save_chain(claim_id, res["chain"], cur_level if overall == "in_review" else 0, status)
    log(cl["company"], by, f"wf_{overall}", claim_id,
        f"L{res.get('current_level')} {comment[:30]}")
    out = get_claim(claim_id)
    return {"claim": out, "overall": overall, "current_level": res["current_level"],
            "summary": workflow.chain_summary(res["chain"])}


# ════════════════ 报销对接薪资 (批次过账, 文档 流程3 第5步) ════════════════
def list_postable_claims(company: str) -> list[dict]:
    """获取所有 已批准 + 未过账 的报销单 (待对接薪资)。"""
    return _rows(
        "SELECT * FROM claims WHERE company=? AND status='approved' AND posted=0 "
        "ORDER BY decided_at", (company,))


def post_to_payroll(company: str, pay_calendar: str, by: str = "薪资管理员") -> dict:
    """
    报销对接处理: 把已批准+未过账的报销单批量过账至指定发薪日历。
    生成批次号, 标记 posted=1, 写入 batch_code / pay_calendar / posted_at。
    文档: 一旦已过账, 不能通过批量工作流取消。
    """
    rows = list_postable_claims(company)
    if not rows:
        return {"batch_code": None, "count": 0, "total": 0.0, "claims": []}
    batch = f"BATCH-{company.upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    now = _now()
    ids = [r["id"] for r in rows]
    total = round(sum(float(r["amount_base"]) for r in rows), 2)
    with _LOCK:
        c = _conn()
        try:
            for cid in ids:
                c.execute(
                    "UPDATE claims SET posted=1, status='posted', batch_code=?, "
                    "pay_calendar=?, posted_at=? WHERE id=?",
                    (batch, pay_calendar, now, cid))
            c.commit()
        finally:
            c.close()
    log(company, by, "post_to_payroll", batch,
        f"{len(ids)} 单 → {pay_calendar} 合计 {total}")
    return {"batch_code": batch, "count": len(ids), "total": total,
            "pay_calendar": pay_calendar, "claims": ids}


def list_batches(company: str) -> list[dict]:
    """已过账批次汇总 (供薪资对接面板查看)。"""
    return _rows(
        "SELECT batch_code, pay_calendar, posted_at, COUNT(*) AS cnt, "
        "ROUND(SUM(amount_base),2) AS total FROM claims "
        "WHERE company=? AND posted=1 GROUP BY batch_code ORDER BY posted_at DESC",
        (company,))


def get_family(emp_id: str | None = None, company: str = "sg") -> list[dict]:
    emp = get_employee(emp_id, company)
    if not emp:
        return []
    return _rows("SELECT relation,name FROM family WHERE emp_id=?", (emp["id"],))


def add_family(emp_id: str, company: str, relation: str, name: str) -> dict:
    _exec("INSERT INTO family(emp_id,company,relation,name) VALUES(?,?,?,?)",
          (emp_id, company, relation, name))
    return {"relation": relation, "name": name}


def claim_stats(company: str = "sg") -> dict:
    """统计本公司各状态/各风险数量与金额(供审批面板真实汇总)。"""
    rows = _rows("SELECT status,risk_level,COUNT(*) AS n,COALESCE(SUM(amount_base),0) AS amt "
                 "FROM claims WHERE company=? GROUP BY status,risk_level", (company,))
    stat = {"pending": 0, "approved": 0, "rejected": 0, "paid": 0,
            "risk": {"低": 0, "中": 0, "高": 0}, "total_amt": 0}
    for r in rows:
        stat[r["status"]] = stat.get(r["status"], 0) + r["n"]
        if r["status"] == "pending":
            stat["risk"][r["risk_level"]] = stat["risk"].get(r["risk_level"], 0) + r["n"]
        stat["total_amt"] += r["amt"]
    stat["total_amt"] = round(stat["total_amt"], 2)
    return stat


def log(company: str, actor: str, action: str, target: str, detail: str = "") -> None:
    _exec("INSERT INTO audit_log(company,actor,action,target,detail,created_at) VALUES(?,?,?,?,?,?)",
          (company, actor, action, target, detail, _now()))


def recent_audit(company: str = "sg", limit: int = 20) -> list[dict]:
    return _rows("SELECT * FROM audit_log WHERE company=? ORDER BY id DESC LIMIT ?", (company, limit))


# ═══════════════════════════════════════════════
# LLM 配置:Key 加密(对称混淆,生产可换 KMS/Fernet)
# ═══════════════════════════════════════════════
import base64
import hashlib

_KEY_SECRET = os.environ.get("CLAIMGPT_SECRET", "paydaes-claimgpt-2026-secret")


def _enc(plain: str) -> str:
    if not plain:
        return ""
    k = hashlib.sha256(_KEY_SECRET.encode()).digest()
    b = plain.encode()
    out = bytes(c ^ k[i % len(k)] for i, c in enumerate(b))
    return base64.b64encode(out).decode()


def _dec(enc: str) -> str:
    if not enc:
        return ""
    try:
        k = hashlib.sha256(_KEY_SECRET.encode()).digest()
        b = base64.b64decode(enc.encode())
        out = bytes(c ^ k[i % len(k)] for i, c in enumerate(b))
        return out.decode()
    except Exception:
        return ""


# ── 平台 Providers ──
def upsert_provider(pid: str, name: str, kind: str, base_url: str,
                    api_key: str | None = None) -> dict:
    now = _now()
    existing = _one("SELECT * FROM llm_providers WHERE id=?", (pid,))
    key_enc = _enc(api_key) if api_key else (existing["api_key_enc"] if existing else "")
    key_tail = api_key[-4:] if api_key else (existing["key_tail"] if existing else "")
    if existing:
        _exec("UPDATE llm_providers SET name=?,kind=?,base_url=?,api_key_enc=?,key_tail=?,updated_at=? WHERE id=?",
              (name, kind, base_url, key_enc, key_tail, now, pid))
    else:
        _exec("INSERT INTO llm_providers(id,name,kind,base_url,api_key_enc,key_tail,status,enabled,created_at,updated_at)"
              " VALUES(?,?,?,?,?,?,?,?,?,?)",
              (pid, name, kind, base_url, key_enc, key_tail, "inactive", 1, now, now))
    return get_provider(pid)


def get_provider(pid: str, with_key: bool = False) -> dict | None:
    p = _one("SELECT * FROM llm_providers WHERE id=?", (pid,))
    if not p:
        return None
    if with_key:
        p["api_key"] = _dec(p.get("api_key_enc", ""))
    p.pop("api_key_enc", None)
    return p


def list_providers() -> list[dict]:
    rows = _rows("SELECT id,name,kind,base_url,key_tail,status,verify_msg,enabled,created_at,updated_at FROM llm_providers ORDER BY created_at")
    return rows


def set_provider_status(pid: str, status: str, msg: str = "") -> None:
    _exec("UPDATE llm_providers SET status=?,verify_msg=?,updated_at=? WHERE id=?",
          (status, msg, _now(), pid))


def delete_provider(pid: str) -> None:
    _exec("DELETE FROM agent_bindings WHERE provider_id=?", (pid,))
    _exec("DELETE FROM llm_models WHERE provider_id=?", (pid,))
    _exec("DELETE FROM llm_providers WHERE id=?", (pid,))


# ── 模型 Models ──
def replace_models(provider_id: str, models: list[dict]) -> int:
    """用拉取到的模型列表覆盖该平台的模型(保留已有 enabled 状态)。"""
    now = _now()
    old = {m["model_id"]: m for m in list_models(provider_id)}
    with _LOCK:
        c = _conn()
        try:
            c.execute("DELETE FROM llm_models WHERE provider_id=?", (provider_id,))
            for m in models:
                mid = m.get("model_id") or m.get("id")
                if not mid:
                    continue
                prev = old.get(mid)
                enabled = prev["enabled"] if prev else 0
                c.execute(
                    "INSERT OR IGNORE INTO llm_models(provider_id,model_id,label,capability,enabled,is_default,created_at)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (provider_id, mid, m.get("label", mid), m.get("capability", "chat"),
                     enabled, 0, now))
            c.commit()
        finally:
            c.close()
    return len(models)


def list_models(provider_id: str | None = None, enabled_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM llm_models"
    params: list[Any] = []
    conds = []
    if provider_id:
        conds.append("provider_id=?")
        params.append(provider_id)
    if enabled_only:
        conds.append("enabled=1")
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY provider_id, model_id"
    return _rows(sql, tuple(params))


def set_model_enabled(model_pk: int, enabled: bool) -> None:
    _exec("UPDATE llm_models SET enabled=? WHERE id=?", (1 if enabled else 0, model_pk))


# ── Agent 分发绑定 ──
def set_binding(agent_id: str, provider_id: str | None, model_id: str | None, note: str = "") -> dict:
    now = _now()
    if _one("SELECT agent_id FROM agent_bindings WHERE agent_id=?", (agent_id,)):
        _exec("UPDATE agent_bindings SET provider_id=?,model_id=?,note=?,updated_at=? WHERE agent_id=?",
              (provider_id, model_id, note, now, agent_id))
    else:
        _exec("INSERT INTO agent_bindings(agent_id,provider_id,model_id,note,updated_at) VALUES(?,?,?,?,?)",
              (agent_id, provider_id, model_id, note, now))
    return get_binding(agent_id)


def get_binding(agent_id: str) -> dict | None:
    return _one("SELECT * FROM agent_bindings WHERE agent_id=?", (agent_id,))


def list_bindings() -> list[dict]:
    return _rows("SELECT * FROM agent_bindings")


def resolve_binding(agent_id: str) -> dict | None:
    """解析某 Agent 的可用调用配置(平台已激活 + 模型已启用),返回含明文 key。"""
    b = get_binding(agent_id)
    if not b or not b.get("provider_id"):
        return None
    p = get_provider(b["provider_id"], with_key=True)
    if not p or p.get("status") != "active" or not p.get("enabled"):
        return None
    return {
        "agent_id": agent_id, "provider_id": p["id"], "kind": p["kind"],
        "base_url": p["base_url"], "api_key": p.get("api_key", ""),
        "model_id": b.get("model_id"),
    }
