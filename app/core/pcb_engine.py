"""
LHDN MTD (PCB) 精确计算引擎 — 计算机化计算方法 (Computerised Calculation Method)
═══════════════════════════════════════════════════════════════════════════
严格依据 LHDN《Specification for MTD Using Computerised Calculation》(2024) 实现。

核心公式(正常薪酬 Normal Remuneration):
        [ (P − M) × R + B ] − (Z + X)
  MTD = ──────────────────────────────
                  n + 1

其中:
  P = 全年应税总额(Total chargeable income for the year)
  M = 所在税档的下限(First chargeable income of the bracket)
  R = 该档税率(%)
  B = M 对应的累计税额(已扣个人/配偶回扣 rebate)
  Z = 当年已缴 Zakat 累计(不含当月)
  X = 之前月份已缴 PCB 累计
  n = 当年剩余月份(不含当月);  n+1 = 含当月的剩余月份

P 的推导:
  P = [ Σ(Y) − EPF_year_capped − other_relief ] + (Y_current − EPF_current)... 简化为年度法:
  P = 年度应税收入 − 个人宽免(9000) − EPF宽免(≤4000) − 配偶宽免(4000,若适用)
      − 子女宽免(Σ) − 人寿保险/其他TP1 − ...

免责声明: 本引擎实现官方公式主干。极端边界(REP/非居民/additional remuneration 的
year-to-date 重算)以 LHDN 官方 e-Calculator / e-PCB 为最终准绳。
"""
from __future__ import annotations

# ── 2024 税率表 (M, R, B) ──
# 每档: (上限 ceiling, M=下限, R=税率, B=M处累计税额含回扣)
MTD_BRACKETS_2024 = [
    # ceiling,        M,        R,      B
    (5000,            0,        0.00,   0),
    (20000,           5000,     0.01,   -400),    # 含个人回扣 RM400 (应税≤35000)
    (35000,           20000,    0.03,   -250),    # 含回扣
    (50000,           35000,    0.06,   600),
    (70000,           50000,    0.11,   1500),
    (100000,          70000,    0.19,   3700),
    (400000,          100000,   0.25,   9400),
    (600000,          400000,   0.26,   84400),
    (2000000,         600000,   0.28,   136400),
    (float("inf"),    2000000,  0.30,   528400),
]

# ── 法定宽免 (2024) ──
RELIEF_INDIVIDUAL = 9000.0       # 个人宽免
RELIEF_EPF_CAP = 4000.0          # EPF + 人寿保险宽免上限
RELIEF_SPOUSE = 4000.0           # 配偶宽免(配偶无收入时)
RELIEF_CHILD = 2000.0            # 每名子女宽免(普通,18岁以下)
RELIEF_CHILD_TERTIARY = 8000.0   # 高等教育子女宽免


def _bracket_for(p: float):
    """根据全年应税额 P 找到所在税档 (M, R, B)。"""
    for ceiling, M, R, B in MTD_BRACKETS_2024:
        if p <= ceiling:
            return M, R, B
    last = MTD_BRACKETS_2024[-1]
    return last[1], last[2], last[3]


def annual_chargeable(
    annual_gross_taxable: float,
    annual_epf: float,
    *,
    spouse_no_income: bool = False,
    children: int = 0,
    children_tertiary: int = 0,
    tp1_other_relief: float = 0.0,
) -> float:
    """
    计算全年应税总额 P。
      annual_gross_taxable : 年度应税总收入(薪资+固定津贴+加班+奖金,不含免税津贴)
      annual_epf           : 年度 EPF 雇员缴款(宽免上限 4000)
      spouse_no_income     : 配偶无收入 → 享 4000 配偶宽免
      children             : 普通子女数(每名 2000)
      children_tertiary    : 高教子女数(每名 8000)
      tp1_other_relief     : TP1 表其他已申报宽免(人寿/医疗/教育保险等)
    """
    epf_relief = min(annual_epf, RELIEF_EPF_CAP)
    relief = RELIEF_INDIVIDUAL + epf_relief
    if spouse_no_income:
        relief += RELIEF_SPOUSE
    relief += children * RELIEF_CHILD
    relief += children_tertiary * RELIEF_CHILD_TERTIARY
    relief += max(tp1_other_relief, 0)
    return max(annual_gross_taxable - relief, 0)


def compute_mtd(
    annual_gross_taxable: float,
    annual_epf: float,
    *,
    spouse_no_income: bool = False,
    children: int = 0,
    children_tertiary: int = 0,
    tp1_other_relief: float = 0.0,
    zakat_paid_ytd: float = 0.0,
    pcb_paid_ytd: float = 0.0,
    remaining_months: int = 12,
) -> dict:
    """
    返回精确 MTD/PCB 月度税额及推导明细。
      remaining_months : 含当月的剩余月份 (n+1)。年初满额则 12。
    """
    P = annual_chargeable(
        annual_gross_taxable, annual_epf,
        spouse_no_income=spouse_no_income,
        children=children, children_tertiary=children_tertiary,
        tp1_other_relief=tp1_other_relief,
    )
    M, R, B = _bracket_for(P)
    # 全年应纳税额(扣回扣)
    annual_tax = (P - M) * R + B
    annual_tax = max(annual_tax, 0)
    # 公式: MTD = [annual_tax − (Z + X)] / (n+1)
    nplus1 = max(remaining_months, 1)
    mtd = (annual_tax - (zakat_paid_ytd + pcb_paid_ytd)) / nplus1
    mtd = max(round(mtd, 2), 0)
    return {
        "P": round(P, 2),
        "M": M, "R": R, "B": B,
        "annual_tax": round(annual_tax, 2),
        "zakat_ytd": round(zakat_paid_ytd, 2),
        "pcb_ytd": round(pcb_paid_ytd, 2),
        "remaining_months": nplus1,
        "mtd_monthly": mtd,
        "formula": "[(P-M)*R + B - (Z+X)] / (n+1)",
    }


def compute_mtd_from_monthly(
    monthly_taxable: float,
    monthly_epf: float,
    **kwargs,
) -> dict:
    """便捷封装:用月度数据年化后计算(年化=月×12)。"""
    return compute_mtd(
        annual_gross_taxable=monthly_taxable * 12,
        annual_epf=monthly_epf * 12,
        **kwargs,
    )
