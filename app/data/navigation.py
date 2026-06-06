"""
企业级导航结构(按文档第三章"产品结构目录"真实菜单层级)
+ 工作台 KPI / 待办 / 18 模块工作区内容
"""
from __future__ import annotations

# ═══════════════════════════════════════════════
# 左侧多级导航树(对应文档 3.1 一级导航结构图)
# ═══════════════════════════════════════════════
NAV_TREE = [
    {"id": "dashboard", "name": "工作台", "name_en": "Dashboard", "icon": "fa-gauge-high", "type": "page"},
    {"id": "settings", "name": "设置", "name_en": "Settings", "icon": "fa-gear", "type": "group", "children": [
        {"id": "claim_type", "name": "报销类型", "name_en": "Claim Type", "module": "报销类型"},
        {"id": "claim_group", "name": "报销组", "name_en": "Claim Group", "module": "报销组"},
        {"id": "entitlement", "name": "报销权益", "name_en": "Entitlement", "module": "报销权益"},
        {"id": "exchange", "name": "汇率", "name_en": "Exchange Rate", "module": "汇率"},
    ]},
    {"id": "my", "name": "我的", "name_en": "My Space", "icon": "fa-folder-open", "type": "group", "children": [
        {"id": "my_claim", "name": "报销申请", "name_en": "My Claim", "module": "报销申请-自助"},
        {"id": "my_travel_req", "name": "商务差旅申请", "name_en": "Travel Request", "module": "商务差旅申请-自助"},
        {"id": "my_travel_claim", "name": "商务差旅报销", "name_en": "Travel Claim", "module": "商务差旅报销-自助"},
    ]},
    {"id": "claim_data", "name": "报销数据", "name_en": "Claim Data", "icon": "fa-clipboard-list", "type": "group", "children": [
        {"id": "mgr_claim", "name": "报销申请(管理)", "name_en": "Claim (Manage)", "module": "报销申请-管理"},
        {"id": "mgr_travel_req", "name": "差旅申请(管理)", "name_en": "Travel Req (Manage)", "module": "差旅申请-管理"},
        {"id": "mgr_travel_claim", "name": "差旅报销(管理)", "name_en": "Travel Claim (Manage)", "module": "差旅报销-管理"},
    ]},
    {"id": "claim_flow", "name": "报销流程", "name_en": "Claim Flow", "icon": "fa-diagram-project", "type": "group", "children": [
        {"id": "payroll_if", "name": "报销接口流程", "name_en": "Payroll Interface", "module": "报销接口流程"},
        {"id": "gen_entitlement", "name": "生成权益流程", "name_en": "Generate Entitlement", "module": "生成权益流程"},
    ]},
    {"id": "audit", "name": "审核", "name_en": "Audit", "icon": "fa-magnifying-glass-chart", "type": "group", "children": [
        {"id": "audit_if", "name": "审核接口数据", "name_en": "Audit Interface Data", "module": "审核接口数据"},
        {"id": "balance_adj", "name": "审核调整报销余额", "name_en": "Balance Adjustment", "module": "余额调整"},
    ]},
    {"id": "report", "name": "报表", "name_en": "Reports", "icon": "fa-chart-pie", "type": "group", "children": [
        {"id": "rpt_benefit", "name": "福利使用报表", "name_en": "Benefits Usage", "module": "福利使用报表"},
        {"id": "rpt_travel", "name": "差旅申请报表", "name_en": "Travel Report", "module": "差旅申请报表"},
        {"id": "rpt_claim", "name": "报销申请报表", "name_en": "Claim Report", "module": "报销申请报表"},
    ]},
    {"id": "hr", "name": "核心HR", "name_en": "Core HR", "icon": "fa-users", "type": "group", "children": [
        {"id": "family", "name": "家庭信息", "name_en": "Family Info", "module": "家庭信息"},
    ]},
    {"id": "global", "name": "全球合规中心", "name_en": "Global Compliance", "icon": "fa-earth-asia", "type": "page", "badge": "NEW"},
]

# ═══════════════════════════════════════════════
# 工作台 KPI(按公司动态,这里给默认)
# ═══════════════════════════════════════════════
def dashboard_kpi(company_id: str = "sg"):
    base = {
        "sg": [120, 86, 12, 9.2], "my": [98, 72, 8, 6.0], "th": [76, 65, 15, 7.0],
        "vn": [64, 58, 6, 10.0], "id": [142, 110, 21, 11.0], "hk": [42, 30, 3, 0.0], "cn": [210, 180, 28, 6.0],
    }.get(company_id, [120, 86, 12, 9.2])
    return [
        {"label": "本月报销单", "label_en": "Claims This Month", "value": base[0], "unit": "笔", "unit_en": "", "trend": "+12%", "icon": "fa-receipt", "color": "#20c997"},
        {"label": "已审批", "label_en": "Approved", "value": base[1], "unit": "笔", "unit_en": "", "trend": "+8%", "icon": "fa-circle-check", "color": "#10b981"},
        {"label": "待处理", "label_en": "Pending", "value": base[2], "unit": "笔", "unit_en": "", "trend": "需关注", "trend_en": "Attention", "icon": "fa-clock", "color": "#f59e0b"},
        {"label": "适用税率", "label_en": "Tax Rate", "value": base[3], "unit": "%", "unit_en": "%", "trend": "本地", "trend_en": "Local", "icon": "fa-percent", "color": "#ec4899"},
    ]

TODOS = [
    {"title": "3 笔高风险报销待审批", "title_en": "3 high-risk claims to approve", "type": "审批", "type_en": "Approval", "level": "high", "agent": "ApprovalCopilot"},
    {"title": "本月薪资接口待跑批", "title_en": "Monthly payroll interface pending", "type": "流程", "type_en": "Flow", "level": "mid", "agent": "PayrollNavigator"},
    {"title": "2 名晋升员工权益待重算", "title_en": "2 promoted staff entitlements to recompute", "type": "权益", "type_en": "Entitlement", "level": "mid", "agent": "HRStrategist"},
    {"title": "差旅报销超标 1 笔需复核", "title_en": "1 over-limit travel claim to review", "type": "审核", "type_en": "Audit", "level": "high", "agent": "ApprovalCopilot"},
]

DASHBOARD_CHART = {
    "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
    "labels_en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    "series": [
        {"name": "报销总额(万)", "name_en": "Total Claims (10k)", "data": [45, 52, 38, 61, 72, 58]},
        {"name": "差旅支出(万)", "name_en": "Travel Spend (10k)", "data": [12, 15, 9, 18, 22, 16]},
    ],
}
