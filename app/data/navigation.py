"""
企业级导航结构(按文档第三章"产品结构目录"真实菜单层级)
+ 工作台 KPI / 待办 / 18 模块工作区内容
"""
from __future__ import annotations

# ═══════════════════════════════════════════════
# 左侧多级导航树(对应文档 3.1 一级导航结构图)
# ═══════════════════════════════════════════════
NAV_TREE = [
    {"id": "dashboard", "name": "工作台", "icon": "fa-gauge-high", "type": "page"},
    {"id": "settings", "name": "设置", "icon": "fa-gear", "type": "group", "children": [
        {"id": "claim_type", "name": "报销类型", "module": "报销类型"},
        {"id": "claim_group", "name": "报销组", "module": "报销组"},
        {"id": "entitlement", "name": "报销权益", "module": "报销权益"},
        {"id": "exchange", "name": "汇率", "module": "汇率"},
    ]},
    {"id": "my", "name": "我的", "icon": "fa-folder-open", "type": "group", "children": [
        {"id": "my_claim", "name": "报销申请", "module": "报销申请-自助"},
        {"id": "my_travel_req", "name": "商务差旅申请", "module": "商务差旅申请-自助"},
        {"id": "my_travel_claim", "name": "商务差旅报销", "module": "商务差旅报销-自助"},
    ]},
    {"id": "claim_data", "name": "报销数据", "icon": "fa-clipboard-list", "type": "group", "children": [
        {"id": "mgr_claim", "name": "报销申请(管理)", "module": "报销申请-管理"},
        {"id": "mgr_travel_req", "name": "差旅申请(管理)", "module": "差旅申请-管理"},
        {"id": "mgr_travel_claim", "name": "差旅报销(管理)", "module": "差旅报销-管理"},
    ]},
    {"id": "claim_flow", "name": "报销流程", "icon": "fa-diagram-project", "type": "group", "children": [
        {"id": "payroll_if", "name": "报销接口流程", "module": "报销接口流程"},
        {"id": "gen_entitlement", "name": "生成权益流程", "module": "生成权益流程"},
    ]},
    {"id": "audit", "name": "审核", "icon": "fa-magnifying-glass-chart", "type": "group", "children": [
        {"id": "audit_if", "name": "审核接口数据", "module": "审核接口数据"},
        {"id": "balance_adj", "name": "审核调整报销余额", "module": "余额调整"},
    ]},
    {"id": "report", "name": "报表", "icon": "fa-chart-pie", "type": "group", "children": [
        {"id": "rpt_benefit", "name": "福利使用报表", "module": "福利使用报表"},
        {"id": "rpt_travel", "name": "差旅申请报表", "module": "差旅申请报表"},
        {"id": "rpt_claim", "name": "报销申请报表", "module": "报销申请报表"},
    ]},
    {"id": "hr", "name": "核心HR", "icon": "fa-users", "type": "group", "children": [
        {"id": "family", "name": "家庭信息", "module": "家庭信息"},
    ]},
    {"id": "global", "name": "全球合规中心", "icon": "fa-earth-asia", "type": "page", "badge": "NEW"},
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
        {"label": "本月报销单", "value": base[0], "unit": "笔", "trend": "+12%", "icon": "fa-receipt", "color": "#20c997"},
        {"label": "已审批", "value": base[1], "unit": "笔", "trend": "+8%", "icon": "fa-circle-check", "color": "#10b981"},
        {"label": "待处理", "value": base[2], "unit": "笔", "trend": "需关注", "icon": "fa-clock", "color": "#f59e0b"},
        {"label": "适用税率", "value": base[3], "unit": "%", "trend": "本地", "icon": "fa-percent", "color": "#ec4899"},
    ]

TODOS = [
    {"title": "3 笔高风险报销待审批", "type": "审批", "level": "high", "agent": "ApprovalCopilot"},
    {"title": "本月薪资接口待跑批", "type": "流程", "level": "mid", "agent": "PayrollNavigator"},
    {"title": "2 名晋升员工权益待重算", "type": "权益", "level": "mid", "agent": "HRStrategist"},
    {"title": "差旅报销超标 1 笔需复核", "type": "审核", "level": "high", "agent": "ApprovalCopilot"},
]

DASHBOARD_CHART = {
    "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
    "series": [
        {"name": "报销总额(万)", "data": [45, 52, 38, 61, 72, 58]},
        {"name": "差旅支出(万)", "data": [12, 15, 9, 18, 22, 16]},
    ],
}
