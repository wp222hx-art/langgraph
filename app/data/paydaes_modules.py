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


# 国家代码 → 英文国家全名(供 Country 下拉框默认值联动)
_COUNTRY_NAME = {
    "SG": "Singapore", "MY": "Malaysia", "TH": "Thailand", "VN": "Vietnam",
    "ID": "Indonesia", "HK": "Hong Kong", "CN": "China",
}
# 全量国家下拉选项(7 国)
_COUNTRY_OPTS = list(_COUNTRY_NAME.values())


def _country_name(country: str) -> str:
    return _COUNTRY_NAME.get((country or "MY").upper(), "Malaysia")


# Tax 家族顶部横滚 Tab 群(对应真实截图)
TAX_TABS = ["EPF Rate", "SOCSO Rate", "EIS Rate", "Tax Rate Table",
            "Tax Parameters", "Tax Exemption (TP1)", "Tax Receipt",
            "EA Setting", "EC Setting"]


def _tax_modules(cur: str, country: str = "MY") -> dict:
    """税务合规 6 子模块 —— 按公司所属国家(country)联动真实税制数据。"""
    from app.data.tax_data import get_tax_data
    td = get_tax_data(country)
    cy = (country or "MY").upper()
    cur = td.get("currency", cur)        # 以国别币种为准
    yr = td.get("year", "2026")
    cats = td.get("categories", ["Resident"])
    first_cat = cats[0]
    # 税率表行:取首个税种的累进档(切税种由前端 Tab 控制,数据全量也带上)
    bracket_rows = td["brackets"].get(first_cat, [])
    tax_rows = [[str(i + 1)] + list(row) for i, row in enumerate(bracket_rows)]
    # 全税种的档位(供前端切税种用)
    brackets_all = {k: [[str(i + 1)] + list(r) for i, r in enumerate(v)]
                    for k, v in td["brackets"].items()}
    # 参数
    param_fields = [F("Tax Year", "dd", yr, True, opts=[yr, str(int(yr) - 1)])]
    for name, val in td.get("params", []):
        param_fields.append(F(name, "num", val, False, unit=cur))
    # 免税/扣除项
    tp1_rows = [[str(i + 1)] + list(r) for i, r in enumerate(td.get("tp1", []))]
    # 回单类型
    receipts = td.get("receipts", ["—"])
    rcpt_rows = [
        [f"{receipts[0].split(' ')[0]}-{yr}05-001", receipts[0], f"{yr}-05", "Employee A", f"540 {cur}", "已提交"],
        [f"{(receipts[1] if len(receipts) > 1 else receipts[0]).split(' ')[0]}-{yr}05-002",
         receipts[1] if len(receipts) > 1 else receipts[0], f"{yr}-05", "Employee B", f"320 {cur}", "已提交"],
    ]
    ea_name = td.get("ea_form", "EA Form")
    ec_name = td.get("ec_form", "EC Form")

    return {
        # ① Tax Rate Table —— Inline Table 行编辑 + 横滚 Tab 群(按国别税种/税率)
        "tax_rate": {
            "title": "Tax Rate Table · 税率表", "domain": "税务合规",
            "country": cy, "authority": td.get("authority", ""),
            "desc": f"维护 {cy} 各税种({' / '.join(c.split(' - ')[0].split(' (')[0] for c in cats)})的应税区间与税率,支持分级累进 · 主管:{td.get('authority','')}",
            "layout": "p_inline", "tabs_top": TAX_TABS, "tabs_active": 3,
            "actions": ["+ Add Row", "AI 自动算税"],
            "header_fields": [
                F("Tax Year", "dd", yr, True, opts=[yr, str(int(yr) - 1), str(int(yr) - 2)]),
                F("Tax Category", "dd", first_cat, True, opts=cats),
                F("Effective Date", "date", f"{yr}-01-01", True),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
            ],
            "columns": ["No", "Chargeable Income From", "To", "Rate (%)", f"Cumulative Tax ({cur})"],
            "rows": tax_rows,
            "brackets_all": brackets_all,   # 前端切税种用
        },
        # ② Tax Parameters —— 详情表单(国别法定参数)
        "tax_param": {
            "title": "Tax Parameters · 税务参数", "domain": "税务合规",
            "country": cy, "authority": td.get("authority", ""),
            "desc": f"{cy} 法定减免/上限参数配置(币种 {cur}) · 主管:{td.get('authority','')}",
            "layout": "p_detail", "tabs_top": TAX_TABS, "tabs_active": 4,
            "actions": ["Save Changes"],
            "fields": param_fields,
        },
        # ③ Tax Exemption Limit (TP1) —— Inline Table(国别免税/扣除项)
        "tax_tp1": {
            "title": "Tax Exemption Limit (TP1) · 免税限额", "domain": "税务合规",
            "country": cy,
            "desc": f"{cy} 年度免税/扣除项目限额配置(币种 {cur})",
            "layout": "p_inline", "tabs_top": TAX_TABS, "tabs_active": 5,
            "actions": ["+ Add Row"],
            "header_fields": [
                F("Tax Year", "dd", yr, True, opts=[yr, str(int(yr) - 1)]),
                F("Status", "dd", "A - Active", True, opts=["A - Active", "I - Inactive"]),
            ],
            "columns": ["No", "Code", "Exemption / Deduction Item", f"Annual Limit ({cur})", "Per Claim"],
            "rows": tp1_rows,
        },
        # ④ Tax Receipt —— 列表页(国别月度回单)
        "tax_receipt": {
            "title": "Tax Receipt · 税务回单", "domain": "税务合规",
            "country": cy,
            "desc": f"{cy} 月度预扣/申报回单管理({' / '.join(receipts)})",
            "layout": "p_list", "tabs_top": TAX_TABS, "tabs_active": 6,
            "actions": ["Download", "+ Add"],
            "filters": ["Tax Year", "Receipt Type", "Month"],
            "columns": ["Receipt No", "Type", "Month", "Employee", "Amount", "Status"],
            "rows": rcpt_rows,
        },
        # ⑤ EA Setting —— 穿梭框(国别年度个税表名称)
        "ea_setting": {
            "title": f"EA Setting · {ea_name} 配置", "domain": "税务合规",
            "country": cy,
            "desc": f"将薪资 Earnings 要素映射到 {cy} 法定年度申报表「{ea_name}」栏位",
            "layout": "p_shuttle", "tabs_top": TAX_TABS, "tabs_active": 7,
            "actions": ["Save Changes", "AI 自动归集"],
            "header_fields": [
                F("From Tax Year", "dd", yr, True, opts=[yr, str(int(yr) - 1)]),
                F("Form", "ro", ea_name, False),
            ],
            "shuttle_left_title": "可选 Earnings 要素",
            "shuttle_right_title": f"已映射到 {ea_name}",
            "left": ["基本工资", "加班费", "全勤奖", "交通津贴", "餐补", "绩效奖金", "年终奖"],
            "right": ["基本工资", "绩效奖金", "年终奖"],
        },
        # ⑥ EC Setting —— 穿梭框(国别雇主申报表名称)
        "ec_setting": {
            "title": f"EC Setting · {ec_name} 配置", "domain": "税务合规",
            "country": cy,
            "desc": f"{cy} 雇主薪酬申报表「{ec_name}」的 Earnings 要素映射",
            "layout": "p_shuttle", "tabs_top": TAX_TABS, "tabs_active": 8,
            "actions": ["Save Changes"],
            "header_fields": [
                F("From Tax Year", "dd", yr, True, opts=[yr, str(int(yr) - 1)]),
                F("Form", "ro", ec_name, False),
            ],
            "shuttle_left_title": "可选 Earnings 要素",
            "shuttle_right_title": f"已映射到 {ec_name}",
            "left": ["基本工资", "加班费", "全勤奖", "交通津贴", "餐补", "绩效奖金"],
            "right": ["基本工资", "加班费"],
        },
    }


# ═══════════════════════════════════════════════════════════
#  🏖️ Leave 假期域
# ═══════════════════════════════════════════════════════════
def _leave_modules(cur: str, country: str = "MY") -> dict:
    return {
        # Leave Entitlement —— Formula 公式编辑器(AI 自然语言生成预埋点)
        "leave_entitlement": {
            "title": "Leave Entitlement · 假期权益", "domain": "假期管理",
            "desc": "定义假期资格规则,支持 Eligibility / Pro Rata / Carry Forward / Advance 多维配置",
            "layout": "p_formula",
            "actions": ["Save Changes", "新增权益"],
            "header_fields": [
                F("Country Code", "ro", country, True),
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
def _ta_modules(cur: str, code: str = "PDS-MY", country: str = "MY") -> dict:
    return {
        # Shift —— 详情表单(含弹性班次单选 + 宽限期)
        "shift": {
            "title": "Shift · 班次", "domain": "考勤管理",
            "desc": "定义班次时间、班别类型、弹性设置、迟到宽限期",
            "layout": "p_detail",
            "actions": ["Save Changes", "+ Add"],
            "fields": [
                F("Company Code", "ro", code, True),
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
                F("Company Code", "ro", code, True),
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
                F("Company Code", "ro", code, True),
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
                F("Country", "dd", _country_name(country), False, opts=_COUNTRY_OPTS),
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
                F("Company Code", "ro", code, True),
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
def _acc_modules(cur: str, code: str = "PDS-MY", country: str = "MY") -> dict:
    return {
        # Chart of Accounts —— Tabset(Chartfields/COA Mapping/Remapping)
        "coa": {
            "title": "Chart of Accounts · 会计科目表", "domain": "财务做账",
            "desc": "配置 Chartfield 1-6 维度、科目映射与重映射",
            "layout": "p_tabset",
            "actions": ["Save Changes", "AI 科目映射"],
            "sub_tabs": ["Chartfields Details", "COA Mapping", "COA Remapping"],
            "fields": [
                F("Company Code", "ro", code, True),
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
def _master_modules(cur: str, code: str = "PDS-MY", country: str = "MY") -> dict:
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
                F("Country", "dd", _country_name(country), True, opts=_COUNTRY_OPTS),
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


# ── 模块文案 i18n 表(domain / 常见 desc 片段 / actions) ──
# title 采用「English · 中文」双语共显,无需翻译;此处只翻 domain / desc / actions
_DOMAIN_EN = {
    "税务合规": "Statutory Tax", "假期管理": "Leave", "考勤管理": "Time & Attendance",
    "财务做账": "Accounting", "主数据": "Master Data",
}
_ACTION_EN = {
    "新增权益": "+ Add Entitlement", "新增类型": "+ Add Type", "新增": "+ Add",
    "新增班次": "+ Add Shift", "新增地点": "+ Add Location", "新增科目": "+ Add Account",
    "新增银行": "+ Add Bank", "新增变量": "+ Add Variable", "新增假期": "+ Add Leave Type",
    "新增排班组": "+ Add Schedule Group", "新增假日": "+ Add Holiday",
    "新增加班规则": "+ Add OT Rule", "新增科目表": "+ Add CoA", "新增分组": "+ Add Group",
    "新增税率": "+ Add Rate", "新增参数": "+ Add Parameter",
    "下载": "Download", "导出": "Export", "导入": "Import", "保存": "Save Changes",
    "AI 自动算税": "AI Auto Tax", "AI智能排班": "AI Smart Roster",
    "AI 异常检测": "AI Anomaly Detect", "AI 自动归集": "AI Auto Collect",
    "AI 科目映射": "AI Account Mapping", "自然语言生成公式": "NL→Formula",
}
_DESC_EN = {
    "leave_entitlement": "Define leave eligibility rules with Eligibility / Pro Rata / Carry Forward / Advance.",
    "tax_rate": "Maintain country tax brackets and rates; supports effective-dated versions.",
    "tax_param": "Statutory tax parameters such as relief, rebate and round rules.",
    "tax_tp1": "Tax exemption (TP1) limit table maintained per category.",
    "tax_receipt": "Statutory tax receipts and submission records.",
    "ea_setting": "Configure EA form fields and mapping for year-end statements.",
    "ec_setting": "Configure EC form fields and mapping.",
    "leave_type": "Define leave types, accrual and approval flow.",
    "leave_group": "Group leave policies for assignment to employees.",
    "shift": "Define work shifts, time bands and break rules.",
    "schedule_group": "Group shifts into rotating schedule patterns.",
    "holiday": "Maintain public-holiday calendar per country.",
    "attendance_loc": "Configure GPS clock-in locations and valid radius.",
    "overtime": "Configure overtime rules, multipliers and approval.",
    "coa": "Maintain the Chart of Accounts hierarchy.",
    "element_group": "Group payroll/expense elements for posting.",
    "gl_account": "Maintain GL account numbers and mapping.",
    "bank": "Maintain bank master data for payment files.",
    "payroll_var": "Define payroll variables used in formulas.",
}


# 字段标签双语词典(源 label 为英文 → 中文)。落库 key 始终用英文(label_key),
# 保证多语言下持久化键一致。前端 pField 已支持 label_key/label_en。
_FIELD_ZH = {
    "Allow Half Day": "允许半天", "BIC / SWIFT": "BIC / SWIFT 代码",
    "Bank Code": "银行代码", "Bank Name": "银行名称",
    "Chartfield 1 (Entity)": "核算字段1(实体)", "Chartfield 2 (Dept)": "核算字段2(部门)",
    "Chartfield 3 (Project)": "核算字段3(项目)", "Chartfield 4 (Cost Center)": "核算字段4(成本中心)",
    "Chartfield 5 (Account)": "核算字段5(科目)", "Chartfield 6 (Future)": "核算字段6(预留)",
    "Company Code": "公司代码", "Country": "国家", "Country Code": "国家代码",
    "Day Type": "日期类型", "Default Entitlement Day(s)": "默认权益天数",
    "Effective Date": "生效日期", "End Time": "结束时间",
    "Entitlement Code": "权益代码", "Entitlement Name": "权益名称",
    "Flexible Shift": "弹性班次", "Form": "表单", "From Tax Year": "起始税务年度",
    "Gender Restriction": "性别限制", "Grace for Late": "迟到宽限",
    "Group Code": "分组代码", "Leave Code": "假期代码", "Leave Name": "假期名称",
    "Location Address": "地点地址", "Location Name": "地点名称",
    "Maximum Radius": "最大半径", "Min. OT Block": "最小加班时段",
    "Min. Service (months)": "最低服务期(月)", "Monthly Overtime Maximum Hours": "每月加班上限(小时)",
    "Paid Leave": "带薪假期", "Postcode": "邮编",
    "Replacement Leave Conversion": "补休折算", "Same for all employee": "全员一致",
    "Schedule Group Code": "排班组代码", "Shift Code": "班次代码",
    "Shift Description": "班次说明", "Start Time": "开始时间", "State": "州/省",
    "Status": "状态", "Tax Category": "税务类别", "Tax Year": "税务年度", "Year": "年度",
}
def _localize_field(f: dict, lang: str) -> dict:
    """翻译单个字段的 label(显示), 并写入 label_key(英文,落库稳定)/label_en。
    注意: opts/value 是枚举数据, 跨语言保持英文统一(避免落库/回显键漂移),
    仅 label 做显示层翻译。"""
    nf = dict(f)
    raw = nf.get("label", "")
    nf["label_key"] = raw          # 英文原文 → 落库 key
    nf["label_en"] = raw
    if lang == "zh":
        nf["label"] = _FIELD_ZH.get(raw, raw)
    else:
        nf["label"] = raw
    return nf


def _localize_module(mod: dict, module_id: str, lang: str) -> dict:
    """按语言本地化模块的 domain / desc / actions / 字段标签(title 双语共显不动)。
    中文模式翻译字段为中文, 英文模式保持英文; 落库 key 始终英文。"""
    m = dict(mod)
    # 字段标签双语(两种语言都处理, 以注入 label_key/label_en)
    for fk in ("fields", "header_fields"):
        if m.get(fk):
            m[fk] = [_localize_field(f, lang) for f in m[fk]]
    if lang != "en":
        return m
    if m.get("domain") in _DOMAIN_EN:
        m["domain"] = _DOMAIN_EN[m["domain"]]
    if module_id in _DESC_EN:
        m["desc"] = _DESC_EN[module_id]
    if m.get("actions"):
        m["actions"] = [_ACTION_EN.get(a, a) for a in m["actions"]]
    if m.get("filters"):
        m["filters"] = [_FILTER_EN.get(f, f) for f in m["filters"]]
    return m


_FILTER_EN = {
    "国家": "Country", "状态": "Status", "类型": "Type", "生效日期": "Effective Date",
    "币种": "Currency", "科目类型": "Account Type", "银行": "Bank", "分组": "Group",
    "年度": "Year", "假期类型": "Leave Type", "地点": "Location",
}


def get_paydaes_module(module_id: str, cur: str = "MYR", lang: str = "zh",
                       country: str = "MY", code: str = "PDS-MY") -> dict | None:
    """返回 Paydaes 6 大域模块视图;不存在返回 None(交回原 18 模块逻辑)。
    country = 公司所属国家代码(SG/MY/TH/VN/ID/HK/CN),税务合规模块据此联动真实税制。
    code    = 当前所选公司的公司代码(如 PDS-SG / HZN-CN),供各模块的 Company Code 字段联动。"""
    registry = {}
    registry.update(_tax_modules(cur, country))
    registry.update(_leave_modules(cur, country))
    registry.update(_ta_modules(cur, code, country))
    registry.update(_acc_modules(cur, code, country))
    registry.update(_master_modules(cur, code, country))
    mod = registry.get(module_id)
    if mod is None:
        return None
    return _localize_module(mod, module_id, lang)


# 供导航树使用:Paydaes 6 大域菜单(全量铺开)
PAYDAES_NAV = [
    {"id": "tax", "name": "税务合规", "name_en": "Statutory Tax", "icon": "fa-percent", "type": "group", "badge": "NEW", "children": [
        {"id": "tax_rate", "name": "税率表", "name_en": "Tax Rate Table", "module": "税率表"},
        {"id": "tax_param", "name": "税务参数", "name_en": "Tax Parameters", "module": "税务参数"},
        {"id": "tax_tp1", "name": "免税限额 (TP1)", "name_en": "Tax Exemption (TP1)", "module": "免税限额"},
        {"id": "tax_receipt", "name": "税务回单", "name_en": "Tax Receipt", "module": "税务回单"},
        {"id": "ea_setting", "name": "EA 表单", "name_en": "EA Setting", "module": "EA表单"},
        {"id": "ec_setting", "name": "EC 表单", "name_en": "EC Setting", "module": "EC表单"},
    ]},
    {"id": "leave", "name": "假期管理", "name_en": "Leave", "icon": "fa-umbrella-beach", "type": "group", "badge": "NEW", "children": [
        {"id": "leave_entitlement", "name": "假期权益", "name_en": "Leave Entitlement", "module": "假期权益"},
        {"id": "leave_type", "name": "假期类型", "name_en": "Leave Type", "module": "假期类型"},
        {"id": "leave_group", "name": "假期组", "name_en": "Leave Group", "module": "假期组"},
    ]},
    {"id": "ta", "name": "考勤管理", "name_en": "Time & Attendance", "icon": "fa-business-time", "type": "group", "badge": "NEW", "children": [
        {"id": "shift", "name": "班次", "name_en": "Shift", "module": "班次"},
        {"id": "schedule_group", "name": "排班组", "name_en": "Schedule Group", "module": "排班组"},
        {"id": "holiday", "name": "假日表", "name_en": "Holiday Schedule", "module": "假日表"},
        {"id": "attendance_loc", "name": "打卡地点", "name_en": "Attendance Location", "module": "打卡地点"},
        {"id": "overtime", "name": "加班设置", "name_en": "Overtime Setting", "module": "加班设置"},
    ]},
    {"id": "accounting", "name": "财务做账", "name_en": "Accounting", "icon": "fa-book", "type": "group", "badge": "NEW", "children": [
        {"id": "coa", "name": "会计科目表", "name_en": "Chart of Accounts", "module": "会计科目表"},
        {"id": "element_group", "name": "要素分组", "name_en": "Element Grouping", "module": "要素分组"},
        {"id": "gl_account", "name": "总账科目", "name_en": "GL Account Number", "module": "总账科目"},
    ]},
    {"id": "master", "name": "主数据", "name_en": "Master Data", "icon": "fa-database", "type": "group", "badge": "NEW", "children": [
        {"id": "bank", "name": "银行", "name_en": "Bank", "module": "银行"},
        {"id": "payroll_var", "name": "薪资变量", "name_en": "Payroll Variable", "module": "薪资变量"},
    ]},
]
