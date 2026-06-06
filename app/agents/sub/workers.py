"""
8 个能力子 Agent (Capability Workers)
对应文档 L4 子 Agent 层:Intent / Extraction / Validation / Risk / Policy / Workflow / Insight / Conversation
每个子 Agent 是一个可被主 Agent 子图调用的能力单元。
MVP 阶段用规则 + Mock 实现,阶段二可平滑替换为真实 LLM 调用。
"""
from __future__ import annotations

import re
from typing import Any

from app.data import mock_db


# ─────────────────────────────────────────────
# ① IntentAgent — 意图识别与槽位填充
# ─────────────────────────────────────────────
# 关键词 → (主Agent, 模块名)
# 规则按从具体到宽泛排序,先匹配者优先(避免"报销"等宽泛词抢占)
_INTENT_RULES = [
    # —— HRStrategist(配置类,关键词最具体,放最前)——
    (["报销类型", "费用类别", "新增类型", "类别规则", "配置类型"], "HRStrategist", "报销类型"),
    (["报销组", "费用分组", "类型分组"], "HRStrategist", "报销组"),
    (["生成权益", "年度权益", "批量生成权益"], "HRStrategist", "生成权益流程"),
    (["余额调整", "调整额度", "改余额", "调整余额"], "HRStrategist", "余额调整"),
    (["权益", "预算配置", "额度配置"], "HRStrategist", "报销权益"),
    # —— InsightOracle(报表/分析)——
    (["福利报表", "福利分析", "福利使用"], "InsightOracle", "福利使用报表"),
    (["差旅报表", "差旅分析"], "InsightOracle", "差旅申请报表"),
    (["报销报表", "报销分析", "全局分析", "月度总结", "生成ppt", "生成PPT", "数据洞察", "分析报告"], "InsightOracle", "报销申请报表"),
    # —— PayrollNavigator(薪资/跑批/汇率)——
    (["跑批", "推送薪资", "薪资接口", "接口流程"], "PayrollNavigator", "报销接口流程"),
    (["审核接口", "接口数据", "对账"], "PayrollNavigator", "审核接口数据"),
    (["汇率", "换算", "美元", "外币", "欧元"], "PayrollNavigator", "汇率"),
    # —— ClaimMate 差旅自助(含"预审批",须排在通用"审批"之前)——
    (["申请预审批", "预审批", "出差申请", "要去", "出差去", "我要出差"], "ClaimMate", "商务差旅申请-自助"),
    (["差旅报销", "出差回来", "出差报销"], "ClaimMate", "商务差旅报销-自助"),
    # —— ApprovalCopilot(审批)——
    (["差旅审批", "出差审批"], "ApprovalCopilot", "差旅申请-管理"),
    (["审批", "待审", "批一下", "通过", "驳回", "批量审批"], "ApprovalCopilot", "报销申请-管理"),
    # —— ClaimMate(员工自助)——
    (["家属", "家庭", "配偶", "子女", "登记家人"], "ClaimMate", "家庭信息"),
    (["余额", "还能报", "剩多少", "查余额"], "ClaimMate", "报销申请-自助"),
    (["报销", "发票", "拍照", "提交", "餐费", "打车", "买了", "花了"], "ClaimMate", "报销申请-自助"),
]


def intent_agent(text: str) -> dict[str, Any]:
    text_l = text.lower()
    for keywords, agent, module in _INTENT_RULES:
        for kw in keywords:
            if kw.lower() in text_l:
                return {"intent": module, "module": module, "target_agent": agent, "confidence": 0.95}
    # 默认兜底到报销伙伴
    return {"intent": "通用咨询", "module": "报销申请-自助", "target_agent": "ClaimMate", "confidence": 0.6}


# ─────────────────────────────────────────────
# ② ExtractionAgent — 多模态 OCR 信息抽取
# ─────────────────────────────────────────────
def extraction_agent(text: str) -> dict[str, Any]:
    # 尝试从文本提取金额
    amt = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块|rmb|RMB)?", text)
    if m:
        amt = float(m.group(1))
    ocr = mock_db.mock_ocr_invoice()
    if amt:
        ocr["amount"] = amt
    return {"extracted": ocr}


# ─────────────────────────────────────────────
# ③ ValidationAgent — 业务规则合规校验
# ─────────────────────────────────────────────
def validation_agent(extracted: dict) -> dict[str, Any]:
    cat = extracted.get("category", "")
    amount = extracted.get("amount", 0)
    ctype = next((t for t in mock_db.CLAIM_TYPES if t["name"] == cat), None)
    issues = []
    if ctype:
        if amount > ctype["limit"]:
            issues.append(f"金额 {amount} 超过【{cat}】单笔限额 {ctype['limit']} 元")
    else:
        issues.append(f"未匹配到报销类型「{cat}」")
    return {"validation": {"passed": len(issues) == 0, "issues": issues, "type": ctype}}


# ─────────────────────────────────────────────
# ④ RiskAgent — 风险评分与反欺诈
# ─────────────────────────────────────────────
def risk_agent(extracted: dict, validation: dict) -> dict[str, Any]:
    score = 10
    reasons = []
    if not validation.get("passed"):
        score += 50
        reasons.append("触发合规校验异常")
    amount = extracted.get("amount", 0)
    if amount > 1000:
        score += 25
        reasons.append("大额报销")
    if amount > 3000:
        score += 15
        reasons.append("超大额需重点关注")
    level = "低" if score < 30 else ("中" if score < 60 else "高")
    return {"risk": {"score": min(score, 99), "level": level, "reasons": reasons or ["无明显风险"]}}


# ─────────────────────────────────────────────
# ⑤ PolicyAgent — 政策推理与复杂规则
# ─────────────────────────────────────────────
def policy_agent(module: str, text: str) -> dict[str, Any]:
    suggestions = {
        "报销权益": "建议 P7 及以上年度权益设为 3.5 万,P5-P6 设为 2.5 万,与市场 75 分位对齐。",
        "生成权益流程": "检测到 3 名员工本年度晋升,建议按新职级重新核算年度权益包。",
        "报销类型": "建议新增类型时关联税务编码与单笔限额,并设置是否强制上传发票。",
        "余额调整": "调整需记录理由并留痕,单次调整超 5000 元建议触发二级审批。",
    }
    return {"policy": {"suggestion": suggestions.get(module, "已应用标准政策规则。")}}


# ─────────────────────────────────────────────
# ⑥ WorkflowAgent — 流程推进与状态管理(长事务)
# ─────────────────────────────────────────────
def workflow_agent(action: str) -> dict[str, Any]:
    steps = [
        {"step": "校验接口数据完整性", "status": "完成", "result": "126 条单据,0 异常"},
        {"step": "生成银行付款文件", "status": "完成", "result": "payment_20260606.txt"},
        {"step": "推送至薪资系统", "status": "完成", "result": "已同步 Paydaes 薪资"},
        {"step": "回写报销状态", "status": "完成", "result": "全部标记为已支付"},
    ]
    return {"workflow": {"action": action, "steps": steps, "batch": "BATCH-20260606", "total": 126}}


# ─────────────────────────────────────────────
# ⑦ InsightAgent — 数据聚合与归因分析(NL2SQL)
# ─────────────────────────────────────────────
def insight_agent(module: str, text: str) -> dict[str, Any]:
    return {"report": mock_db.mock_report_data(module + text)}


# ─────────────────────────────────────────────
# ⑧ ConversationAgent — 多轮对话与人格化风格
# ─────────────────────────────────────────────
_PERSONA = {
    "ClaimMate": "😊 我是你的报销伙伴",
    "ApprovalCopilot": "🛡️ 审批副驾为你护航",
    "HRStrategist": "🧠 HR 战略顾问在此",
    "PayrollNavigator": "⚙️ 薪资领航员就位",
    "InsightOracle": "📊 数据洞察先知洞悉一切",
}


def conversation_agent(agent: str, content: str) -> str:
    return content
