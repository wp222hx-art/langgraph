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
    {"id": "cockpit", "name": "AI 老板驾驶舱", "name_en": "AI Boss Cockpit", "icon": "fa-gauge-high", "type": "page", "badge": "AI"},
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

# ═══════════════════════════════════════════════
# 工作台待办 —— 按公司"活数据"派生(待办数量随该公司报销规模/待处理量浮动)
# ═══════════════════════════════════════════════
import hashlib as _hashlib


def _seed(key: str) -> float:
    """字符串 → 0~1 确定性伪随机(保证 Demo 可复现)。"""
    return int(_hashlib.md5(key.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def dashboard_todos(company_id: str = "sg"):
    """按公司动态待办:数量与该公司「待处理报销笔数 / 适用税率 / 规模」联动,
    而非全公司一模一样的死常量。"""
    kpi = dashboard_kpi(company_id)
    pending = int(kpi[2]["value"])          # 待处理报销笔数(本月)
    tax_rate = kpi[3]["value"]              # 适用税率
    claims = int(kpi[0]["value"])           # 本月报销单
    # 由规模派生各类待办数量(确定性,贴合该公司体量)
    high_risk = max(1, round(pending * 0.35))
    promo = max(1, round(claims * 0.02 * (0.6 + _seed(company_id + "promo"))))
    over_limit = max(0, round(pending * 0.12))
    cur_label = {"sg": "SGD", "my": "MYR", "th": "THB", "vn": "VND",
                 "id": "IDR", "hk": "HKD", "cn": "CNY"}.get(company_id, "")
    todos = [
        {"title": f"{high_risk} 笔高风险报销待审批",
         "title_en": f"{high_risk} high-risk claims to approve",
         "type": "审批", "type_en": "Approval", "level": "high", "agent": "ApprovalCopilot"},
        {"title": f"本月薪资接口待跑批（{cur_label} · {tax_rate}% 税率）",
         "title_en": f"Monthly payroll interface pending ({cur_label} · {tax_rate}% tax)",
         "type": "流程", "type_en": "Flow", "level": "mid", "agent": "PayrollNavigator"},
        {"title": f"{promo} 名晋升员工权益待重算",
         "title_en": f"{promo} promoted staff entitlements to recompute",
         "type": "权益", "type_en": "Entitlement", "level": "mid", "agent": "HRStrategist"},
    ]
    if over_limit > 0:
        todos.append({
            "title": f"差旅报销超标 {over_limit} 笔需复核",
            "title_en": f"{over_limit} over-limit travel claim(s) to review",
            "type": "审核", "type_en": "Audit", "level": "high", "agent": "ApprovalCopilot"})
    return todos


def dashboard_chart(company_id: str = "sg"):
    """按公司动态趋势图:6 月报销/差旅曲线锚定该公司「本月报销单」量级,
    叠加确定性月度波动,使各公司图表各不相同(活数据)。"""
    kpi = dashboard_kpi(company_id)
    base_claim = max(8.0, kpi[0]["value"] * 0.6)   # 报销总额(万)基准,锚定本月报销量
    claim_series, travel_series = [], []
    for i, mon in enumerate(["1月", "2月", "3月", "4月", "5月", "6月"]):
        # 逐月增长 + 公司确定性波动
        growth = 0.82 + i * 0.04
        wobble = 0.85 + _seed(company_id + mon) * 0.30
        c = round(base_claim * growth * wobble, 1)
        t = round(c * (0.22 + _seed(company_id + mon + "tv") * 0.12), 1)  # 差旅约占 22~34%
        claim_series.append(c)
        travel_series.append(t)
    return {
        "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
        "labels_en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "series": [
            {"name": "报销总额(万)", "name_en": "Total Claims (10k)", "data": claim_series},
            {"name": "差旅支出(万)", "name_en": "Travel Spend (10k)", "data": travel_series},
        ],
    }


# 向后兼容:保留默认常量(默认 sg),旧引用不报错
TODOS = dashboard_todos("sg")
DASHBOARD_CHART = dashboard_chart("sg")
