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
    source       TEXT DEFAULT 'chat'         -- chat / form / batch
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


def init_db(force_seed: bool = False) -> None:
    """建表 + 首次播种。已存在数据则跳过播种。"""
    with _LOCK:
        c = _conn()
        try:
            c.executescript(_SCHEMA)
            c.commit()
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
    return _one("SELECT * FROM claim_types WHERE code=? AND company=?", (code, company)) \
        or _one("SELECT * FROM claim_types WHERE name=? AND company=?", (code, company))


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
        "created_at,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (cid, data.get("company", "sg"), data.get("emp_id", ""), data.get("emp_name", ""),
         data.get("type_code", ""), data.get("type_name", ""), data.get("merchant", ""),
         data.get("amount", 0), data.get("currency", "CNY"), data.get("amount_base", 0),
         data.get("tax_amount", 0), data.get("invoice_date", now[:10]), data.get("tax_no", ""),
         data.get("note", ""), data.get("risk_score", 0), data.get("risk_level", "低"),
         __import__("json").dumps(data.get("risk_reasons", []), ensure_ascii=False),
         data.get("status", "pending"), now, data.get("source", "chat")),
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
