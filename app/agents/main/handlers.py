"""
5 个主 Agent (User-Facing Agents)
每个主 Agent 负责"理解+表达",内部调度 8 个子 Agent 完成名下模块。
覆盖全部 18 个业务模块。

返回结构统一为 dict: {reply, cards, think, needs_human, hil_level}
"""
from __future__ import annotations

from typing import Any

from app.agents.sub import workers
from app.data import mock_db


def _think(agent: str, action: str, detail: str = "") -> dict:
    return {"agent": agent, "action": action, "detail": detail}


# ═══════════════════════════════════════════════
# 🙋 ClaimMate — 员工报销伙伴
# 模块: ⑤报销申请-自助 ⑥差旅申请-自助 ⑦差旅报销-自助 ⑱家庭信息
# ═══════════════════════════════════════════════
def claim_mate(state: dict) -> dict[str, Any]:
    text = state["user_input"]
    module = state.get("module", "报销申请-自助")
    think, cards = [], []

    if module == "家庭信息":
        think.append(_think("ConversationAgent", "登记家属信息"))
        fam = mock_db.FAMILY.get("E001", [])
        cards.append({"type": "family", "title": "我的家属档案", "data": {"members": fam or [{"relation": "配偶", "name": "刘敏"}]}})
        return {"reply": "已为你登记/查询家属信息 👨‍👩‍👧。家属报销时我会自动关联他们的档案,无需重复填写。",
                "cards": cards, "think": think, "needs_human": False, "hil_level": "L4"}

    if "余额" in text or "剩多少" in text or "还能报" in text:
        think.append(_think("WorkflowAgent", "查询权益余额"))
        bal = mock_db.get_balance("E001")
        cards.append({"type": "entitlement", "title": "我的报销额度", "data": bal})
        return {"reply": f"你好 {bal['name']} 😊 你的年度额度 {bal['annual']} 元,已用 {bal['used']} 元,还剩 **{bal['remaining']} 元**。需要我帮你报销点什么吗?",
                "cards": cards, "think": think, "needs_human": False, "hil_level": "L4"}

    # 报销提交主链路:意图已识别 → OCR抽取 → 校验 → 风险
    think.append(_think("ExtractionAgent", "识别发票", "多模态 OCR 抽取金额/商户/品类"))
    ext = workers.extraction_agent(text)["extracted"]

    think.append(_think("ValidationAgent", "合规校验", "比对报销类型与限额"))
    val = workers.validation_agent(ext)["validation"]

    think.append(_think("RiskAgent", "风险评分", "反欺诈与超限检测"))
    risk = workers.risk_agent(ext, val)["risk"]

    is_travel = "差旅" in module
    claim_card = {
        "type": "claim",
        "title": "差旅报销单(AI 已填好)" if is_travel else "报销单(AI 已填好)",
        "data": {**ext, "校验": "✅ 通过" if val["passed"] else "⚠️ " + "; ".join(val["issues"]),
                 "风险等级": risk["level"]},
    }
    cards.append(claim_card)

    if is_travel and module == "商务差旅报销-自助":
        cards.append({"type": "table", "title": "已自动关联的差旅预审批",
                      "data": {"rows": [["预审批单号", "TRV-20260520"], ["目的地", "上海"], ["预算", "6000 元"]]}})

    reply = f"📸 我识别到这是【{ext['merchant']}】的{ext['category']},金额 {ext['amount']} 元。"
    if val["passed"]:
        reply += "校验通过,已为你填好报销单,确认即可提交 ✅"
    else:
        reply += "不过 " + "; ".join(val["issues"]) + "。要我帮你拆分或说明原因吗?"

    return {"reply": reply, "cards": cards, "think": think,
            "needs_human": False, "hil_level": "L4"}


# ═══════════════════════════════════════════════
# ✅ ApprovalCopilot — 审批副驾
# 模块: ⑧报销申请-管理 ⑨差旅申请-管理 ⑩差旅报销-管理
# ═══════════════════════════════════════════════
def approval_copilot(state: dict) -> dict[str, Any]:
    think, cards = [], []
    think.append(_think("RiskAgent", "风险分级", "对全部待审单据做风险评分"))
    think.append(_think("PolicyAgent", "政策推理", "应用审批规则"))

    claims = mock_db.PENDING_CLAIMS
    low = [c for c in claims if c["risk"] == "低"]
    high = [c for c in claims if c["risk"] == "高"]
    mid = [c for c in claims if c["risk"] == "中"]

    rows = [[c["id"], c["user"], c["type"], f"{c['amount']}元", c["risk"], c["note"]] for c in claims]
    cards.append({"type": "approval", "title": "待审批单据(已风险分级)",
                  "data": {"headers": ["单号", "申请人", "类型", "金额", "风险", "备注"], "rows": rows,
                           "summary": {"低风险": len(low), "中风险": len(mid), "高风险": len(high)}}})

    reply = (f"📋 共 {len(claims)} 张待审单据,我已完成风险分级:\n"
             f"- 🟢 低风险 {len(low)} 张 → 建议**一键批量通过**\n"
             f"- 🟡 中风险 {len(mid)} 张 → 建议快速复核\n"
             f"- 🔴 高风险 {len(high)} 张 → **需你人工决策**(我仅提供建议)\n\n"
             f"高风险单据涉及超标/超限,按 L2 协同规则,最终审批权在你手上。是否对高风险单据逐一处理?")

    # 高风险触发人机协同(Human-in-the-loop)
    return {"reply": reply, "cards": cards, "think": think,
            "needs_human": True, "hil_level": "L2",
            "hil_items": high}


# ═══════════════════════════════════════════════
# 🧠 HRStrategist — HR 战略顾问
# 模块: ①报销类型 ②报销组 ③报销权益 ⑫生成权益流程 ⑭余额调整
# ═══════════════════════════════════════════════
def hr_strategist(state: dict) -> dict[str, Any]:
    text = state["user_input"]
    module = state.get("module", "报销类型")
    think, cards = [], []

    think.append(_think("PolicyAgent", "政策推理", f"为「{module}」生成智能配置建议"))
    policy = workers.policy_agent(module, text)["policy"]

    if module == "报销类型":
        cards.append({"type": "table", "title": "现有报销类型",
                      "data": {"headers": ["编码", "名称", "限额", "分组"],
                               "rows": [[t["code"], t["name"], f"{t['limit']}元", t["group"]] for t in mock_db.CLAIM_TYPES]}})
        reply = f"🧠 你想配置报销类型规则。{policy['suggestion']}\n\n你只需用大白话告诉我类型名、限额和是否要发票,我来生成结构化规则。"
    elif module == "报销组":
        cards.append({"type": "table", "title": "报销分组",
                      "data": {"headers": ["分组"], "rows": [[g] for g in mock_db.CLAIM_GROUPS]}})
        reply = "🧠 当前共 4 个报销组。告诉我你想新建/调整哪个组,我对话式帮你管理,无需填表。"
    elif module in ("报销权益", "生成权益流程"):
        cards.append({"type": "entitlement", "title": "权益智能推荐",
                      "data": {"P7+": "35000 元/年", "P5-P6": "25000 元/年", "P3-P4": "18000 元/年",
                               "依据": "对齐市场 75 分位"}})
        reply = f"🧠 {policy['suggestion']}\n\n要我按这个方案一键生成全员年度权益包吗?(由 PolicyAgent 后台推理,WorkflowAgent 跑批生成)"
    elif module == "余额调整":
        cards.append({"type": "entitlement", "title": "可调整员工", "data": mock_db.get_balance("E001")})
        reply = f"🧠 {policy['suggestion']}\n\n请告诉我要调整谁、调整多少、理由是什么,我会执行并留痕。"
    else:
        reply = f"🧠 {policy['suggestion']}"

    return {"reply": reply, "cards": cards, "think": think,
            "needs_human": False, "hil_level": "L3"}


# ═══════════════════════════════════════════════
# ⚙️ PayrollNavigator — 薪资领航员
# 模块: ⑪报销接口流程 ⑬审核接口数据 ④汇率
# ═══════════════════════════════════════════════
def payroll_navigator(state: dict) -> dict[str, Any]:
    text = state["user_input"]
    module = state.get("module", "报销接口流程")
    think, cards = [], []

    if module == "汇率":
        think.append(_think("WorkflowAgent", "拉取实时汇率", "forex_api 自动更新"))
        cards.append({"type": "table", "title": "实时汇率(自动更新)",
                      "data": {"headers": ["币种", "对人民币"], "rows": [[k, v] for k, v in mock_db.EXCHANGE_RATES.items()]}})
        return {"reply": "⚙️ 汇率已自动从 forex_api 更新,多币种报销会自动换算,无需人工维护。",
                "cards": cards, "think": think, "needs_human": False, "hil_level": "L4"}

    think.append(_think("WorkflowAgent", "自主跑批", "校验→生成付款文件→推送薪资→回写状态"))
    wf = workers.workflow_agent(module)["workflow"]
    cards.append({"type": "payroll", "title": f"薪资跑批进度 · {wf['batch']}",
                  "data": {"steps": wf["steps"], "total": wf["total"]}})
    reply = (f"⚙️ 跑批完成 ✅ 本批次 {wf['total']} 条单据,全部校验通过、0 异常。\n"
             "付款文件已生成并推送至 Paydaes 薪资系统,报销状态已回写为「已支付」。\n"
             "整个长事务我做了断点续跑保护(基于 Checkpoint),即使中途中断也能从断点恢复。")
    return {"reply": reply, "cards": cards, "think": think, "needs_human": False, "hil_level": "L1"}


# ═══════════════════════════════════════════════
# 📊 InsightOracle — 数据洞察先知
# 模块: ⑮福利使用报表 ⑯差旅申请报表 ⑰报销申请报表
# ═══════════════════════════════════════════════
def insight_oracle(state: dict) -> dict[str, Any]:
    text = state["user_input"]
    module = state.get("module", "报销申请报表")
    think, cards = [], []

    think.append(_think("InsightAgent", "NL2SQL", "把自然语言问题翻译为查询"))
    think.append(_think("InsightAgent", "归因分析", "聚合 + 时序预测"))
    rep = workers.insight_agent(module, text)["report"]

    cards.append({"type": "chart", "title": f"{module} · 可视化",
                  "data": {"labels": rep["labels"], "series": rep["series"], "kind": "bar"}})

    reply = f"📊 已为你分析【{module}】:\n\n💡 **核心洞察**:{rep['insight']}"
    if "报销申请报表" in module and ("ppt" in text.lower() or "PPT" in text or "总结" in text):
        reply += "\n\n📑 我还可以一键把这份分析生成高管月度 PPT 简报,需要吗?"
        cards.append({"type": "report", "title": "可生成物", "data": {"options": ["导出 PPT 简报", "导出 Excel 明细", "订阅每月自动推送"]}})

    return {"reply": reply, "cards": cards, "think": think, "needs_human": False, "hil_level": "L3"}


# 主 Agent 路由表
MAIN_AGENTS = {
    "ClaimMate": claim_mate,
    "ApprovalCopilot": approval_copilot,
    "HRStrategist": hr_strategist,
    "PayrollNavigator": payroll_navigator,
    "InsightOracle": insight_oracle,
}
