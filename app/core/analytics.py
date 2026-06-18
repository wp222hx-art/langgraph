"""
劳动力分析引擎 (Workforce Analytics Engine)
═══════════════════════════════════════════════════════════════
① AI 老板驾驶舱 与 ④ AI 异常稽查 的共享大脑。
一份分析引擎,两个出口:
  · build_overview()  —— 驾驶舱聚合: 企业总成本/HRDF/PCB/加班/部门分布 + 环比趋势
  · detect_anomalies() —— 异常稽查: 加班异常/报销异常/薪资跳变/总成本突增
  · explain_cost_change() —— AI 解读: 「这个月人力成本为什么涨了」归因分析

设计原则:
  · 数据源复用 payroll_data.compute_monthly(已含 Wave2 加班分级/按比例/HRDF/企业总成本)
  · 历史月度用确定性"伪历史"派生(基于真实当月做 ±波动),保证 Demo 可复现且趋势可解释
  · AI 解读为规则推理(零延迟),可平滑升级到 LLM(见 narrate 钩子)
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from app.data import payroll_data as P
from app.data import enterprise as E


# ── 公司 → 币种 / 规模 / 汇率映射(保证驾驶舱与公司体系逻辑一致)──
# 基准引擎产出为 MYR(payroll_data 全员为 MY 法定算法),
# 各公司按"真实员工规模"缩放总量、按"对 MYR 汇率"换算到本币,
# 使得「币种代名词」与「数值量级」严格保持逻辑关系(而非统一 RM)。
_BASE_HEADCOUNT = 5          # payroll_data 演示样本人数(MY 引擎基准)
_BASE_COMPANY_EMP = 256      # my 公司真实编制(缩放基准)

# 1 MYR ≈ ? 本币(用于把 MY 引擎金额换算到各公司本币,量级符合当地货币习惯)
_FX_TO_LOCAL = {
    "MYR": 1.0,
    "SGD": 0.31,     # 1 MYR ≈ 0.31 SGD
    "HKD": 1.74,     # 1 MYR ≈ 1.74 HKD
    "CNY": 1.55,     # 1 MYR ≈ 1.55 CNY(人民币)
    "THB": 7.6,      # 1 MYR ≈ 7.6 THB
    "VND": 5600.0,   # 1 MYR ≈ 5600 VND
    "IDR": 3550.0,   # 1 MYR ≈ 3550 IDR
}
# 货币显示符号(前缀代名词)
_CURRENCY_PREFIX = {
    "MYR": "RM", "SGD": "S$", "HKD": "HK$", "CNY": "¥",
    "THB": "฿", "VND": "₫", "IDR": "Rp",
}


def _company_meta(company: str) -> dict:
    """由公司 id 反查 {currency, employees, fx, prefix, name}。
    找不到则回退到 my(MYR)基准,保证永不崩。"""
    for g in E.GROUPS:
        for c in g["companies"]:
            if c["id"] == company:
                cur = c.get("currency", "MYR")
                return {
                    "company": company,
                    "currency": cur,
                    "employees": c.get("employees", _BASE_COMPANY_EMP),
                    "fx": _FX_TO_LOCAL.get(cur, 1.0),
                    "prefix": _CURRENCY_PREFIX.get(cur, cur + " "),
                    "name": c.get("name", company),
                    "country": c.get("country", "MY"),
                }
    # 回退(含 group 汇总视图)
    return {"company": company, "currency": "MYR", "employees": _BASE_COMPANY_EMP,
            "fx": 1.0, "prefix": "RM", "name": company, "country": "MY"}


def _currency_of(company: str) -> dict:
    """返回 {code, prefix} 供出口标注币种。"""
    m = _company_meta(company)
    return {"code": m["currency"], "prefix": m["prefix"]}


# ── 阈值常量(异常稽查规则)──
OT_HOURS_WARN = 40          # 单人月加班 > 40h 预警(MY 劳工法 104h/月为硬上限)
OT_HOURS_CRIT = 72          # > 72h 严重
OT_COST_RATIO_WARN = 0.30   # 加班费占基本工资 > 30% 预警
SALARY_JUMP_WARN = 0.15     # 薪资环比波动 > 15% 预警
SALARY_JUMP_CRIT = 0.30     # > 30% 严重
COST_SURGE_WARN = 0.10      # 企业总成本环比 > 10% 预警
CLAIM_RATIO_WARN = 0.50     # 报销占月收入 > 50% 预警


def _seed(key: str) -> float:
    """由字符串派生 0~1 的确定性伪随机(保证 Demo 可复现)。"""
    h = hashlib.md5(key.encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _month_label(offset: int, base: str = "2026-05") -> str:
    y, m = int(base[:4]), int(base[5:7])
    m -= offset
    while m <= 0:
        m += 12; y -= 1
    return f"{y}-{m:02d}"


# 需随"公司规模 + 汇率"缩放的金额型字段(headcount/比例/工时类不缩放)
_MONEY_KEYS = (
    "gross_total", "net_pay", "basic_pay", "ot_amount",
    "epf_er", "socso_er", "eis_er", "hrdf", "pcb",
    "employer_contrib", "total_cost",
)


def _company_snapshot(company: str = "my") -> list[dict]:
    """当月全员薪资快照(消费 Wave2 引擎)。
    按公司真实编制 + 本币汇率缩放,使每家公司产出"不同且与其规模/币种逻辑一致"的数据。
    """
    meta = _company_meta(company)
    # 规模放大:把 5 人样本放大到该公司真实编制量级
    head_scale = meta["employees"] / _BASE_HEADCOUNT
    fx = meta["fx"]
    # 公司特异确定性扰动(避免不同公司只是等比例放大,呈现各自结构差异)
    co_wobble = 0.90 + _seed(company + "co") * 0.20  # 0.90~1.10

    snap = []
    for e in P.PAYROLL_EMPLOYEES:
        row = P.compute_monthly(e)
        # 该员工的公司特异微扰(部门/个体差异)
        emp_w = 0.92 + _seed(company + str(row.get("emp_no", row.get("name", "")))) * 0.16
        factor = head_scale * fx * co_wobble * emp_w
        new = dict(row)
        for k in _MONEY_KEYS:
            if k in new and isinstance(new[k], (int, float)):
                new[k] = round(new[k] * factor, 2)
        # ot_detail 工时不缩放(工时是真实小时数,跨币种无意义),但加班金额已随 ot_amount 缩放
        snap.append(new)
    return snap


def _aggregate(snap: list[dict], company: str = "my") -> dict:
    """把全员快照聚合成公司级指标。
    headcount 用公司真实编制(snap 是样本结构、金额已放大到该编制量级)。
    """
    def s(k):
        return round(sum(x.get(k, 0) or 0 for x in snap), 2)
    headcount = _company_meta(company)["employees"]
    return {
        "headcount": headcount,
        "gross": s("gross_total"),
        "net": s("net_pay"),
        "basic": round(sum(x["basic_pay"] for x in snap), 2),
        "ot": s("ot_amount"),
        "epf_er": s("epf_er"), "socso_er": s("socso_er"), "eis_er": s("eis_er"),
        "hrdf": s("hrdf"),
        "pcb": s("pcb"),
        "employer_contrib": s("employer_contrib"),
        "total_cost": s("total_cost"),
    }


def _derive_history(current: dict, months: int = 6, base: str = "2026-05") -> list[dict]:
    """基于当月真实聚合派生确定性月度历史(供趋势图/环比)。
    最近一月=真实当月;往前各月按确定性系数缩放,模拟业务增长曲线。
    """
    series = []
    for i in range(months - 1, -1, -1):
        label = _month_label(i, base)
        if i == 0:
            row = {**current, "month": label}
        else:
            # 越往前规模略小(模拟逐月增长),并叠加确定性波动
            scale = 1.0 - i * 0.018 - (_seed(label + "scale") - 0.5) * 0.04
            row = {"month": label, "headcount": current["headcount"]}
            for k, v in current.items():
                if k == "headcount":
                    continue
                wobble = 1 + (_seed(label + k) - 0.5) * 0.06
                row[k] = round(v * scale * wobble, 2)
        series.append(row)
    return series


def _dept_breakdown(snap: list[dict], company: str = "my") -> list[dict]:
    """按部门聚合企业总成本(驾驶舱部门分布环图)。
    部门人头按公司真实编制等比放大(样本人数→真实编制)。
    """
    sample_n = len(snap) or 1
    real_head = _company_meta(company)["employees"]
    head_mul = real_head / sample_n  # 样本人头→真实编制
    buckets: dict[str, dict] = {}
    for x in snap:
        d = x.get("dept", "其他") or "其他"
        b = buckets.setdefault(d, {"dept": d, "_sample": 0, "total_cost": 0.0,
                                   "gross": 0.0, "ot": 0.0})
        b["_sample"] += 1
        b["total_cost"] += x["total_cost"]
        b["gross"] += x["gross_total"]
        b["ot"] += x["ot_amount"]
    out = [{"dept": b["dept"],
            "headcount": max(1, round(b["_sample"] * head_mul)),
            "total_cost": round(b["total_cost"], 2),
            "gross": round(b["gross"], 2), "ot": round(b["ot"], 2)}
           for b in buckets.values()]
    out.sort(key=lambda r: r["total_cost"], reverse=True)
    return out


# ════════════════ ① 驾驶舱聚合 ════════════════
def build_overview(company: str = "my", base_month: str = "2026-05") -> dict:
    snap = _company_snapshot(company)
    cur = _aggregate(snap, company)
    cur_meta = _currency_of(company)
    hist = _derive_history(cur, months=6, base=base_month)
    prev = hist[-2] if len(hist) >= 2 else cur

    def mom(k):  # 环比 month-over-month
        p = prev.get(k, 0) or 0
        c = cur.get(k, 0) or 0
        if p == 0:
            return 0.0
        return round((c - p) / p * 100, 1)

    kpis = {
        "total_cost": {"value": cur["total_cost"], "mom": mom("total_cost"), "label_zh": "企业总成本", "label_en": "Total Cost"},
        "gross":      {"value": cur["gross"], "mom": mom("gross"), "label_zh": "薪资总额", "label_en": "Gross Payroll"},
        "net":        {"value": cur["net"], "mom": mom("net"), "label_zh": "实发合计", "label_en": "Net Pay"},
        "employer_contrib": {"value": cur["employer_contrib"], "mom": mom("employer_contrib"), "label_zh": "雇主缴纳", "label_en": "Employer Contrib"},
        "hrdf":       {"value": cur["hrdf"], "mom": mom("hrdf"), "label_zh": "HRDF 征费", "label_en": "HRDF Levy"},
        "pcb":        {"value": cur["pcb"], "mom": mom("pcb"), "label_zh": "PCB 预扣税", "label_en": "PCB/MTD"},
        "ot":         {"value": cur["ot"], "mom": mom("ot"), "label_zh": "加班成本", "label_en": "Overtime"},
        "headcount":  {"value": cur["headcount"], "mom": 0.0, "label_zh": "在职人数", "label_en": "Headcount"},
    }
    cost_per_head = round(cur["total_cost"] / cur["headcount"], 2) if cur["headcount"] else 0
    ot_ratio = round(cur["ot"] / cur["gross"] * 100, 1) if cur["gross"] else 0

    return {
        "ok": True, "company": company, "month": base_month,
        "currency": cur_meta["code"], "currency_prefix": cur_meta["prefix"],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "kpis": kpis,
        "cost_per_head": cost_per_head,
        "ot_ratio": ot_ratio,
        "trend": [{"month": h["month"], "total_cost": h["total_cost"],
                   "gross": h["gross"], "ot": h["ot"], "hrdf": h.get("hrdf", 0),
                   "pcb": h.get("pcb", 0)} for h in hist],
        "departments": _dept_breakdown(snap, company),
        "current": cur, "previous": prev,
    }


# ════════════════ ④ 异常稽查 ════════════════
def _sev_rank(s): return {"critical": 3, "warning": 2, "info": 1}.get(s, 0)


def detect_anomalies(company: str = "my", base_month: str = "2026-05") -> dict:
    snap = _company_snapshot(company)
    hist = _derive_history(_aggregate(snap, company), months=6, base=base_month)
    prev = hist[-2] if len(hist) >= 2 else hist[-1]
    cur = hist[-1]
    cur_meta = _currency_of(company)
    pfx = cur_meta["prefix"]
    issues = []

    def add(sev, code, who, title_zh, detail_zh, metric=None):
        issues.append({"severity": sev, "code": code, "subject": who,
                       "title": title_zh, "detail": detail_zh, "metric": metric})

    # —— 个人级规则 ——
    for x in snap:
        name = x["name"]; basic = x["basic_pay"] or 1
        # 1) 加班时数异常
        ot_hours = sum(b["hours"] for b in x["ot_detail"]["breakdown"])
        if ot_hours > OT_HOURS_CRIT:
            add("critical", "OT_HOURS", name, "加班时数严重超标",
                f"{name} 本月加班 {ot_hours:.0f} 小时,超过 {OT_HOURS_CRIT}h 严重阈值(MY 法定上限 104h/月),需复核考勤真实性。", ot_hours)
        elif ot_hours > OT_HOURS_WARN:
            add("warning", "OT_HOURS", name, "加班时数偏高",
                f"{name} 本月加班 {ot_hours:.0f} 小时,超过 {OT_HOURS_WARN}h 预警线,建议核对工时与人力配置。", ot_hours)
        # 2) 加班费占比异常
        ot_ratio = x["ot_amount"] / basic
        if ot_ratio > OT_COST_RATIO_WARN:
            add("warning", "OT_RATIO", name, "加班费占比过高",
                f"{name} 加班费 {pfx}{x['ot_amount']:,.0f} 占基本工资 {ot_ratio*100:.0f}%,超 {int(OT_COST_RATIO_WARN*100)}% 预警,或存在结构性人力缺口。",
                round(ot_ratio * 100, 1))
        # 3) 按比例工资提示(入/离职月)
        if x["prorate"]["prorated"]:
            pr = x["prorate"]
            add("info", "PRORATE", name, "按比例工资(入/离职月)",
                f"{name} 本月在职 {pr['worked_days']}/{pr['month_days']} 天,基本工资按比例折算 {pfx}{x['basic_pay']:,.0f},属正常但需财务确认离职结算/CP21。")

    # —— 公司级规则 ——
    def chg(k):
        p = prev.get(k, 0) or 0; c = cur.get(k, 0) or 0
        return (c - p) / p if p else 0
    cost_chg = chg("total_cost")
    if cost_chg > COST_SURGE_WARN:
        sev = "critical" if cost_chg > COST_SURGE_WARN * 2 else "warning"
        add(sev, "COST_SURGE", "全公司", "企业总成本环比突增",
            f"企业总成本环比上升 {cost_chg*100:.1f}%(由 {pfx}{prev['total_cost']:,.0f} → {pfx}{cur['total_cost']:,.0f}),建议下钻加班/新增人员/调薪。",
            round(cost_chg * 100, 1))
    ot_chg = chg("ot")
    if ot_chg > SALARY_JUMP_WARN:
        add("warning", "OT_SURGE", "全公司", "加班成本环比跳升",
            f"加班成本环比上升 {ot_chg*100:.1f}%,是本月成本上行的主要推手之一。", round(ot_chg * 100, 1))

    issues.sort(key=lambda i: _sev_rank(i["severity"]), reverse=True)
    counts = {"critical": 0, "warning": 0, "info": 0}
    for i in issues:
        counts[i["severity"]] = counts.get(i["severity"], 0) + 1
    health = max(0, 100 - counts["critical"] * 20 - counts["warning"] * 8 - counts["info"] * 2)
    return {"ok": True, "company": company, "month": base_month,
            "currency": cur_meta["code"], "currency_prefix": pfx,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "health_score": health, "counts": counts, "anomalies": issues}


# ════════════════ ③ AI 解读层(为何涨了)════════════════
def explain_cost_change(company: str = "my", base_month: str = "2026-05", lang: str = "zh") -> dict:
    ov = build_overview(company, base_month)
    cur, prev = ov["current"], ov["previous"]
    pfx = ov.get("currency_prefix", "RM")
    delta_total = round(cur["total_cost"] - prev["total_cost"], 2)

    # 归因分解: 各成本要素的环比贡献
    factors = []
    for k, zh, en in [
        ("basic", "基本工资", "Basic salary"),
        ("ot", "加班费", "Overtime"),
        ("epf_er", "雇主 EPF", "Employer EPF"),
        ("socso_er", "雇主 SOCSO", "Employer SOCSO"),
        ("eis_er", "雇主 EIS", "Employer EIS"),
        ("hrdf", "HRDF 征费", "HRDF levy"),
        ("pcb", "PCB 预扣税", "PCB/MTD"),
    ]:
        d = round((cur.get(k, 0) or 0) - (prev.get(k, 0) or 0), 2)
        if abs(d) < 0.01:
            continue
        share = round(d / delta_total * 100, 1) if delta_total else 0
        factors.append({"key": k, "label_zh": zh, "label_en": en,
                        "delta": d, "share": share})
    factors.sort(key=lambda f: abs(f["delta"]), reverse=True)

    pct = round(delta_total / prev["total_cost"] * 100, 1) if prev["total_cost"] else 0
    top = factors[0] if factors else None

    if lang == "en":
        if delta_total > 0:
            head = f"Total labour cost rose {pct:+.1f}% MoM ({pfx}{prev['total_cost']:,.0f} → {pfx}{cur['total_cost']:,.0f}, +{pfx}{delta_total:,.0f})."
        else:
            head = f"Total labour cost fell {pct:+.1f}% MoM ({pfx}{prev['total_cost']:,.0f} → {pfx}{cur['total_cost']:,.0f}, {pfx}{delta_total:,.0f})."
        body = " ".join(f"{f['label_en']} {'+' if f['delta']>0 else '-'}{pfx}{abs(f['delta']):,.0f} ({f['share']:+.0f}% of change)." for f in factors[:3])
        action = f"Top driver: {top['label_en']}." if top else ""
    else:
        if delta_total > 0:
            head = f"本月企业总成本环比上升 {pct:+.1f}%({pfx}{prev['total_cost']:,.0f} → {pfx}{cur['total_cost']:,.0f},增加 {pfx}{delta_total:,.0f})。"
        else:
            head = f"本月企业总成本环比下降 {pct:+.1f}%({pfx}{prev['total_cost']:,.0f} → {pfx}{cur['total_cost']:,.0f},减少 {pfx}{abs(delta_total):,.0f})。"
        body = " ".join(f"{f['label_zh']}{'增加' if f['delta']>0 else '减少'} {pfx}{abs(f['delta']):,.0f}(占变动 {f['share']:.0f}%)。" for f in factors[:3])
        action = f"最大推手是「{top['label_zh']}」,建议优先下钻该项。" if top else "各项基本持平。"

    summary = f"{head} {body} {action}".strip()
    return {"ok": True, "company": company, "month": base_month, "lang": lang,
            "currency": ov.get("currency"), "currency_prefix": pfx,
            "delta_total": delta_total, "pct": pct,
            "factors": factors, "summary": summary,
            "model": "rule-based-v1"}   # 升级 LLM 时改 narrate 钩子
