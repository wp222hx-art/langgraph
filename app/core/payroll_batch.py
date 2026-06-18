"""
批量发薪管线 · 公式引擎真实驱动工资单
═══════════════════════════════════════════════════════════════
把「公式编辑器里配的规则」真正接进发薪批算:
  · leave_entitlement._formula  → 按每个员工的 HR 维度(性别/婚姻/司龄/职级)算「应享假期天数」
  · overtime._formula           → 按每个员工的加班时数/倍率算「加班费」(可覆盖默认 OT_RATES)
每条工资单都带「公式溯源」(formula_trace): 用了哪条公式 / 喂了哪些变量 / 算出什么值,
实现「公式 → 工资单」的可解释闭环。

数据流(与「AI 老板驾驶舱」同源,消除数据割裂):
  intl_roster.localized_roster(国别本地化花名册) ──► formula_engine.evaluate(公式, 员工变量) ──►
  应享天数 / 加班费 ──► 国别法定引擎(MY=compute_monthly · 其他=statutory_intl) ──► 工资单
  使「驾驶舱看到的 / 发薪算出的 / 工资单展示的」= 同一个数据世界。
"""
from __future__ import annotations

from app.core import formula_engine
from app.core import statutory_intl as SI
from app.data import payroll_data, db
from app.data import intl_roster as R
from app.data import enterprise as E


# 货币显示符号(与驾驶舱 analytics._CURRENCY_PREFIX 保持一致)
_CURRENCY_PREFIX = {
    "MYR": "RM", "SGD": "S$", "HKD": "HK$", "CNY": "¥",
    "THB": "฿", "VND": "₫", "IDR": "Rp",
}


# ── 公司 → 国别 反查(与驾驶舱 analytics._company_meta 同源逻辑)──
def _country_of(company: str) -> str:
    """由公司 id 反查所在国(MY/SG/CN/TH/HK/VN/ID);找不到回退 MY。"""
    for g in E.GROUPS:
        for c in g["companies"]:
            if c["id"] == company:
                return c.get("country", "MY")
    return "MY"


def _currency_of(company: str) -> dict:
    """由公司 id 反查 {code, prefix}(币种代码 + 显示符号);找不到回退 MYR/RM。"""
    for g in E.GROUPS:
        for c in g["companies"]:
            if c["id"] == company:
                code = c.get("currency", "MYR")
                return {"code": code, "prefix": _CURRENCY_PREFIX.get(code, code + " ")}
    return {"code": "MYR", "prefix": "RM"}


def _statutory_payslip(emp: dict, country: str) -> dict:
    """非 MY 国家:本地化花名册 + 国别法定引擎 → 工资单(字段对齐 compute_monthly)。
    与驾驶舱 analytics._compute_employee_intl 完全同口径,确保「发薪算的」=「驾驶舱看的」。
    """
    basic_full = float(emp.get("basic", 0) or 0)
    pr = payroll_data.prorate_basic(basic_full, emp.get("worked_days"), emp.get("month_days"))
    basic = pr["basic"]
    ot_calc = payroll_data.compute_ot(basic_full, emp.get("ot_hours"))
    ot = ot_calc["amount"]
    gross = round(basic + ot, 2)

    st = SI.compute_statutory(country, gross)
    # 各国雇主缴纳归并到通用桶(共享 SI.employer_buckets,与驾驶舱 analytics 同一套逻辑)
    bk = SI.employer_buckets(st["er"])
    epf_er, socso_er, eis_er, hrdf = bk["epf_er"], bk["socso_er"], bk["eis_er"], bk["hrdf"]
    ee_total = st["ee_total"]
    return {
        **emp,
        "basic_pay": basic,
        "prorate": pr,
        "ot_amount": ot,
        "ot_detail": ot_calc,
        "gross_taxable": gross,
        "gross_total": gross,
        "epf_emp": 0.0, "epf_er": round(epf_er, 2),
        "socso_emp": 0.0, "socso_er": round(socso_er, 2),
        "eis_emp": 0.0, "eis_er": round(eis_er, 2),
        "hrdf": round(hrdf, 2),
        "pcb": st["income_tax"], "zakat": 0.0,
        "total_deduction": ee_total,
        "net_pay": st["net_pay"],
        "employer_contrib": st["employer_contrib"],
        "total_cost": st["total_cost"],
        "currency": st["currency"],
        "statutory_ee": st["ee"], "statutory_er": st["er"],
        "scheme_zh": SI.SCHEME_NAME.get(country, {}).get("zh", ""),
    }


# ── 员工 dict → 公式变量空间 ──
def _emp_vars(emp: dict) -> dict:
    """把员工字段映射成公式可识别的点号变量(HR.GENDER / SERVICE.YEARS ...)。
    覆盖 leave_entitlement 与 overtime 公式可能用到的全部变量。"""
    ot = emp.get("ot_hours") or {}
    if not isinstance(ot, dict):
        ot = {}
    return {
        # 人事维度
        "HR.GENDER": emp.get("gender", "M"),
        "HR.MARITAL": emp.get("marital", "single"),
        "HR.GRADE": emp.get("grade", "P5"),
        "AGE": emp.get("age", 35),
        # 假期维度
        "SERVICE.YEARS": emp.get("service_years", 3),
        "ENTITLEMENT.DAYS": emp.get("base_entitlement", 14),
        "CARRY.FORWARD": emp.get("carry_forward", 0),
        "JOIN.MONTH": emp.get("join_month", 1),
        # 考勤 / 加班维度
        "OT.HOURS": float(sum(float(v or 0) for v in ot.values())) if ot else 0.0,
        "OT.NORMAL": float(ot.get("normal", 0) or 0),
        "OT.REST": float(ot.get("rest", 0) or 0),
        "OT.HOLIDAY": float(ot.get("holiday", 0) or 0),
        "RATE.NORMAL": payroll_data.OT_RATES["normal"],
        "RATE.REST": payroll_data.OT_RATES["rest"],
        "RATE.HOLIDAY": payroll_data.OT_RATES["holiday"],
        "IS.HOLIDAY": 1 if float(ot.get("holiday", 0) or 0) > 0 else 0,
        "BASE.HOURLY": payroll_data.hourly_rate(emp.get("basic", 0)),
    }


def _eval_formula(formula: str, variables: dict) -> dict:
    """安全求值;成功返回 {ok,result,...},失败/无公式返回 {ok:False,...}。"""
    if not formula or not str(formula).strip():
        return {"ok": False, "error": "无公式", "result": None}
    return formula_engine.evaluate(str(formula), variables)


def _get_company_formula(module_id: str, company: str) -> str:
    """从 module_forms 取该公司保存的公式(fxSave 存于 form._formula)。"""
    form = db.get_module_form(module_id, company) or {}
    return form.get("_formula", "") or ""


def compute_employee_pay(emp: dict, company: str,
                         leave_formula: str = "", ot_formula: str = "") -> dict:
    """单员工:公式驱动应享天数/加班费 → 再走法定扣除 → 出工资单(含公式溯源)。"""
    variables = _emp_vars(emp)
    trace = []

    # ① 假期应享天数 —— 由 leave_entitlement 公式驱动
    entitlement_days = emp.get("base_entitlement", 14)
    if leave_formula:
        r = _eval_formula(leave_formula, variables)
        if r.get("ok") and isinstance(r.get("result"), (int, float)):
            entitlement_days = r["result"]
        trace.append({
            "driver": "leave_entitlement",
            "label": "应享假期天数",
            "formula": leave_formula,
            "ok": bool(r.get("ok")),
            "result": r.get("result") if r.get("ok") else None,
            "error": r.get("error"),
            "used_vars": {k: variables.get(k) for k in (r.get("used_vars") or [])},
        })

    # ② 加班费 —— 若配了 overtime 公式则由公式驱动,否则用默认分级费率
    emp_calc = dict(emp)        # 副本,避免污染源数据
    ot_amount_formula = None
    if ot_formula:
        r = _eval_formula(ot_formula, variables)
        if r.get("ok") and isinstance(r.get("result"), (int, float)):
            ot_amount_formula = round(float(r["result"]), 2)
            # 用公式算出的金额覆盖默认加班费(转成旧 ot 数字通道)
            emp_calc["ot_hours"] = ot_amount_formula
        trace.append({
            "driver": "overtime",
            "label": "加班费(公式驱动)",
            "formula": ot_formula,
            "ok": bool(r.get("ok")),
            "result": r.get("result") if r.get("ok") else None,
            "error": r.get("error"),
            "used_vars": {k: variables.get(k) for k in (r.get("used_vars") or [])},
        })

    # ③ 法定扣除 + 净薪(按国别分流,与驾驶舱同源)
    #    · MY → compute_monthly(保留 LHDN MTD 精确 PCB / Zakat / EA Form 链路)
    #    · 其他国 → statutory_intl(CPF/五险一金/SSF/MPF/PIT…)
    country = (emp.get("country") or _country_of(company)).upper()
    if country == "MY":
        pay = payroll_data.compute_monthly(emp_calc)
    else:
        pay = _statutory_payslip(emp_calc, country)

    # ④ 公式驱动结果挂回工资单
    pay["entitlement_days"] = entitlement_days
    pay["ot_formula_amount"] = ot_amount_formula
    pay["formula_trace"] = trace
    return pay


def run_batch(company: str = "my", period: str = "",
              employees: list | None = None) -> dict:
    """批量发薪:遍历公司员工 → 逐人公式驱动 → 汇总。
    返回 {period, company, formulas, count, payslips, totals}。"""
    if employees is not None:
        emps = employees
    else:
        # 与驾驶舱同源:本地化花名册(按公司所在国生成本币真实薪资样本)。
        # MY 仍可拿到 5 个 MY 员工(本地化档案首条即 MY),其余国家拿本国本地化样本,
        # 从根上消除「驾驶舱多国 / 发薪纯 MY」的数据割裂。
        country = _country_of(company)
        emps = R.localized_roster(country)
    leave_formula = _get_company_formula("leave_entitlement", company)
    ot_formula = _get_company_formula("overtime", company)

    payslips = []
    tot = {"gross_total": 0.0, "net_pay": 0.0, "epf_emp": 0.0, "epf_er": 0.0,
           "socso_emp": 0.0, "socso_er": 0.0, "eis_emp": 0.0, "eis_er": 0.0,
           "pcb": 0.0, "zakat": 0.0, "ot_amount": 0.0, "employer_contrib": 0.0,
           "total_cost": 0.0, "entitlement_days": 0.0}
    for e in emps:
        ps = compute_employee_pay(e, company, leave_formula, ot_formula)
        payslips.append(ps)
        for k in tot:
            v = ps.get(k, 0) or 0
            try:
                tot[k] += float(v)
            except (TypeError, ValueError):
                pass
    tot = {k: round(v, 2) for k, v in tot.items()}

    cur = _currency_of(company)
    return {
        "ok": True,
        "company": company,
        "period": period,
        "currency": cur["code"],
        "currency_prefix": cur["prefix"],
        "count": len(payslips),
        "formulas": {
            "leave_entitlement": leave_formula or "(未配置·用默认天数)",
            "overtime": ot_formula or "(未配置·用默认分级费率)",
            "leave_active": bool(leave_formula),
            "ot_active": bool(ot_formula),
        },
        "payslips": payslips,
        "totals": tot,
    }


def batch_summary(company: str = "my", period: str = "") -> dict:
    """轻量摘要(不含每人完整明细),供前端列表/校验用。"""
    full = run_batch(company, period)
    rows = []
    for ps in full["payslips"]:
        rows.append({
            "emp_no": ps.get("emp_no"), "name": ps.get("name"),
            "dept": ps.get("dept"), "grade": ps.get("grade"),
            "basic_pay": ps.get("basic_pay"),
            "ot_amount": ps.get("ot_amount"),
            "entitlement_days": ps.get("entitlement_days"),
            "gross_total": ps.get("gross_total"),
            "total_deduction": ps.get("total_deduction"),
            "net_pay": ps.get("net_pay"),
            "formula_trace": ps.get("formula_trace"),
        })
    return {"ok": True, "company": company, "period": period,
            "currency": full["currency"], "currency_prefix": full["currency_prefix"],
            "formulas": full["formulas"], "count": full["count"],
            "rows": rows, "totals": full["totals"]}
