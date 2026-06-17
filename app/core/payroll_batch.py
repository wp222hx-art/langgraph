"""
批量发薪管线 · 公式引擎真实驱动工资单
═══════════════════════════════════════════════════════════════
把「公式编辑器里配的规则」真正接进发薪批算:
  · leave_entitlement._formula  → 按每个员工的 HR 维度(性别/婚姻/司龄/职级)算「应享假期天数」
  · overtime._formula           → 按每个员工的加班时数/倍率算「加班费」(可覆盖默认 OT_RATES)
每条工资单都带「公式溯源」(formula_trace): 用了哪条公式 / 喂了哪些变量 / 算出什么值,
实现「公式 → 工资单」的可解释闭环。

数据流:
  module_forms(公司维度落库公式) ──► formula_engine.evaluate(公式, 员工变量) ──►
  应享天数 / 加班费 ──► payroll_data.compute_monthly(法定扣除) ──► 工资单
"""
from __future__ import annotations

from app.core import formula_engine
from app.data import payroll_data, db


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

    # ③ 法定扣除 + 净薪(沿用成熟引擎)
    pay = payroll_data.compute_monthly(emp_calc)

    # ④ 公式驱动结果挂回工资单
    pay["entitlement_days"] = entitlement_days
    pay["ot_formula_amount"] = ot_amount_formula
    pay["formula_trace"] = trace
    return pay


def run_batch(company: str = "my", period: str = "",
              employees: list | None = None) -> dict:
    """批量发薪:遍历公司员工 → 逐人公式驱动 → 汇总。
    返回 {period, company, formulas, count, payslips, totals}。"""
    emps = employees if employees is not None else payroll_data.PAYROLL_EMPLOYEES
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

    return {
        "ok": True,
        "company": company,
        "period": period,
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
            "formulas": full["formulas"], "count": full["count"],
            "rows": rows, "totals": full["totals"]}
