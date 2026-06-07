"""
5 个主 Agent (User-Facing Agents)
每个主 Agent 负责"理解+表达",内部调度 8 个子 Agent 完成名下模块。
覆盖全部 18 个业务模块。

返回结构统一为 dict: {reply, cards, think, needs_human, hil_level}
"""
from __future__ import annotations

from typing import Any

from app.agents.sub import workers
from app.core import permissions, telemetry
from app.data import mock_db, db, calc


def _think(agent: str, action: str, detail: str = "") -> dict:
    telemetry.hit(agent)   # 真实埋点:子 Agent 每次工作即点亮对应灯(零回归)
    return {"agent": agent, "action": action, "detail": detail}


# ═══════════════════════════════════════════════
# 🙋 ClaimMate — 员工报销伙伴
# 模块: ⑤报销申请-自助 ⑥差旅申请-自助 ⑦差旅报销-自助 ⑱家庭信息
# ═══════════════════════════════════════════════
def claim_mate(state: dict) -> dict[str, Any]:
    text = state["user_input"]
    module = state.get("module", "报销申请-自助")
    company = state.get("company", "sg")
    emp = db.get_employee(None, company) or {}
    emp_id = emp.get("id", "")
    cur = db.COMPANY_CURRENCY.get(company, "CNY")
    think, cards = [], []

    if module == "家庭信息":
        think.append(_think("ConversationAgent", "登记家属信息"))
        fam = db.get_family(emp_id, company)
        cards.append({"type": "family", "title": "我的家属档案", "data": {"members": fam}})
        return {"reply": f"已为你查询家属信息 👨‍👩‍👧(共 {len(fam)} 位)。家属报销时我会自动关联他们的档案,无需重复填写。",
                "cards": cards, "think": think, "needs_human": False, "hil_level": "L4"}

    if "余额" in text or "剩多少" in text or "还能报" in text:
        think.append(_think("WorkflowAgent", "查询权益余额", "实时聚合已批准报销"))
        bal = db.get_balance(emp_id, company)
        cards.append({"type": "entitlement", "title": "我的报销额度", "data": bal})
        return {"reply": f"你好 {bal['name']} 😊 你的年度额度 {bal['annual']} {cur},已用 {bal['used']} {cur},还剩 **{bal['remaining']} {cur}**。需要我帮你报销点什么吗?",
                "cards": cards, "think": think, "needs_human": False, "hil_level": "L4"}

    # 报销提交主链路:抽取 → 校验 → 风险 → 真写入数据库
    think.append(_think("ExtractionAgent", "识别发票", "多模态抽取金额/商户/品类"))
    ext = workers.extraction_agent(text, company)["extracted"]

    think.append(_think("ValidationAgent", "合规校验", "比对报销类型与限额"))
    val = workers.validation_agent(ext, company)["validation"]

    think.append(_think("RiskAgent", "风险评分", "多因子加权 + 超限检测"))
    risk = workers.risk_agent(ext, val)["risk"]

    amount = ext.get("amount", 0) or 0
    amount_base = calc.to_base_currency(amount, ext.get("currency", cur), cur)
    tax = calc.deductible_tax(amount_base, company)

    # 真写库
    think.append(_think("WorkflowAgent", "提交入库", "写入 SQLite 持久化"))
    saved = db.create_claim({
        "company": company, "emp_id": emp_id, "emp_name": emp.get("name", ""),
        "type_code": ext.get("type_code", ""), "type_name": ext.get("category", ""),
        "merchant": ext.get("merchant", ""), "amount": amount, "currency": ext.get("currency", cur),
        "amount_base": amount_base, "tax_amount": tax, "tax_no": ext.get("tax_no", ""),
        "note": ext.get("merchant", ""), "risk_score": risk["score"], "risk_level": risk["level"],
        "risk_reasons": risk["reasons"], "status": "pending", "source": "chat",
    })

    is_travel = "差旅" in module
    issue_txt = "; ".join(i.get("zh", "") for i in val.get("issues", []))
    claim_card = {
        "type": "claim",
        "title": "差旅报销单(已提交入库)" if is_travel else "报销单(已提交入库)",
        "data": {"单号": saved["id"], "商户": ext.get("merchant", ""), "品类": ext.get("category", ""),
                 "金额": f"{amount} {ext.get('currency', cur)}", "本币金额": f"{amount_base} {cur}",
                 "可抵扣税": f"{tax} {cur}",
                 "校验": "✅ 通过" if val["passed"] else "⚠️ " + issue_txt,
                 "风险等级": f"{risk['level']}({risk['score']})", "状态": "待审批"},
    }
    cards.append(claim_card)

    reply = f"📸 已识别【{ext.get('merchant','')}】的{ext.get('category','')},金额 {amount} {ext.get('currency', cur)}。"
    if val["passed"]:
        reply += f"校验通过 ✅ 已生成报销单 **{saved['id']}** 并提交入库,进入审批队列。可抵扣 {tax} {cur} 进项税。"
    else:
        reply += f"单号 **{saved['id']}** 已提交,但 " + issue_txt + f"。风险等级 {risk['level']},需审批人关注。"

    return {"reply": reply, "cards": cards, "think": think,
            "needs_human": False, "hil_level": "L4"}


# ═══════════════════════════════════════════════
# ✅ ApprovalCopilot — 审批副驾
# 模块: ⑧报销申请-管理 ⑨差旅申请-管理 ⑩差旅报销-管理
# ═══════════════════════════════════════════════
def approval_copilot(state: dict) -> dict[str, Any]:
    text = state["user_input"]
    company = state.get("company", "sg")
    cur = db.COMPANY_CURRENCY.get(company, "CNY")
    think, cards = [], []
    think.append(_think("RiskAgent", "风险分级", "读取数据库待审单据的真实风险分"))
    think.append(_think("PolicyAgent", "政策推理", "应用审批规则"))

    # 意图:是否是执行性指令(批量通过低风险)
    do_batch = any(k in text for k in ["批量通过", "一键通过", "都通过", "全部通过", "batch approve", "approve all"])
    if do_batch:
        # 【权限贯穿·handler 硬拦截】无批量审批权的角色(如普通员工)让 AI 代办审批 → 写库前拦住
        role = state.get("role") or "employee"
        if not permissions.can(role, "claim.batch_approve"):
            dp = permissions.deny_payload(role, "claim.batch_approve")
            think.append(_think("PermissionGuard", "越权拦截", dp["error"]))
            allowed = "、".join(dp["allowed_roles"])
            return {"reply": f"⛔ {dp['error']} 我不能代你执行审批。请联系【{allowed}】处理该批量审批。",
                    "cards": cards, "think": think, "needs_human": False, "hil_level": "L4", "_denied": True}
        think.append(_think("WorkflowAgent", "批量审批入库", "低风险 pending → approved"))
        n = db.batch_decide(company, "approved", risk_level="低")
        stat = db.claim_stats(company)
        claims = db.list_claims(company, status="pending")
        rows = [[c["id"], c["emp_name"], c["type_name"], f"{c['amount']} {c['currency']}",
                 c["risk_level"], c["note"] or ""] for c in claims]
        cards.append({"type": "approval", "title": "批量通过后的待审单据",
                      "data": {"headers": ["单号", "申请人", "类型", "金额", "风险", "备注"], "rows": rows,
                               "summary": {"低风险": stat["risk"]["低"], "中风险": stat["risk"]["中"], "高风险": stat["risk"]["高"]}}})
        return {"reply": f"✅ 已一键批量通过 **{n}** 张低风险单据(状态真实更新为已批准)。当前还剩 {len(claims)} 张待审,其中高风险 {stat['risk']['高']} 张需你人工决策。",
                "cards": cards, "think": think, "needs_human": stat["risk"]["高"] > 0, "hil_level": "L2"}

    claims = db.list_claims(company, status="pending")
    stat = db.claim_stats(company)
    low = [c for c in claims if c["risk_level"] == "低"]
    mid = [c for c in claims if c["risk_level"] == "中"]
    high = [c for c in claims if c["risk_level"] == "高"]

    rows = [[c["id"], c["emp_name"], c["type_name"], f"{c['amount']} {c['currency']}",
             c["risk_level"], c["note"] or ""] for c in claims]
    cards.append({"type": "approval", "title": "待审批单据(来自数据库·已风险分级)",
                  "data": {"headers": ["单号", "申请人", "类型", "金额", "风险", "备注"], "rows": rows,
                           "summary": {"低风险": len(low), "中风险": len(mid), "高风险": len(high)}}})

    reply = (f"📋 当前数据库共 {len(claims)} 张待审单据(总额 {stat['total_amt']} {cur}),已完成风险分级:\n"
             f"- 🟢 低风险 {len(low)} 张 → 说「批量通过」我就**真入库批准**\n"
             f"- 🟡 中风险 {len(mid)} 张 → 建议快速复核\n"
             f"- 🔴 高风险 {len(high)} 张 → **需你人工决策**(我仅提供建议)\n\n"
             f"按 L2 协同规则,最终审批权在你手上。")

    return {"reply": reply, "cards": cards, "think": think,
            "needs_human": len(high) > 0, "hil_level": "L2",
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

    company = state.get("company", "sg")
    if module == "报销类型":
        types = db.get_claim_types(company)
        cards.append({"type": "table", "title": "现有报销类型(来自数据库)",
                      "data": {"headers": ["编码", "名称", "限额", "分组"],
                               "rows": [[t["code"], t["name"], f"{t['limit_amt']}", t["grp"]] for t in types]}})
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
        cards.append({"type": "entitlement", "title": "可调整员工", "data": db.get_balance(None, company)})
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

    company = state.get("company", "sg")
    cur = db.COMPANY_CURRENCY.get(company, "CNY")
    if module == "汇率":
        think.append(_think("WorkflowAgent", "交叉汇率计算", f"以本位币 {cur} 为基准真实换算"))
        majors = ["USD", "EUR", "CNY", "SGD", "MYR", "THB", "HKD"]
        rows = [[m, calc.fx_rate(m, cur)] for m in majors if m != cur]
        cards.append({"type": "table", "title": f"实时交叉汇率(1 外币 = ? {cur})",
                      "data": {"headers": ["币种", f"对 {cur}"], "rows": rows}})
        return {"reply": f"⚙️ 以本公司本位币 **{cur}** 为基准的交叉汇率已算好。员工提交多币种报销时,系统会自动按这张表换算为 {cur} 入库。",
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

    company = state.get("company", "sg")
    think.append(_think("InsightAgent", "NL2SQL", "从真实报销库聚合查询"))
    think.append(_think("InsightAgent", "归因分析", "按部门/品类聚合"))
    rep = workers.insight_agent(module, text, company)["report"]

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
