"""
7 国真实税务合规数据库 · TAX_DATA_BY_COUNTRY
═══════════════════════════════════════════════════════════════
覆盖 SG / MY / TH / VN / ID / HK / CN 的:
  · tax_categories  税种(各国术语不同:大马 RES/NON/REP/KNO/CSU;新加坡 Resident/Non-Resident…)
  · brackets        分级累进税率表 {category: [[from, to, rate%, cumulative_tax], ...]}
  · params          法定参数(减免/上限,字段随国别变)
  · tp1             免税/扣除项目(各国制度不同)
  · receipts        税务回单类型(MY 是 PCB/CP38;SG 是 IRAS;等)
  · ea_ec           EA/EC 表单映射(法定年度申报表的本地名称)
注:税率档位为各国 2024-2026 公开税制的合规框架值,正式申报以各国税务机关官方系统为准。
"""
from __future__ import annotations

# ──────────────────────────────────────────────────────────────
# 🇲🇾 马来西亚(LHDN)—— RES/NON/REP/KNO/CSU,累进 0~30%
# ──────────────────────────────────────────────────────────────
MY = {
    "currency": "MYR", "year": "2026", "authority": "LHDN (IRBM)",
    "categories": ["RES - Resident", "NON - Non-Resident", "REP - Returning Expert",
                   "KNO - Knowledge Worker", "CSU - Civil Servant"],
    "brackets": {
        "RES - Resident": [
            ["0", "5,000", "0", "0"], ["5,001", "20,000", "1", "150"],
            ["20,001", "35,000", "3", "600"], ["35,001", "50,000", "8", "1,800"],
            ["50,001", "70,000", "13", "4,400"], ["70,001", "100,000", "21", "10,700"],
            ["100,001", "400,000", "24", "82,700"], ["400,001", "600,000", "25", "132,700"],
            ["600,001", "2,000,000", "26", "496,700"], ["2,000,001", "above", "30", "—"],
        ],
        "NON - Non-Resident": [["0", "above", "30", "—"]],
        "REP - Returning Expert": [["0", "above", "15", "—"]],
        "KNO - Knowledge Worker": [["0", "above", "15", "—"]],
        "CSU - Civil Servant": [
            ["0", "5,000", "0", "0"], ["5,001", "20,000", "1", "150"],
            ["20,001", "35,000", "3", "600"], ["35,001", "50,000", "8", "1,800"],
        ],
    },
    "params": [
        ("EPF Limit", "4,000"), ("Individual Deduction", "9,000"),
        ("Spouse Deduction", "4,000"), ("Child Deduction (per child)", "2,000"),
        ("Disabled Individual Add-on", "6,000"), ("Life Insurance & EPF Limit", "7,000"),
        ("Medical / Education Insurance", "3,000"), ("Lifestyle Relief", "2,500"),
    ],
    "tp1": [
        ["NP01", "Petrol / Travelling Allowance", "6,000", "—"],
        ["NP02", "Parking Allowance", "Full", "—"],
        ["NP03", "Meal Allowance", "Full", "—"],
        ["NP04", "Childcare Allowance", "2,400", "—"],
        ["NP05", "Gift / Award (Long Service)", "2,000", "—"],
        ["NP06", "Medical / Dental Benefit", "Full", "—"],
    ],
    "receipts": ["PCB (Monthly MTD)", "CP38 (Court Order)"],
    "ea_form": "EA Form (C.P.8A)", "ec_form": "Form C.P.8D (EC)",
}

# ──────────────────────────────────────────────────────────────
# 🇸🇬 新加坡(IRAS)—— Resident 累进 0~24% + Non-Resident 15%/24%
# ──────────────────────────────────────────────────────────────
SG = {
    "currency": "SGD", "year": "2026", "authority": "IRAS",
    "categories": ["Resident", "Non-Resident", "PR (Permanent Resident)"],
    "brackets": {
        "Resident": [
            ["0", "20,000", "0", "0"], ["20,001", "30,000", "2", "200"],
            ["30,001", "40,000", "3.5", "550"], ["40,001", "80,000", "7", "3,350"],
            ["80,001", "120,000", "11.5", "7,950"], ["120,001", "160,000", "15", "13,950"],
            ["160,001", "200,000", "18", "21,150"], ["200,001", "240,000", "19", "28,750"],
            ["240,001", "280,000", "19.5", "36,550"], ["280,001", "320,000", "20", "44,550"],
            ["320,001", "500,000", "22", "84,150"], ["500,001", "1,000,000", "23", "199,150"],
            ["1,000,001", "above", "24", "—"],
        ],
        "Non-Resident": [["0", "above", "15 or 24 (higher)", "—"]],
        "PR (Permanent Resident)": [
            ["0", "20,000", "0", "0"], ["20,001", "30,000", "2", "200"],
            ["30,001", "40,000", "3.5", "550"], ["40,001", "80,000", "7", "3,350"],
        ],
    },
    "params": [
        ("CPF Ordinary Wage Ceiling", "7,400"), ("CPF Annual Salary Ceiling", "102,000"),
        ("Earned Income Relief", "1,000"), ("Spouse Relief", "2,000"),
        ("Qualifying Child Relief", "4,000"), ("Parent Relief", "9,000"),
        ("CPF Cash Top-up Relief", "8,000"), ("SRS Contribution Cap", "15,300"),
    ],
    "tp1": [
        ["DR01", "Earned Income Relief", "1,000", "—"],
        ["DR02", "CPF Relief (employee)", "Statutory", "—"],
        ["DR03", "NSman Relief", "3,000", "—"],
        ["DR04", "Course Fees Relief", "5,500", "—"],
        ["DR05", "Foreign Maid Levy Relief", "2x Levy", "—"],
        ["DR06", "Life Insurance Relief", "5,000", "—"],
    ],
    "receipts": ["IRAS NOA (Notice of Assessment)", "CPF Contribution Receipt"],
    "ea_form": "Form IR8A (Annual Return)", "ec_form": "Appendix 8A / 8B",
}

# ──────────────────────────────────────────────────────────────
# 🇹🇭 泰国(Revenue Department)—— 累进 0~35% 7 档
# ──────────────────────────────────────────────────────────────
TH = {
    "currency": "THB", "year": "2026", "authority": "Revenue Department (สรรพากร)",
    "categories": ["Resident", "Non-Resident"],
    "brackets": {
        "Resident": [
            ["0", "150,000", "0", "0"], ["150,001", "300,000", "5", "7,500"],
            ["300,001", "500,000", "10", "27,500"], ["500,001", "750,000", "15", "65,000"],
            ["750,001", "1,000,000", "20", "115,000"], ["1,000,001", "2,000,000", "25", "365,000"],
            ["2,000,001", "5,000,000", "30", "1,265,000"], ["5,000,001", "above", "35", "—"],
        ],
        "Non-Resident": [["0", "above", "15 (WHT on Thai-source)", "—"]],
    },
    "params": [
        ("Personal Allowance", "60,000"), ("Spouse Allowance", "60,000"),
        ("Child Allowance (per child)", "30,000"), ("Parental Care Allowance", "30,000"),
        ("Provident Fund Cap", "500,000"), ("SSF / RMF Cap", "500,000"),
        ("Life Insurance Premium", "100,000"), ("Health Insurance Premium", "25,000"),
    ],
    "tp1": [
        ["TH01", "Personal Allowance", "60,000", "—"],
        ["TH02", "Spouse Allowance", "60,000", "—"],
        ["TH03", "Child Allowance", "30,000", "per child"],
        ["TH04", "Social Security Contribution", "9,000", "—"],
        ["TH05", "Provident Fund", "500,000", "—"],
        ["TH06", "Home Loan Interest", "100,000", "—"],
    ],
    "receipts": ["PND.1 (Monthly WHT)", "PND.91 (Annual PIT)"],
    "ea_form": "Form 50 Tawi (WHT Certificate)", "ec_form": "PND.1 Kor (Annual Summary)",
}

# ──────────────────────────────────────────────────────────────
# 🇻🇳 越南(General Department of Taxation)—— 累进 5~35% 7 档
# ──────────────────────────────────────────────────────────────
VN = {
    "currency": "VND", "year": "2026", "authority": "General Department of Taxation",
    "categories": ["Resident", "Non-Resident"],
    "brackets": {
        # 单位:百万越南盾/年(显示用千分位)
        "Resident": [
            ["0", "60,000,000", "5", "3,000,000"], ["60,000,001", "120,000,000", "10", "9,000,000"],
            ["120,000,001", "216,000,000", "15", "23,400,000"], ["216,000,001", "384,000,000", "20", "57,000,000"],
            ["384,000,001", "624,000,000", "25", "117,000,000"], ["624,000,001", "960,000,000", "30", "217,800,000"],
            ["960,000,001", "above", "35", "—"],
        ],
        "Non-Resident": [["0", "above", "20 (flat on Vietnam-source)", "—"]],
    },
    "params": [
        ("Personal Deduction (annual)", "132,000,000"), ("Dependant Deduction (per person)", "52,800,000"),
        ("Social Insurance (SI) Rate", "8%"), ("Health Insurance (HI) Rate", "1.5%"),
        ("Unemployment Insurance (UI) Rate", "1%"), ("SI Salary Cap (x base)", "20x"),
    ],
    "tp1": [
        ["VN01", "Personal Deduction", "132,000,000", "—"],
        ["VN02", "Dependant Deduction", "52,800,000", "per person"],
        ["VN03", "Compulsory Social Insurance", "Statutory", "—"],
        ["VN04", "Charitable / Humanitarian Donation", "Full", "—"],
        ["VN05", "Voluntary Pension Contribution", "12,000,000", "—"],
    ],
    "receipts": ["PIT Monthly Declaration (Form 05/KK-TNCN)", "PIT Annual Finalisation (02/QTT-TNCN)"],
    "ea_form": "Form 02/QTT-TNCN (Annual)", "ec_form": "Form 05/QTT-TNCN (Employer)",
}

# ──────────────────────────────────────────────────────────────
# 🇮🇩 印度尼西亚(DJP)—— 累进 5~35% 5 档 (UU HPP 2022)
# ──────────────────────────────────────────────────────────────
ID = {
    "currency": "IDR", "year": "2026", "authority": "DJP (Direktorat Jenderal Pajak)",
    "categories": ["Resident (NPWP)", "Non-Resident", "Without NPWP (+20%)"],
    "brackets": {
        "Resident (NPWP)": [
            ["0", "60,000,000", "5", "3,000,000"], ["60,000,001", "250,000,000", "15", "31,500,000"],
            ["250,000,001", "500,000,000", "25", "94,000,000"], ["500,000,001", "5,000,000,000", "30", "1,444,000,000"],
            ["5,000,000,001", "above", "35", "—"],
        ],
        "Non-Resident": [["0", "above", "20 (WHT Art.26)", "—"]],
        "Without NPWP (+20%)": [["0", "above", "+20% surcharge", "—"]],
    },
    "params": [
        ("PTKP (Single/TK0)", "54,000,000"), ("PTKP Marriage Add-on", "4,500,000"),
        ("PTKP Dependant (max 3)", "4,500,000"), ("BPJS Kesehatan Rate", "1%"),
        ("BPJS Ketenagakerjaan (JHT)", "2%"), ("Occupational Cost Deduction", "6,000,000"),
    ],
    "tp1": [
        ["ID01", "PTKP Basic (TK0)", "54,000,000", "—"],
        ["ID02", "PTKP Marriage", "4,500,000", "—"],
        ["ID03", "PTKP Dependant", "4,500,000", "max 3"],
        ["ID04", "Occupational Cost (Biaya Jabatan)", "6,000,000", "5% capped"],
        ["ID05", "Pension Contribution", "2,400,000", "—"],
        ["ID06", "Zakat / Religious Donation", "Full", "—"],
    ],
    "receipts": ["SPT Masa PPh 21 (Monthly)", "Bukti Potong 1721-A1 (Annual)"],
    "ea_form": "Form 1721-A1 (Annual)", "ec_form": "SPT Tahunan 1721",
}

# ──────────────────────────────────────────────────────────────
# 🇭🇰 香港(IRD)—— 累进 2~17% 4 档 / 标准税率 15%(2024起两级 15%/16%)
# ──────────────────────────────────────────────────────────────
HK = {
    "currency": "HKD", "year": "2026", "authority": "Inland Revenue Department (IRD)",
    "categories": ["Progressive (累进)", "Standard Rate (标准税率)"],
    "brackets": {
        "Progressive (累进)": [
            ["0", "50,000", "2", "1,000"], ["50,001", "100,000", "6", "4,000"],
            ["100,001", "150,000", "10", "9,000"], ["150,001", "above", "17", "—"],
        ],
        "Standard Rate (标准税率)": [
            ["0", "5,000,000", "15", "750,000"], ["5,000,001", "above", "16", "—"],
        ],
    },
    "params": [
        ("Basic Allowance", "132,000"), ("Married Person's Allowance", "264,000"),
        ("Child Allowance (per child)", "130,000"), ("Dependent Parent Allowance", "50,000"),
        ("MPF Mandatory Contribution Cap", "18,000"), ("Self-Education Expenses", "100,000"),
        ("Home Loan Interest", "100,000"), ("Elderly Residential Care", "100,000"),
    ],
    "tp1": [
        ["HK01", "Basic Allowance", "132,000", "—"],
        ["HK02", "Child Allowance", "130,000", "per child"],
        ["HK03", "MPF Contribution", "18,000", "—"],
        ["HK04", "Self-Education Expenses", "100,000", "—"],
        ["HK05", "Approved Charitable Donations", "35% of income", "—"],
        ["HK06", "Home Loan Interest", "100,000", "20 years"],
    ],
    "receipts": ["IR56B (Employer's Return)", "IR56E/F/G (Commencement/Cessation)"],
    "ea_form": "Form IR56B (Annual)", "ec_form": "Form BIR56A (Employer's Return)",
}

# ──────────────────────────────────────────────────────────────
# 🇨🇳 中国大陆(国家税务总局)—— 综合所得累进 3~45% 7 档
# ──────────────────────────────────────────────────────────────
CN = {
    "currency": "CNY", "year": "2026", "authority": "国家税务总局 (STA)",
    "categories": ["居民个人 Resident", "非居民个人 Non-Resident"],
    "brackets": {
        "居民个人 Resident": [
            ["0", "36,000", "3", "1,080"], ["36,001", "144,000", "10", "11,880"],
            ["144,001", "300,000", "20", "43,080"], ["300,001", "420,000", "25", "73,080"],
            ["420,001", "660,000", "30", "145,080"], ["660,001", "960,000", "35", "250,080"],
            ["960,001", "above", "45", "—"],
        ],
        "非居民个人 Non-Resident": [
            ["0", "3,000", "3", "90"], ["3,001", "12,000", "10", "1,290"],
            ["12,001", "25,000", "20", "3,890"], ["25,001", "35,000", "25", "6,390"],
        ],
    },
    "params": [
        ("基本减除费用 Basic Deduction", "60,000"), ("子女教育 Children Education", "24,000"),
        ("继续教育 Continuing Education", "4,800"), ("住房贷款利息 Mortgage Interest", "12,000"),
        ("住房租金 Housing Rent", "18,000"), ("赡养老人 Elderly Support", "36,000"),
        ("3岁以下婴幼儿照护 Infant Care", "24,000"), ("社保公积金 Social Insurance", "Statutory"),
    ],
    "tp1": [
        ["CN01", "子女教育 Children Education", "24,000", "per child"],
        ["CN02", "继续教育 Continuing Education", "4,800", "—"],
        ["CN03", "住房贷款利息 Mortgage Interest", "12,000", "—"],
        ["CN04", "住房租金 Housing Rent", "18,000", "—"],
        ["CN05", "赡养老人 Elderly Support", "36,000", "—"],
        ["CN06", "大病医疗 Critical Illness", "80,000", "—"],
    ],
    "receipts": ["个税预扣预缴申报 (Monthly Withholding)", "年度汇算清缴 (Annual Reconciliation)"],
    "ea_form": "个人所得税年度自行申报表", "ec_form": "扣缴个人所得税报告表",
}

TAX_DATA_BY_COUNTRY = {
    "MY": MY, "SG": SG, "TH": TH, "VN": VN, "ID": ID, "HK": HK, "CN": CN,
}


def get_tax_data(country: str) -> dict:
    """按国家代码返回税务数据;未知国别回退马来西亚。"""
    return TAX_DATA_BY_COUNTRY.get((country or "MY").upper(), MY)
