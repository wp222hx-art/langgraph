"""
18 模块工作区视图数据 —— 为每个模块生成专业的表格/表单/卡片结构。
每个模块返回: {title, desc, role_hint, layout, ...内容}
layout: table | form | flow | report | balance | family
"""
from __future__ import annotations

from app.data import mock_db, enterprise, db


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
        "claim_type": _claim_type_view(company, cur),
        "claim_group": {
            "title": "报销组", "desc": "聚合多个报销类型,管理生效日期,决定员工可见范围", "layout": "table",
            "actions": ["新增组", "管理生效日期"],
            "columns": ["组名", "包含类型", "生效日期", "可见角色", "状态"],
            "rows": [
                ["日常报销组", "餐饮/交通/办公", "2026-01-01", "全员", "✅ 生效"],
                ["差旅报销组", "住宿/机票/高铁", "2026-01-01", "差旅白名单", "✅ 生效"],
                ["福利组", "体检/培训", "2026-01-01", "正式员工", "✅ 生效"],
            ],
            "crud": {"module_id": "claim_group", "action": "新增组", "fields": [
                {"key": "组名", "label": "组名", "type": "text", "required": True},
                {"key": "包含类型", "label": "包含类型", "type": "text", "placeholder": "餐饮/交通/办公"},
                {"key": "生效日期", "label": "生效日期", "type": "date"},
                {"key": "可见角色", "label": "可见角色", "type": "text", "placeholder": "全员"},
                {"key": "状态", "label": "状态", "type": "select", "options": ["✅ 生效", "草稿"]},
            ]},
        },
        "entitlement": {
            "title": "报销权益", "desc": "定义福利预算,支持按职级差异化、新聘/晋升/离职按比例分配", "layout": "table",
            "actions": ["新增权益", "智能推荐(AI)"],
            "columns": ["职级", "年度权益", "刷新频率", "比例分配", "适用公司"],
            "rows": [
                ["P7+", f"35000 {cur}", "年度", "按入职日", company_info["name"] if company_info else "—"],
                ["P5-P6", f"25000 {cur}", "年度", "按入职日", "全部"],
                ["P3-P4", f"18000 {cur}", "季度", "按入职日", "全部"],
            ],
            "crud": {"module_id": "entitlement", "action": "新增权益", "fields": [
                {"key": "职级", "label": "职级", "type": "text", "required": True, "placeholder": "P5-P6"},
                {"key": "年度权益", "label": f"年度权益({cur})", "type": "text", "required": True},
                {"key": "刷新频率", "label": "刷新频率", "type": "select", "options": ["年度", "季度", "月度"]},
                {"key": "比例分配", "label": "比例分配", "type": "text", "placeholder": "按入职日"},
                {"key": "适用公司", "label": "适用公司", "type": "text", "placeholder": "全部"},
            ]},
        },
        "exchange": {
            "title": "汇率", "desc": "维护多币种汇率,6 位小数精度,支持跨境报销自动换算", "layout": "table",
            "actions": ["新增汇率", "自动更新(forex_api)"],
            "columns": ["源币种", "目标币种", "汇率", "更新方式", "更新时间"],
            "rows": [[k, "CNY", f"{v:.6f}", "🔄 自动", "2026-06-06 09:00"] for k, v in mock_db.EXCHANGE_RATES.items()],
            "crud": {"module_id": "exchange", "action": "新增汇率", "fields": [
                {"key": "源币种", "label": "源币种", "type": "text", "required": True, "placeholder": "USD"},
                {"key": "目标币种", "label": "目标币种", "type": "text", "required": True, "placeholder": "CNY"},
                {"key": "汇率", "label": "汇率", "type": "text", "required": True, "placeholder": "7.180000"},
                {"key": "更新方式", "label": "更新方式", "type": "select", "options": ["✍️ 手动", "🔄 自动"]},
                {"key": "更新时间", "label": "更新时间", "type": "text", "placeholder": "自动填当前"},
            ]},
        },
        # ── 我的 ──
        "my_claim": {
            "title": "报销申请 · 自助", "desc": "余额摘要、动态字段、附件上传、家属选择、草稿存取", "layout": "self_claim",
            "balance": {**mock_db.get_balance("E001"), "currency": cur},
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
            "crud": {"module_id": "my_travel_req", "action": "新建差旅申请", "fields": [
                {"key": "申请号", "label": "申请号", "type": "text", "placeholder": "自动生成可留空"},
                {"key": "目的地", "label": "目的地", "type": "text", "required": True},
                {"key": "出行日期", "label": "出行日期", "type": "text", "required": True, "placeholder": "2026-06-15 ~ 06-17"},
                {"key": "预估费用", "label": f"预估费用({cur})", "type": "text", "required": True},
                {"key": "状态", "label": "状态", "type": "select", "options": ["审批中", "✅ 已批", "草稿"]},
            ]},
        },
        "my_travel_claim": {
            "title": "商务差旅报销", "desc": "关联已批差旅申请,多维费用(里程/住宿/津贴),实际对比预估", "layout": "table",
            "actions": ["关联预审批报销"],
            "columns": ["报销号", "关联申请", "预估", "实际", "差异", "状态"],
            "rows": [
                ["TC-20260530", "TRV-20260520", f"6000 {cur}", f"5680 {cur}", "-320", "审批中"],
            ],
            "crud": {"module_id": "my_travel_claim", "action": "关联预审批报销", "fields": [
                {"key": "报销号", "label": "报销号", "type": "text", "placeholder": "自动生成可留空"},
                {"key": "关联申请", "label": "关联差旅申请号", "type": "text", "required": True, "placeholder": "TRV-..."},
                {"key": "预估", "label": f"预估({cur})", "type": "text", "required": True},
                {"key": "实际", "label": f"实际({cur})", "type": "text", "required": True},
                {"key": "差异", "label": "差异", "type": "text", "placeholder": "自动可留空"},
                {"key": "状态", "label": "状态", "type": "select", "options": ["审批中", "✅ 已批"]},
            ]},
        },
        # ── 报销数据(管理)──
        "mgr_claim": _approval_view(cur, "报销申请 · 管理", "批量审批/拒绝/退回,交易级勾选,保留退回历史", company),
        "mgr_travel_req": _approval_view(cur, "差旅申请 · 管理", "差旅预审批管理,合规审核", company),
        "mgr_travel_claim": _approval_view(cur, "差旅报销 · 管理", "差旅报销审核,实际对比预估", company),
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
            "title": "家庭信息", "desc": "管理员工家属档案,用于关联家属报销(真实数据库)", "layout": "family",
            "actions": ["对话式登记(AI)"],
            "members": [{"relation": m.get("relation"), "name": m.get("name")}
                        for m in db.get_family(None, company)],
        },
    }
    view = V.get(module_id, {"title": module_id, "desc": "模块开发中", "layout": "table", "columns": [], "rows": []})
    # 合并用户真新增的自定义记录(置顶,标记 NEW),让"新增"立即可见
    crud = view.get("crud")
    if crud and view.get("layout") == "table":
        cols = view.get("columns", [])
        recs = db.list_module_records(crud["module_id"], company)
        extra = []
        for rec in recs:
            p = rec.get("payload", {})
            extra.append([p.get(c, "—") or "—" for c in cols] + [f"__rec:{rec['id']}"])
        if extra:
            # 给原有静态行补一个空操作位,保证列对齐
            view["rows"] = [r + ["__seed"] for r in view.get("rows", [])]
            view["rows"] = extra + view["rows"]
            view["has_record_col"] = True
    return view


def _claim_type_view(company: str, cur: str) -> dict:
    """报销类型 —— 读真实数据库(claim_types),支持真新增/删除。"""
    types = db.get_claim_types(company)
    rows = []
    for t_ in types:
        need = "是" if t_.get("need_invoice") else "否"
        rows.append([
            t_.get("code", ""), t_.get("name", ""),
            f"{t_.get('limit_amt', 0):g} {cur}", "按金额", need,
            "—", "—", t_.get("grp", "日常"),
            f"__type:{t_.get('code', '')}",   # 末列:删除句柄
        ])
    return {
        "title": "报销类型", "desc": "定义费用类别、限额规则、字段显示与薪资要素关联（真实数据库）",
        "layout": "table", "actions": ["新增类型", "对话式配置(AI)"],
        "columns": ["编码", "名称", "限额", "限额方式", "需发票", "拆分%", "薪资要素", "分组"],
        "rows": rows, "has_record_col": True,
        "crud": {"module_id": "claim_type", "action": "新增类型", "kind": "claim_type", "fields": [
            {"key": "code", "label": "编码", "type": "text", "required": True, "placeholder": "如 TRAIN"},
            {"key": "name", "label": "名称", "type": "text", "required": True, "placeholder": "如 高铁费"},
            {"key": "name_en", "label": "英文名", "type": "text", "placeholder": "Train"},
            {"key": "grp", "label": "分组", "type": "select", "options": ["日常", "差旅", "福利"]},
            {"key": "limit_amt", "label": f"限额({cur})", "type": "number", "required": True, "placeholder": "2000"},
            {"key": "need_invoice", "label": "需发票", "type": "select", "options": ["是", "否"]},
        ]},
    }


def _approval_view(cur, title, desc, company="sg"):
    """审批端读真实数据库的待审单(status=pending),审批按钮接 decide API 真改状态。"""
    claims = db.list_claims(company, status="pending", limit=100)
    rows = [[c["id"], c.get("emp_name", "—"), c.get("type_name", c.get("type_code", "")),
             f"{c.get('amount', 0):g} {c.get('currency', cur)}",
             c.get("risk_level", "低"), c.get("note", "") or "—"] for c in claims]
    lvl = [c.get("risk_level", "低") for c in claims]
    return {
        "title": title, "desc": desc + "(真实数据库 · 审批即改状态)", "layout": "approval",
        "actions": ["AI 风险分级"],
        "columns": ["单号", "申请人", "类型", "金额", "风险", "备注"],
        "rows": rows,
        "summary": {"低": lvl.count("低"), "中": lvl.count("中"), "高": lvl.count("高")},
    }


def _report_view(title, desc):
    data = mock_db.mock_report_data(title)
    return {"title": title, "desc": desc, "layout": "report",
            "actions": ["NL2SQL 查询(AI)", "导出 PPT", "导出 Excel"],
            "chart": {"labels": data["labels"], "series": data["series"], "kind": "bar"},
            "insight": data["insight"]}
