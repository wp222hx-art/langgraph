"""
18 模块工作区视图数据 —— 为每个模块生成专业的表格/表单/卡片结构。
每个模块返回: {title, desc, role_hint, layout, ...内容}
layout: table | form | flow | report | balance | family
"""
from __future__ import annotations

from app.data import mock_db, enterprise


def get_module_view(module_id: str, company: str = "sg") -> dict:
    cc = enterprise.COUNTRIES
    company_info = None
    for g in enterprise.GROUPS:
        for c in g["companies"]:
            if c["id"] == company:
                company_info = c
    cur = company_info["currency"] if company_info else "SGD"
    country = company_info["country"] if company_info else "SG"
    tax = cc.get(country, cc["SG"])["tax"]

    V = {
        # ── 设置 > 基础表 ──
        "claim_type": {
            "title": "报销类型", "desc": "定义费用类别、限额规则、字段显示与薪资要素关联", "layout": "table",
            "actions": ["新增类型", "对话式配置(AI)"],
            "columns": ["编码", "名称", "限额", "限额方式", "需发票", "拆分%", "薪资要素", "分组"],
            "rows": [
                ["MEAL", "餐饮费", f"200 {cur}", "按金额", "是", "50% 个税", "6200", "日常"],
                ["TAXI", "交通费", f"500 {cur}", "按金额", "是", "—", "6100", "日常"],
                ["HOTEL", "住宿费", f"800 {cur}", "按权益", "是", "—", "6100", "差旅"],
                ["FLIGHT", "机票", f"5000 {cur}", "按权益", "是", "—", "6100", "差旅"],
                ["OFFICE", "办公用品", f"1000 {cur}", "按金额", "是", "—", "6300", "日常"],
            ],
        },
        "claim_group": {
            "title": "报销组", "desc": "聚合多个报销类型,管理生效日期,决定员工可见范围", "layout": "table",
            "actions": ["新增组", "管理生效日期"],
            "columns": ["组名", "包含类型", "生效日期", "可见角色", "状态"],
            "rows": [
                ["日常报销组", "餐饮/交通/办公", "2026-01-01", "全员", "✅ 生效"],
                ["差旅报销组", "住宿/机票/高铁", "2026-01-01", "差旅白名单", "✅ 生效"],
                ["福利组", "体检/培训", "2026-01-01", "正式员工", "✅ 生效"],
            ],
        },
        "entitlement": {
            "title": "报销权益", "desc": "定义福利预算,支持按职级差异化、新聘/晋升/离职按比例分配", "layout": "table",
            "actions": ["智能推荐(AI)", "按职级配置"],
            "columns": ["职级", "年度权益", "刷新频率", "比例分配", "适用公司"],
            "rows": [
                ["P7+", f"35000 {cur}", "年度", "按入职日", company_info["name"] if company_info else "—"],
                ["P5-P6", f"25000 {cur}", "年度", "按入职日", "全部"],
                ["P3-P4", f"18000 {cur}", "季度", "按入职日", "全部"],
            ],
        },
        "exchange": {
            "title": "汇率", "desc": "维护多币种汇率,6 位小数精度,支持跨境报销自动换算", "layout": "table",
            "actions": ["自动更新(forex_api)", "手动维护"],
            "columns": ["源币种", "目标币种", "汇率", "更新方式", "更新时间"],
            "rows": [[k, "CNY", f"{v:.6f}", "🔄 自动", "2026-06-06 09:00"] for k, v in mock_db.EXCHANGE_RATES.items()],
        },
        # ── 我的 ──
        "my_claim": {
            "title": "报销申请 · 自助", "desc": "余额摘要、动态字段、附件上传、家属选择、草稿存取", "layout": "self_claim",
            "balance": mock_db.get_balance("E001"),
            "recent": [
                ["C20260601", "餐饮费", f"186 {cur}", "审批中", "2026-06-01"],
                ["C20260598", "交通费", f"88 {cur}", "已支付", "2026-05-28"],
                ["C20260595", "办公用品", f"1280 {cur}", "已支付", "2026-05-25"],
            ],
        },
        "my_travel_req": {
            "title": "商务差旅申请", "desc": "出行前预审批、行程规划、预估费用录入", "layout": "table",
            "actions": ["新建差旅申请", "对话式申请(AI)"],
            "columns": ["申请号", "目的地", "出行日期", "预估费用", "状态"],
            "rows": [
                ["TRV-20260520", "上海", "2026-06-15 ~ 06-17", f"6000 {cur}", "✅ 已批"],
                ["TRV-20260518", "曼谷", "2026-06-20 ~ 06-22", f"8500 {cur}", "审批中"],
            ],
        },
        "my_travel_claim": {
            "title": "商务差旅报销", "desc": "关联已批差旅申请,多维费用(里程/住宿/津贴),实际对比预估", "layout": "table",
            "actions": ["关联预审批报销"],
            "columns": ["报销号", "关联申请", "预估", "实际", "差异", "状态"],
            "rows": [
                ["TC-20260530", "TRV-20260520", f"6000 {cur}", f"5680 {cur}", "-320", "审批中"],
            ],
        },
        # ── 报销数据(管理)──
        "mgr_claim": _approval_view(cur, "报销申请 · 管理", "批量审批/拒绝/退回,交易级勾选,保留退回历史"),
        "mgr_travel_req": _approval_view(cur, "差旅申请 · 管理", "差旅预审批管理,合规审核"),
        "mgr_travel_claim": _approval_view(cur, "差旅报销 · 管理", "差旅报销审核,实际对比预估"),
        # ── 报销流程 ──
        "payroll_if": {
            "title": "报销接口流程", "desc": "批量检索已批报销、生成接口文件、批处理代码管理、支持回滚", "layout": "flow",
            "steps": [
                {"step": "检索已批报销", "status": "完成", "result": "126 笔"},
                {"step": "生成接口文件", "status": "完成", "result": "payroll_20260606.txt"},
                {"step": "推送薪资系统", "status": "进行中", "result": "Paydaes Payroll"},
                {"step": "回写报销状态", "status": "待执行", "result": "—"},
            ],
            "batch_code": "BATCH-20260606", "rollback": True,
        },
        "gen_entitlement": {
            "title": "生成权益流程", "desc": "年度权益批量生成与分配,新聘/晋升按比例", "layout": "flow",
            "steps": [
                {"step": "读取职级配置", "status": "完成", "result": "3 档"},
                {"step": "计算按比例分配", "status": "完成", "result": "320 人"},
                {"step": "生成权益包", "status": "完成", "result": "320 份"},
                {"step": "通知员工", "status": "完成", "result": "已推送"},
            ],
            "batch_code": "ENT-2026", "rollback": False,
        },
        # ── 审核 ──
        "audit_if": {
            "title": "审核接口数据", "desc": "推送薪资前最后的数据完整性校验,异常对话式修正", "layout": "table",
            "actions": ["重新校验", "AI 异常报告"],
            "columns": ["批次", "单据数", "校验状态", "异常数", "操作人"],
            "rows": [
                ["BATCH-20260606", "126", "✅ 通过", "0", "薪资专员"],
                ["BATCH-20260520", "98", "⚠️ 警告", "2", "薪资专员"],
            ],
        },
        "balance_adj": {
            "title": "审核 / 调整报销余额", "desc": "增加、减少、转移余额,必填原因,全留痕审计", "layout": "balance",
            "balance": mock_db.get_balance("E001"),
            "history": [
                ["2026-05-20", "增加", f"+2000 {cur}", "年中权益追加", "财务-王芳"],
                ["2026-03-15", "减少", f"-500 {cur}", "误录修正", "财务-王芳"],
            ],
        },
        # ── 报表 ──
        "rpt_benefit": _report_view("福利使用报表", "使用率分析、权益余额追踪"),
        "rpt_travel": _report_view("差旅申请报表", "预估 vs 实际、KPI 分析"),
        "rpt_claim": _report_view("报销申请报表", "全维度明细、批处理代码追溯、一键生成 PPT"),
        # ── 核心HR ──
        "family": {
            "title": "家庭信息", "desc": "管理员工家属档案,用于关联家属报销", "layout": "family",
            "actions": ["新增家属", "对话式登记(AI)"],
            "members": mock_db.FAMILY.get("E001", []) + [{"relation": "子女", "name": "张小妹"}],
        },
    }
    return V.get(module_id, {"title": module_id, "desc": "模块开发中", "layout": "table", "columns": [], "rows": []})


def _approval_view(cur, title, desc):
    rows = [[c["id"], c["user"], c["type"], f"{c['amount']} {cur}", c["risk"], c["note"]] for c in mock_db.PENDING_CLAIMS]
    return {
        "title": title, "desc": desc, "layout": "approval",
        "actions": ["一键批量通过", "AI 风险分级"],
        "columns": ["单号", "申请人", "类型", "金额", "风险", "备注"],
        "rows": rows,
        "summary": {"低": len([c for c in mock_db.PENDING_CLAIMS if c["risk"] == "低"]),
                    "中": len([c for c in mock_db.PENDING_CLAIMS if c["risk"] == "中"]),
                    "高": len([c for c in mock_db.PENDING_CLAIMS if c["risk"] == "高"])},
    }


def _report_view(title, desc):
    data = mock_db.mock_report_data(title)
    return {"title": title, "desc": desc, "layout": "report",
            "actions": ["NL2SQL 查询(AI)", "导出 PPT", "导出 Excel"],
            "chart": {"labels": data["labels"], "series": data["series"], "kind": "bar"},
            "insight": data["insight"]}
