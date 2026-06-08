"""
马来西亚薪资数据 & 法定费率（KWSP/PERKESO/LHDN）
═══════════════════════════════════════════════════════════════
为「合规报表中心」三件套(Payslip / EPF Borang A / EA Form)提供数据源。
费率依据 2024 年马来西亚现行标准:
  · EPF(KWSP):  雇员 11% / 雇主 13%(月薪≤5000) 或 12%(月薪>5000)
  · SOCSO(PERKESO): 一类(就业伤害+伤残) 按薪资级距,雇主≈1.75% 雇员≈0.5%
  · EIS(SIP):   雇员 0.2% / 雇主 0.2%(月薪上限 5000)
  · PCB:        月度预扣税(此处用简化累进估算,真实以 LHDN PCB 计算器为准)
免责声明: 以下员工为演示数据;费率为通用近似值,正式申报请以 KWSP/PERKESO/LHDN 官方表为准。
"""
from __future__ import annotations

# ── 雇主主体信息(申报抬头) ──
EMPLOYER = {
    "name": "Paydaes Malaysia Sdn Bhd",
    "ssm_no": "202401012345 (1234567-X)",     # SSM 公司注册号
    "employer_no": "E 1234567890",             # LHDN 雇主编号
    "epf_no": "13012345678",                   # KWSP 雇主号
    "socso_no": "B1234567890",                 # PERKESO 雇主号
    "address": "Level 28, Menara Paydaes, Jalan Ampang, 50450 Kuala Lumpur, Malaysia",
    "tel": "+603-2168 8888",
    "mtd_no": "PCB/IGD/2024",
}

# ── 法定费率(2024) ──
EPF_EMPLOYEE_RATE = 0.11
def epf_employer_rate(monthly_wage: float) -> float:
    return 0.13 if monthly_wage <= 5000 else 0.12
EIS_RATE = 0.002          # 雇员/雇主各 0.2%
EIS_WAGE_CAP = 5000.0     # EIS 计算工资上限

def socso_employee(monthly_wage: float) -> float:
    # 一类(<60岁) 雇员约 0.5%,以 5000 为上限近似
    base = min(monthly_wage, 5000.0)
    return round(base * 0.005, 2)

def socso_employer(monthly_wage: float) -> float:
    # 一类(<60岁) 雇主约 1.75%
    base = min(monthly_wage, 5000.0)
    return round(base * 0.0175, 2)

def eis_amount(monthly_wage: float) -> float:
    base = min(monthly_wage, EIS_WAGE_CAP)
    return round(base * EIS_RATE, 2)

# pcb_estimate 已由 app.core.pcb_engine 的精确 LHDN MTD 引擎替代(见 compute_monthly)。


# ── 演示员工薪资档案(马来西亚) ──
# 字段:
#   basic / allow_fixed(应税固定津贴) / allow_taxexempt(免税津贴,EA Part F) / bonus / ot
#   marital(婚姻: single/married) / spouse_income(配偶有无收入) / children(普通子女) /
#   children_tertiary(高教子女) / zakat_monthly(月度Zakat) / tp1_relief(TP1其他年度宽免)
def _emp(emp_no, name, ic_no, epf_no, socso_no, designation, dept, basic,
         allow_fixed=0, allow_taxexempt=0, bonus=0, ot=0,
         marital="single", spouse_income=True, children=0, children_tertiary=0,
         zakat_monthly=0.0, tp1_relief=0.0):
    return dict(emp_no=emp_no, name=name, ic_no=ic_no, epf_no=epf_no, socso_no=socso_no,
                designation=designation, dept=dept, basic=basic, allow_fixed=allow_fixed,
                allow_taxexempt=allow_taxexempt, bonus=bonus, ot=ot, marital=marital,
                spouse_income=spouse_income, children=children, children_tertiary=children_tertiary,
                zakat_monthly=zakat_monthly, tp1_relief=tp1_relief)

PAYROLL_EMPLOYEES = [
    _emp("MY001", "Ahmad Bin Ismail",  "880512-14-5523", "12345601", "880512145523",
         "Engineering Manager", "Technology", 9500, 1200, 500, 19000, 0,
         marital="married", spouse_income=False, children=2, zakat_monthly=150),
    _emp("MY002", "Tan Mei Ling",      "910823-10-2241", "12345602", "910823102241",
         "Senior Accountant", "Finance", 6800, 800, 500, 13600, 0,
         marital="married", spouse_income=True, children=1),
    _emp("MY003", "Ruby Rose A/P Raj", "950114-08-5566", "12345603", "950114085566",
         "HR Executive", "Human Resources", 4500, 500, 300, 4500, 420,
         marital="single", children=0),
    _emp("MY004", "John Lim Wei Jie",  "970328-14-7789", "12345604", "970328147789",
         "Sales Executive", "Sales", 3800, 400, 300, 3800, 650,
         marital="married", spouse_income=True, children=1, children_tertiary=1),
    _emp("MY005", "Siti Nurhaliza",    "930707-05-3312", "12345605", "930707053312",
         "Admin Assistant", "Operations", 2900, 200, 200, 2900, 380,
         marital="single", children=0),
]


def compute_monthly(emp: dict) -> dict:
    """计算单个员工的月度薪资明细(含法定扣除)。"""
    basic = emp["basic"]
    allow_fixed = emp.get("allow_fixed", 0)
    allow_te = emp.get("allow_taxexempt", 0)
    ot = emp.get("ot", 0)
    gross_taxable = basic + allow_fixed + ot          # 应税总收入
    gross_total = gross_taxable + allow_te            # 实际总收入(含免税)

    epf_emp = round(gross_taxable * EPF_EMPLOYEE_RATE, 2)
    epf_er = round(gross_taxable * epf_employer_rate(gross_taxable), 2)
    socso_emp = socso_employee(gross_taxable)
    socso_er = socso_employer(gross_taxable)
    eis_emp = eis_amount(gross_taxable)
    eis_er = eis_amount(gross_taxable)

    # 精确 PCB —— 调用 LHDN MTD 官方公式引擎
    from app.core import pcb_engine
    mtd = pcb_engine.compute_mtd_from_monthly(
        monthly_taxable=gross_taxable,
        monthly_epf=epf_emp,
        spouse_no_income=(emp.get("marital") == "married" and not emp.get("spouse_income", True)),
        children=emp.get("children", 0),
        children_tertiary=emp.get("children_tertiary", 0),
        tp1_other_relief=emp.get("tp1_relief", 0.0),
        zakat_paid_ytd=emp.get("zakat_monthly", 0.0) * 11,   # 前11月累计(简化)
        remaining_months=12,
    )
    pcb = mtd["mtd_monthly"]
    zakat = round(emp.get("zakat_monthly", 0.0), 2)
    # PCB 可被 Zakat 抵扣后实缴(MTD 公式已扣 Z),此处 pcb 为净额

    deductions = epf_emp + socso_emp + eis_emp + pcb + zakat
    net = round(gross_total - deductions, 2)
    return {
        **emp,
        "gross_taxable": round(gross_taxable, 2),
        "gross_total": round(gross_total, 2),
        "epf_emp": epf_emp, "epf_er": epf_er,
        "socso_emp": socso_emp, "socso_er": socso_er,
        "eis_emp": eis_emp, "eis_er": eis_er,
        "pcb": pcb, "zakat": zakat,
        "pcb_detail": mtd,
        "total_deduction": round(deductions, 2),
        "net_pay": net,
    }


def compute_annual(emp: dict) -> dict:
    """计算单个员工的年度汇总(供 EA Form 用): 月×12 + 年终奖。"""
    m = compute_monthly(emp)
    months = 12
    bonus = emp.get("bonus", 0)
    annual_basic = m["gross_taxable"] * months - emp.get("ot", 0) * months  # 仅基本+固定津贴部分
    annual_gross_13_1 = round((emp["basic"] + emp.get("allow_fixed", 0)) * months + emp.get("ot", 0) * months + bonus, 2)
    return {
        **emp,
        "annual_gross": annual_gross_13_1,                       # EA Part B 1(a) 薪资类
        "annual_bonus": bonus,                                   # EA Part B 1(b) 奖金
        "annual_ot": round(emp.get("ot", 0) * months, 2),
        "annual_taxexempt": round(emp.get("allow_taxexempt", 0) * months, 2),  # EA Part F 免税津贴
        "annual_epf_emp": round(m["epf_emp"] * months, 2),
        "annual_socso_emp": round(m["socso_emp"] * months, 2),
        "annual_eis_emp": round(m["eis_emp"] * months, 2),
        "annual_pcb": round(m["pcb"] * months, 2),
        "annual_zakat": round(m.get("zakat", 0) * months, 2),
        "pcb_detail": m.get("pcb_detail", {}),
    }
