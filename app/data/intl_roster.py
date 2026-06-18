"""
多国本地化员工花名册 (International Localized Roster)
═══════════════════════════════════════════════════════════════
为「AI 老板驾驶舱」提供按公司/国家本地化的员工样本:
  · 名字 / 职位 / 银行 / 货币  —— 按国家本地化(中文名/英文名/泰文名/越南名…)
  · HR 维度(性别/司龄/职级/部门/加班时数/基本工资)—— 跨国保持一致结构,体现可比性

设计原则:
  · 不污染 app.data.payroll_data 的 MY 真实合规链路(EPF Borang A / EA Form / PCB),
    那套是 MY 法定报表专用;本花名册仅服务驾驶舱多国分析。
  · 基本工资以"当地货币本币"直接给出(贴近各国真实薪资量级),
    再由 statutory_intl 按各国法定规则计算扣除,使数据"币种 × 数值 × 法定项"三者自洽。
"""
from __future__ import annotations

# ── 5 个员工"原型"(职位/部门/HR维度跨国一致,保证可比与差异化结构)──
# tier: 基本工资在各国的相对档位(经理>会计>HR>销售>行政)
_ARCHETYPES = [
    {"slot": 0, "dept": "Technology",      "dept_zh": "技术部",   "gender": "M", "service_years": 12, "grade": "P7",
     "ot_hours": {"normal": 10, "rest": 4},                      "marital": "married", "children": 2},
    {"slot": 1, "dept": "Finance",         "dept_zh": "财务部",   "gender": "F", "service_years": 7,  "grade": "P6",
     "ot_hours": {"normal": 6},                                  "marital": "married", "children": 1},
    {"slot": 2, "dept": "Human Resources", "dept_zh": "人力资源部", "gender": "F", "service_years": 3,  "grade": "P5",
     "ot_hours": {"normal": 8, "holiday": 5},                    "marital": "single",  "children": 0},
    {"slot": 3, "dept": "Sales",           "dept_zh": "销售部",   "gender": "M", "service_years": 1,  "grade": "P4",
     "ot_hours": {"normal": 12, "rest": 6}, "worked_days": 18, "month_days": 30, "marital": "married", "children": 1},
    {"slot": 4, "dept": "Operations",      "dept_zh": "运营部",   "gender": "F", "service_years": 5,  "grade": "P3",
     "ot_hours": {"normal": 60, "rest": 12, "holiday": 8},       "marital": "single",  "children": 0},  # 加班超标(触发稽查)
]

# 职位本地化(中/英),按 slot
_DESIGNATIONS = [
    {"en": "Engineering Manager", "zh": "工程经理"},
    {"en": "Senior Accountant",   "zh": "高级会计师"},
    {"en": "HR Executive",        "zh": "人力资源主管"},
    {"en": "Sales Executive",     "zh": "销售主管"},
    {"en": "Admin Assistant",     "zh": "行政助理"},
]

# ── 各国本地化档案: 名字 + 基本工资(本币月薪) + 主要银行 ──
# 月薪量级贴近各国真实白领薪资(经理→行政递减)。
_COUNTRY_PROFILES = {
    "MY": {  # 马来西亚 · 马来/华裔/印裔混合
        "names": ["Ahmad Bin Ismail", "Tan Mei Ling", "Ruby Rose A/P Raj", "John Lim Wei Jie", "Siti Nurhaliza"],
        "salaries": [9500, 6800, 4500, 3800, 2900],
        "banks": ["Maybank", "CIMB Bank", "Public Bank", "RHB Bank", "Maybank"],
        "id_label": "IC No",
    },
    "SG": {  # 新加坡 · 华裔/英文名为主
        "names": ["Daniel Wong Jun Kai", "Rachel Lim Hui Min", "Priya Subramaniam", "Marcus Tan Wei", "Nurul Aisyah"],
        "salaries": [9800, 7200, 5200, 4600, 3400],
        "banks": ["DBS Bank", "OCBC Bank", "UOB", "DBS Bank", "OCBC Bank"],
        "id_label": "NRIC",
    },
    "TH": {  # 泰国 · 泰文名
        "names": ["สมชาย วงศ์สว่าง", "นภัสสร ศรีสุข", "ธนพร แก้วมณี", "วีรภัทร ทองดี", "กมลวรรณ ใจดี"],
        "salaries": [85000, 62000, 45000, 38000, 28000],
        "banks": ["Bangkok Bank", "Kasikornbank", "SCB", "Krungthai Bank", "Bangkok Bank"],
        "id_label": "บัตรประชาชน",
    },
    "VN": {  # 越南 · 越南名
        "names": ["Nguyễn Văn Hùng", "Trần Thị Mai", "Lê Thị Hương", "Phạm Minh Tuấn", "Võ Thị Lan"],
        "salaries": [42000000, 30000000, 22000000, 18000000, 13000000],
        "banks": ["Vietcombank", "BIDV", "Techcombank", "VietinBank", "Vietcombank"],
        "id_label": "CCCD",
    },
    "ID": {  # 印尼 · 印尼名
        "names": ["Budi Santoso", "Siti Rahayu", "Dewi Lestari", "Agus Pratama", "Rina Wati"],
        "salaries": [38000000, 27000000, 19000000, 15000000, 11000000],
        "banks": ["Bank Mandiri", "BCA", "BRI", "BNI", "Bank Mandiri"],
        "id_label": "NIK",
    },
    "HK": {  # 香港 · 粤语拼音 + 英文名
        "names": ["Chan Tai Man", "Wong Ka Yan", "Lee Siu Ming", "Cheung Ho Yin", "Lam Mei Kuen"],
        "salaries": [52000, 38000, 28000, 24000, 18000],
        "banks": ["HSBC", "Hang Seng Bank", "Bank of China (HK)", "HSBC", "Standard Chartered"],
        "id_label": "HKID",
    },
    "CN": {  # 中国 · 中文名
        "names": ["王建国", "李梅", "张伟", "刘强", "陈静"],
        "salaries": [35000, 25000, 18000, 15000, 11000],
        "banks": ["中国工商银行", "中国建设银行", "招商银行", "中国银行", "中国农业银行"],
        "id_label": "身份证",
    },
}


def localized_roster(country: str) -> list[dict]:
    """生成某国本地化员工样本(5 人)。
    返回字段对齐 payroll_data._emp() 的核心维度,可直接喂给 statutory_intl。
    """
    prof = _COUNTRY_PROFILES.get(country) or _COUNTRY_PROFILES["MY"]
    roster = []
    for arch in _ARCHETYPES:
        i = arch["slot"]
        desig = _DESIGNATIONS[i]
        emp = {
            "emp_no": f"{country}{i+1:03d}",
            "name": prof["names"][i],
            "country": country,
            "dept": arch["dept"],
            "dept_zh": arch["dept_zh"],
            "designation": desig["en"],
            "designation_zh": desig["zh"],
            "gender": arch["gender"],
            "service_years": arch["service_years"],
            "grade": arch["grade"],
            "marital": arch.get("marital", "single"),
            "children": arch.get("children", 0),
            "basic": prof["salaries"][i],          # 本币月基本工资
            "ot_hours": arch["ot_hours"],
            "bank": prof["banks"][i],
            "id_label": prof["id_label"],
        }
        if "worked_days" in arch:
            emp["worked_days"] = arch["worked_days"]
            emp["month_days"] = arch["month_days"]
        roster.append(emp)
    return roster
