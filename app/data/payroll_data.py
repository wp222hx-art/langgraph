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

def pcb_estimate(annual_chargeable: float) -> float:
    """简化累进估算(月度 PCB = 年税/12)。正式以 LHDN 官方 PCB 计算器为准。"""
    brackets = [
        (5000, 0.00, 0),
        (20000, 0.01, 0),
        (35000, 0.03, 150),
        (50000, 0.08, 600),
        (70000, 0.13, 1800),
        (100000, 0.21, 4400),
        (400000, 0.24, 10700),
        (float("inf"), 0.30, 84700),
    ]
    prev = 0
    tax = 0.0
    for cap, rate, cumtax in brackets:
        if annual_chargeable <= cap:
            tax = cumtax + (annual_chargeable - prev) * rate
            break
        prev = cap
    return round(max(tax, 0) / 12, 2)


# ── 演示员工薪资档案(马来西亚) ──
# (emp_no, name, ic_no, epf_no, socso_no, designation, dept, basic, allow_fixed, allow_taxexempt)
#   allow_fixed       = 应税固定津贴(房补/职务津贴等)
#   allow_taxexempt   = 免税津贴(油费/餐补,落入 EA Part F)
PAYROLL_EMPLOYEES = [
    {"emp_no": "MY001", "name": "Ahmad Bin Ismail",  "ic_no": "880512-14-5523",
     "epf_no": "12345601", "socso_no": "880512145523", "designation": "Engineering Manager",
     "dept": "Technology", "basic": 9500, "allow_fixed": 1200, "allow_taxexempt": 500,
     "bonus": 19000, "ot": 0},
    {"emp_no": "MY002", "name": "Tan Mei Ling",      "ic_no": "910823-10-2241",
     "epf_no": "12345602", "socso_no": "910823102241", "designation": "Senior Accountant",
     "dept": "Finance", "basic": 6800, "allow_fixed": 800, "allow_taxexempt": 500,
     "bonus": 13600, "ot": 0},
    {"emp_no": "MY003", "name": "Ruby Rose A/P Raj", "ic_no": "950114-08-5566",
     "epf_no": "12345603", "socso_no": "950114085566", "designation": "HR Executive",
     "dept": "Human Resources", "basic": 4500, "allow_fixed": 500, "allow_taxexempt": 300,
     "bonus": 4500, "ot": 420},
    {"emp_no": "MY004", "name": "John Lim Wei Jie",  "ic_no": "970328-14-7789",
     "epf_no": "12345604", "socso_no": "970328147789", "designation": "Sales Executive",
     "dept": "Sales", "basic": 3800, "allow_fixed": 400, "allow_taxexempt": 300,
     "bonus": 3800, "ot": 650},
    {"emp_no": "MY005", "name": "Siti Nurhaliza",    "ic_no": "930707-05-3312",
     "epf_no": "12345605", "socso_no": "930707053312", "designation": "Admin Assistant",
     "dept": "Operations", "basic": 2900, "allow_fixed": 200, "allow_taxexempt": 200,
     "bonus": 2900, "ot": 380},
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

    # 估算年度应税(简化: 月应税×12 − EPF年度减免上限4000 − 个人减免9000)
    annual_chargeable = max(gross_taxable * 12 - 4000 - 9000, 0)
    pcb = pcb_estimate(annual_chargeable)

    deductions = epf_emp + socso_emp + eis_emp + pcb
    net = round(gross_total - deductions, 2)
    return {
        **emp,
        "gross_taxable": round(gross_taxable, 2),
        "gross_total": round(gross_total, 2),
        "epf_emp": epf_emp, "epf_er": epf_er,
        "socso_emp": socso_emp, "socso_er": socso_er,
        "eis_emp": eis_emp, "eis_er": eis_er,
        "pcb": pcb,
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
    }
