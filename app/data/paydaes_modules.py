"""
Paydaes HR-Payroll 套件 · 6 大业务域功能模块(Pro 方案)
═══════════════════════════════════════════════════════════════
基于真实 Paydaes 生产系统(uat-fe.pydco.com)52 张截图提炼。
全部用「7 块积木」模板驱动,Mock 数据:
  layout 类型:
    p_tabset    —— Tab 详情页(横向子 Tab + 表单字段)
    p_inline    —— Inline Table 行编辑(行尾 +/垃圾桶)
    p_shuttle   —— 双栏穿梭框(候选/已选 + 箭头)
    p_formula   —— Formula 公式编辑器
    p_map       —— 地图定位框
    p_list      —— 列表页(搜索筛选 + Download/+Add + 表格)
    p_detail    —— 普通详情页(只读主键 + 表单 + Back/Save)
每个域顶部支持「横滚 Tab 群」(tax_tabs 字段)。
"""
from __future__ import annotations


# ── 字段类型简写 ──
# t=text  ro=只读  dd=下拉  date=日期  radio=单选  num=数字  area=文本域  map=地图  time=时间
def F(label, ftype="t", value="", req=False, unit="", opts=None, hint=""):
    return {"label": label, "type": ftype, "value": value, "req": req,
            "unit": unit, "opts": opts or [], "hint": hint}


# Tax 家族顶部横滚 Tab 群(对应真实截图)
TAX_TABS = ["EPF Rate", "SOCSO Rate", "EIS Rate", "Tax Rate Table",
            "Tax Parameters", "Tax Exemption (TP1)", "Tax Receipt",
            "EA Setting", "EC Setting"]


def _tax_modules(cur: str) -> dict:
    return {
        # ① Tax Rate Table —— Inline Table 行编辑 + 横滚 Tab 群
        "tax_rate": {
            "title": "Tax Rate Table · 税率表", "domain": "税务合规",
            "desc": "维护各税种(RES/NON/REP/KNO/CSU)的应税区间与税率,支持分级累进",
            "layout": "p_inline", "tabs_top": TAX_TABS, "tabs_active": 3,
            "actions": ["+ Add Row", "AI 自动算税"],
            "header_fields": [
                F("Tax Year", "dd", "2026", True, opts=["2026", "2025", "2024"]),
                F("Tax Category", "dd", "RES - Resident", True,
                  opts=["RES - Resident", "NON - Non-Resident", "REP - Returning Expert",
                        "KNO - Knowledge Worker", "CSU - Civil Servant"]),
                F("Effective Date", "date", "2026-01-01", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
            ],
            "columns": ["No", "Chargeable Income From", "To", "Rate (%)", "Cumulative Tax"],
            "rows": [
                ["1", "0", "5,000", "0", "0"],
                ["2", "5,001", "20,000", "1", "150"],
                ["3", "20,001", "35,000", "3", "600"],
                ["4", "35,001", "50,000", "8", "1,800"],
                ["5", "50,001", "70,000", "13", "4,400"],
                ["6", "70,001", "100,000", "21", "10,700"],
            ],
        },
        # ② Tax Parameters —— 详情表单
        "tax_param": {
            "title": "Tax Parameters · 税务参数", "domain": "税务合规",
            "desc": "EPF 上限、个人/配偶/子女减免额等法定参数配置",
            "layout": "p_detail", "tabs_top": TAX_TABS, "tabs_active": 4,
            "actions": ["Save Changes"],
            "fields": [
                F("Tax Year", "dd", "2026", True, opts=["2026", "2025"]),
                F("EPF Limit", "num", "4000", True, unit=cur),
                F("Individual Deduction", "num", "9000", True, unit=cur),
                F("Spouse Deduction", "num", "4000", True, unit=cur),
                F("Child Deduction (per child)", "num", "2000", True, unit=cur),
                F("Disabled Individual Add-on", "num", "6000", False, unit=cur),
                F("Life Insurance & EPF Limit", "num", "7000", False, unit=cur),
                F("Medical / Education Insurance", "num", "3000", False, unit=cur),
            ],
        },
        # ③ Tax Exemption Limit (TP1) —— Inline Table(13 NP 项)
        "tax_tp1": {
            "title": "Tax Exemption Limit (TP1) · 免税限额", "domain": "税务合规",
            "desc": "TP1 表单的 13 项免税项目(NP)年度限额配置",
            "layout": "p_inline", "tabs_top": TAX_TABS, "tabs_active": 5,
            "actions": ["+ Add Row"],
            "header_fields": [
                F("Tax Year", "dd", "2026", True, opts=["2026", "2025"]),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
            ],
            "columns": ["No", "NP Code", "Exemption Item", "Annual Limit", "Per Claim"],
            "rows": [
                ["1", "NP01", "Petrol / Travelling Allowance", f"6,000 {cur}", "—"],
                ["2", "NP02", "Parking Allowance", "Full", "—"],
                ["3", "NP03", "Meal Allowance", "Full", "—"],
                ["4", "NP04", "Childcare Allowance", f"2,400 {cur}", "—"],
                ["5", "NP05", "Gift / Award (Long Service)", f"2,000 {cur}", "—"],
                ["6", "NP06", "Medical / Dental Benefit", "Full", "—"],
            ],
        },
        # ④ Tax Receipt —— 列表页(PCB/CP38 月度回单)
        "tax_receipt": {
            "title": "Tax Receipt · 税务回单", "domain": "税务合规",
            "desc": "PCB(月度预扣税)/ CP38(法院扣令)月度回单管理",
            "layout": "p_list", "tabs_top": TAX_TABS, "tabs_active": 6,
            "actions": ["Download", "+ Add"],
            "filters": ["Tax Year", "Receipt Type", "Month"],
            "columns": ["Receipt No", "Type", "Month", "Employee", "Amount", "Status"],
            "rows": [
                ["PCB-202605-001", "PCB", "2026-05", "Ruby Rose", f"540 {cur}", "已提交"],
                ["CP38-202605-002", "CP38", "2026-05", "John Tan", f"320 {cur}", "已提交"],
                ["PCB-202604-001", "PCB", "2026-04", "Ruby Rose", f"520 {cur}", "已提交"],
            ],
        },
        # ⑤ EA Setting —— 穿梭框
        "ea_setting": {
            "title": "EA Setting · EA 表单配置", "domain": "税务合规",
            "desc": "将薪资 Earnings 要素映射到法定 EA 表单栏位(年度个税表)",
            "layout": "p_shuttle", "tabs_top": TAX_TABS, "tabs_active": 7,
            "actions": ["Save Changes", "AI 自动归集"],
            "header_fields": [
                F("From Tax Year", "dd", "2026", True, opts=["2026", "2025"]),
                F("Email Template ID", "dd", "EA_2026_TPL", False,
                  opts=["EA_2026_TPL", "EA_DEFAULT"]),
            ],
            "shuttle_left_title": "可选 Earnings 要素",
            "shuttle_right_title": "已映射到 EA 栏位",
            "left": ["基本工资", "加班费", "全勤奖", "交通津贴", "餐补", "绩效奖金", "年终奖"],
            "right": ["基本工资", "绩效奖金", "年终奖"],
        },
        # ⑥ EC Setting —— 穿梭框
        "ec_setting": {
            "title": "EC Setting · EC 表单配置", "domain": "税务合规",
            "desc": "EC 表单(雇主薪酬申报)的 Earnings 要素映射",
            "layout": "p_shuttle", "tabs_top": TAX_TABS, "tabs_active": 8,
            "actions": ["Save Changes"],
            "header_fields": [
                F("From Tax Year", "dd", "2026", True, opts=["2026", "2025"]),
            ],
            "shuttle_left_title": "可选 Earnings 要素",
            "shuttle_right_title": "已映射到 EC 栏位",
            "left": ["基本工资", "加班费", "全勤奖", "交通津贴", "餐补", "绩效奖金"],
            "right": ["基本工资", "加班费"],
        },
    }


# ═══════════════════════════════════════════════════════════
#  🏖️ Leave 假期域
# ═══════════════════════════════════════════════════════════
def _leave_modules(cur: str) -> dict:
    return {
        # Leave Entitlement —— Formula 公式编辑器(AI 自然语言生成预埋点)
        "leave_entitlement": {
            "title": "Leave Entitlement · 假期权益", "domain": "假期管理",
            "desc": "定义假期资格规则,支持 Eligibility / Pro Rata / Carry Forward / Advance 多维配置",
            "layout": "p_formula",
            "actions": ["Save Changes", "新增权益"],
            "header_fields": [
                F("Country Code", "ro", "MY", True),
                F("Entitlement Code", "t", "AL-STD-2026", True),
                F("Effective Date", "date", "2026-01-01", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
                F("Entitlement Name", "t", "标准年假权益", True),
                F("Same for all employee", "radio", "", True, opts=["Yes", "No"]),
                F("Default Entitlement Day(s)", "num", "14", True, unit="天"),
            ],
            "formula": ("IF(HR.GENDER='M' AND HR.MARITAL='married',\n"
                        "   ENTITLEMENT.DAYS + 3,\n"
                        "   IF(SERVICE.YEARS >= 5,\n"
                        "      ENTITLEMENT.DAYS + 2,\n"
                        "      ENTITLEMENT.DAYS))"),
            "formula_vars": ["HR.GENDER", "HR.MARITAL", "SERVICE.YEARS", "HR.GRADE",
                             "ENTITLEMENT.DAYS", "IF()", "AND", "OR", "ROUND()"],
        },
        # Leave Type —— 详情表单 + 内部 Tab
        "leave_type": {
            "title": "Leave Type · 假期类型", "domain": "假期管理",
            "desc": "定义假期类型的基础属性、扣减规则、性别/婚姻限制",
            "layout": "p_tabset",
            "actions": ["Save Changes", "+ Add"],
            "sub_tabs": ["基础设置", "扣减规则", "限制条件", "审批流"],
            "fields": [
                F("Leave Code", "t", "AL", True),
                F("Leave Name", "t", "年假 Annual Leave", True),
                F("Effective Date", "date", "2026-01-01", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
                F("Paid Leave", "radio", "", True, opts=["Yes", "No"]),
                F("Allow Half Day", "radio", "", True, opts=["Yes", "No"]),
                F("Gender Restriction", "dd", "无限制", False, opts=["无限制", "仅男性", "仅女性"]),
                F("Min. Service (months)", "num", "3", False, unit="月"),
            ],
        },
        # Leave Group —— 列表页
        "leave_group": {
            "title": "Leave Group · 假期组", "domain": "假期管理",
            "desc": "聚合假期类型、原因、是否必填、考勤关联与校验规则",
            "layout": "p_list",
            "actions": ["Download", "+ Add"],
            "filters": ["Leave Type", "Status"],
            "columns": ["Group Code", "Leave Type", "Leave Reason", "Required?", "Time&Attendance", "Status"],
            "rows": [
                ["LG-STD", "年假/病假/事假", "需填原因", "Yes", "已关联", "✅ 生效"],
                ["LG-MED", "病假/住院假", "需附件", "Yes", "已关联", "✅ 生效"],
                ["LG-SPC", "婚假/产假/陪产假", "需附件", "Yes", "—", "✅ 生效"],
            ],
        },
    }


# ═══════════════════════════════════════════════════════════
#  ⏰ Time & Attendance 考勤域
# ═══════════════════════════════════════════════════════════
def _ta_modules(cur: str) -> dict:
    return {
        # Shift —— 详情表单(含弹性班次单选 + 宽限期)
        "shift": {
            "title": "Shift · 班次", "domain": "考勤管理",
            "desc": "定义班次时间、班别类型、弹性设置、迟到宽限期",
            "layout": "p_detail",
            "actions": ["Save Changes", "+ Add"],
            "fields": [
                F("Company Code", "ro", "COM01", True),
                F("Shift Code", "t", "AFTERNOON", True),
                F("Effective Date", "date", "2024-05-03", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
                F("Day Type", "dd", "WD - Work Day", True, opts=["WD - Work Day", "RD - Rest Day", "PH - Public Holiday"]),
                F("Flexible Shift", "radio", "", True, opts=["Yes", "Yes (With Limit)", "No"]),
                F("Start Time", "time", "12:00", True),
                F("End Time", "time", "22:00", True),
                F("Grace for Late", "num", "5", True, unit="分钟"),
                F("Shift Description", "t", "Afternoon Shift 12pm - 10pm", False),
            ],
        },
        # Schedule Group —— Inline Table(Admin/Member Option)
        "schedule_group": {
            "title": "Schedule Group · 排班组", "domain": "考勤管理",
            "desc": "管理排班组成员(Admin Option / Member Option),关联部门/员工/班次",
            "layout": "p_inline",
            "actions": ["+ Add Row", "AI 智能排班"],
            "header_fields": [
                F("Company Code", "ro", "COM01", True),
                F("Schedule Group Code", "t", "FUTURE1", True),
                F("Effective Date", "date", "2027-01-12", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
            ],
            "columns": ["No", "Employee ID", "Name", "Department", "Shift Code"],
            "rows": [
                ["1", "EMP99999999", "Ruby Rose", "运营部", "AFTERNOON"],
                ["2", "EMP10000231", "John Tan", "财务部", "MORNING"],
                ["3", "EMP10000455", "Lisa Wong", "技术部", "FLEXIBLE"],
            ],
        },
        # Holiday Schedule —— Inline Table(法定假日)
        "holiday": {
            "title": "Holiday Schedule · 假日表", "domain": "考勤管理",
            "desc": "维护法定公共假日(Gazetted PH),支持按州属差异化",
            "layout": "p_inline",
            "actions": ["+ Add Row"],
            "header_fields": [
                F("Company Code", "ro", "COM01", True),
                F("Year", "dd", "2026", True, opts=["2026", "2025"]),
                F("State", "dd", "Selangor", False, opts=["Selangor", "Kuala Lumpur", "Penang", "Johor"]),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
            ],
            "columns": ["No", "Date", "Holiday Name", "Type", "Gazetted PH"],
            "rows": [
                ["1", "2026-01-01", "New Year's Day", "National", "Yes"],
                ["2", "2026-02-17", "Chinese New Year", "National", "Yes"],
                ["3", "2026-05-01", "Labour Day", "National", "Yes"],
                ["4", "2026-08-31", "Merdeka Day", "National", "Yes"],
            ],
        },
        # Attendance Location —— 地图定位
        "attendance_loc": {
            "title": "Attendance Location · 打卡地点", "domain": "考勤管理",
            "desc": "GPS 打卡地点配置,设置经纬度与有效打卡半径",
            "layout": "p_map", "radius": "500",
            "actions": ["Save Changes", "+ Add"],
            "fields": [
                F("Effective Date", "date", "2026-01-01", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
                F("Location Name", "t", "Paydaes HQ Tower", True),
                F("Location Address", "area", "Level 12, Menara KL, Jalan Sultan Ismail", False, hint="请输入地址…"),
                F("Postcode", "t", "50250", False),
                F("Country", "dd", "Malaysia", False, opts=["Malaysia", "Singapore", "Thailand"]),
                F("State", "dd", "Kuala Lumpur", False, opts=["Kuala Lumpur", "Selangor"]),
                F("Maximum Radius", "num", "500", False, unit="米"),
            ],
        },
        # Overtime Setting —— Tabset(General/Rules/Overtime Type)
        "overtime": {
            "title": "Overtime Setting · 加班设置", "domain": "考勤管理",
            "desc": "加班规则、上限、加班类型、替代假转换配置",
            "layout": "p_tabset",
            "actions": ["Save Changes", "AI 异常检测"],
            "sub_tabs": ["General", "Rules", "Overtime Type"],
            "fields": [
                F("Company Code", "ro", "COM05", True),
                F("Effective Date", "date", "2025-11-11", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
                F("Monthly Overtime Maximum Hours", "num", "104", True, unit="小时"),
                F("Min. OT Block", "num", "30", False, unit="分钟"),
                F("Replacement Leave Conversion", "radio", "", False, opts=["启用", "不启用"]),
            ],
        },
    }


# ═══════════════════════════════════════════════════════════
#  📒 Accounting 财务域
# ═══════════════════════════════════════════════════════════
def _acc_modules(cur: str) -> dict:
    return {
        # Chart of Accounts —— Tabset(Chartfields/COA Mapping/Remapping)
        "coa": {
            "title": "Chart of Accounts · 会计科目表", "domain": "财务做账",
            "desc": "配置 Chartfield 1-6 维度、科目映射与重映射",
            "layout": "p_tabset",
            "actions": ["Save Changes", "AI 科目映射"],
            "sub_tabs": ["Chartfields Details", "COA Mapping", "COA Remapping"],
            "fields": [
                F("Company Code", "ro", "COM01", True),
                F("Effective Date", "date", "2026-01-01", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
                F("Chartfield 1 (Entity)", "dd", "1000 - 总公司", True, opts=["1000 - 总公司", "2000 - 分公司"]),
                F("Chartfield 2 (Dept)", "dd", "100 - 运营部", False, opts=["100 - 运营部", "200 - 财务部"]),
                F("Chartfield 3 (Project)", "dd", "PRJ-001", False, opts=["PRJ-001", "PRJ-002"]),
                F("Chartfield 4 (Cost Center)", "dd", "CC-KL", False, opts=["CC-KL", "CC-SG"]),
                F("Chartfield 5 (Account)", "dd", "6100 - 差旅费", False, opts=["6100 - 差旅费", "6200 - 餐饮费"]),
                F("Chartfield 6 (Future)", "dd", "—", False, opts=["—"]),
            ],
        },
        # Element Grouping —— 穿梭框
        "element_group": {
            "title": "Element Grouping · 要素分组", "domain": "财务做账",
            "desc": "将薪资/报销要素分组,映射到 GL 科目",
            "layout": "p_shuttle",
            "actions": ["Save Changes"],
            "header_fields": [
                F("Group Code", "t", "GRP-CLAIM", True),
                F("Effective Date", "date", "2026-01-01", True),
            ],
            "shuttle_left_title": "可选要素",
            "shuttle_right_title": "已加入分组",
            "left": ["餐饮费", "交通费", "住宿费", "机票", "办公用品", "培训费", "通讯费"],
            "right": ["餐饮费", "交通费", "住宿费"],
        },
        # GL Account Number —— 列表页
        "gl_account": {
            "title": "GL Account Number · 总账科目", "domain": "财务做账",
            "desc": "维护总账科目编号与名称,关联报销/薪资要素",
            "layout": "p_list",
            "actions": ["Download", "+ Add"],
            "filters": ["Account Type", "Status"],
            "columns": ["GL Account No", "Account Name", "Type", "关联要素", "Status"],
            "rows": [
                ["6100", "差旅费 Travel Expense", "费用", "交通/住宿/机票", "✅ 生效"],
                ["6200", "餐饮费 Meal Expense", "费用", "餐饮", "✅ 生效"],
                ["6300", "办公费 Office Expense", "费用", "办公用品", "✅ 生效"],
                ["2100", "应付职工薪酬", "负债", "薪资接口", "✅ 生效"],
            ],
        },
    }


# ═══════════════════════════════════════════════════════════
#  🏦 Master Data 主数据域
# ═══════════════════════════════════════════════════════════
def _master_modules(cur: str) -> dict:
    return {
        # Bank —— Tabset(Bank Table/Branch/BIC)
        "bank": {
            "title": "Bank · 银行主数据", "domain": "主数据",
            "desc": "维护银行表、分行表、银行识别码(BIC/SWIFT)",
            "layout": "p_tabset",
            "actions": ["Save Changes", "+ Add"],
            "sub_tabs": ["Bank Table", "Branch Table", "Bank Identifier Code"],
            "fields": [
                F("Bank Code", "t", "MBB", True),
                F("Bank Name", "t", "Maybank Berhad", True),
                F("Country", "dd", "Malaysia", True, opts=["Malaysia", "Singapore", "Thailand"]),
                F("BIC / SWIFT", "t", "MBBEMYKL", True),
                F("Effective Date", "date", "2026-01-01", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
            ],
        },
        # Payroll Variable —— 列表页
        "payroll_var": {
            "title": "Payroll Variable · 薪资变量", "domain": "主数据",
            "desc": "维护薪资计算用的变量参数(津贴标准、扣款比例等)",
            "layout": "p_list",
            "actions": ["Download", "+ Add"],
            "filters": ["Variable Type", "Status"],
            "columns": ["Variable Code", "Name", "Value", "Unit", "Status"],
            "rows": [
                ["VAR-MEAL", "餐补标准", "200", cur, "✅ 生效"],
                ["VAR-TRANS", "交通津贴", "500", cur, "✅ 生效"],
                ["VAR-EPF-EE", "EPF 员工比例", "11", "%", "✅ 生效"],
                ["VAR-EPF-ER", "EPF 雇主比例", "13", "%", "✅ 生效"],
            ],
        },
    }


def get_paydaes_module(module_id: str, cur: str = "MYR") -> dict | None:
    """返回 Paydaes 6 大域模块视图;不存在返回 None(交回原 18 模块逻辑)"""
    registry = {}
    registry.update(_tax_modules(cur))
    registry.update(_leave_modules(cur))
    registry.update(_ta_modules(cur))
    registry.update(_acc_modules(cur))
    registry.update(_master_modules(cur))
    return registry.get(module_id)


# 供导航树使用:Paydaes 6 大域菜单(全量铺开)
PAYDAES_NAV = [
    {"id": "tax", "name": "税务合规", "icon": "fa-percent", "type": "group", "badge": "NEW", "children": [
        {"id": "tax_rate", "name": "Tax Rate Table", "module": "税率表"},
        {"id": "tax_param", "name": "Tax Parameters", "module": "税务参数"},
        {"id": "tax_tp1", "name": "Tax Exemption (TP1)", "module": "免税限额"},
        {"id": "tax_receipt", "name": "Tax Receipt", "module": "税务回单"},
        {"id": "ea_setting", "name": "EA Setting", "module": "EA表单"},
        {"id": "ec_setting", "name": "EC Setting", "module": "EC表单"},
    ]},
    {"id": "leave", "name": "假期管理", "icon": "fa-umbrella-beach", "type": "group", "badge": "NEW", "children": [
        {"id": "leave_entitlement", "name": "Leave Entitlement", "module": "假期权益"},
        {"id": "leave_type", "name": "Leave Type", "module": "假期类型"},
        {"id": "leave_group", "name": "Leave Group", "module": "假期组"},
    ]},
    {"id": "ta", "name": "考勤管理", "icon": "fa-business-time", "type": "group", "badge": "NEW", "children": [
        {"id": "shift", "name": "Shift", "module": "班次"},
        {"id": "schedule_group", "name": "Schedule Group", "module": "排班组"},
        {"id": "holiday", "name": "Holiday Schedule", "module": "假日表"},
        {"id": "attendance_loc", "name": "Attendance Location", "module": "打卡地点"},
        {"id": "overtime", "name": "Overtime Setting", "module": "加班设置"},
    ]},
    {"id": "accounting", "name": "财务做账", "icon": "fa-book", "type": "group", "badge": "NEW", "children": [
        {"id": "coa", "name": "Chart of Accounts", "module": "会计科目表"},
        {"id": "element_group", "name": "Element Grouping", "module": "要素分组"},
        {"id": "gl_account", "name": "GL Account Number", "module": "总账科目"},
    ]},
    {"id": "master", "name": "主数据", "icon": "fa-database", "type": "group", "badge": "NEW", "children": [
        {"id": "bank", "name": "Bank", "module": "银行"},
        {"id": "payroll_var", "name": "Payroll Variable", "module": "薪资变量"},
    ]},
]
