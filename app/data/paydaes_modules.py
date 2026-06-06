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


def get_paydaes_module(module_id: str, cur: str = "MYR") -> dict | None:
    """返回 Paydaes 6 大域模块视图;不存在返回 None(交回原 18 模块逻辑)"""
    registry = {}
    registry.update(_tax_modules(cur))
    return registry.get(module_id)


# 供导航树使用:Paydaes 6 大域菜单(分阶段开放,先开 Tax)
PAYDAES_NAV = [
    {"id": "tax", "name": "税务合规", "icon": "fa-percent", "type": "group", "badge": "NEW", "children": [
        {"id": "tax_rate", "name": "Tax Rate Table", "module": "税率表"},
        {"id": "tax_param", "name": "Tax Parameters", "module": "税务参数"},
        {"id": "tax_tp1", "name": "Tax Exemption (TP1)", "module": "免税限额"},
        {"id": "tax_receipt", "name": "Tax Receipt", "module": "税务回单"},
        {"id": "ea_setting", "name": "EA Setting", "module": "EA表单"},
        {"id": "ec_setting", "name": "EC Setting", "module": "EC表单"},
    ]},
]
