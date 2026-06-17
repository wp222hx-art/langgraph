"""
Orchestrator 总编排器 —— ClaimGPT 的大脑
基于 LangGraph StateGraph 实现 Orchestrator-Worker 双层架构:
  用户输入 → IntentAgent 路由 → 分发到 5 主 Agent 之一 → (高风险) 人机协同 → 输出

体现的 LangGraph 核心能力:
  - StateGraph 状态图编排
  - 条件边(conditional edges)做意图路由
  - MemorySaver Checkpoint 持久化(短期记忆 + 长事务断点续跑)
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.main.handlers import MAIN_AGENTS
from app.agents.sub import workers
from app.core import permissions, telemetry
from app.core.schema import ClaimState

import time as _t


# ── 节点1:意图识别与路由(IntentAgent) ──
def node_intent(state: ClaimState) -> dict:
    telemetry.hit("IntentAgent")  # 真实埋点:意图识别命中
    result = workers.intent_agent(state["user_input"])
    think = [{"agent": "IntentAgent", "action": "意图识别",
              "detail": f"命中模块「{result['module']}」→ 路由到 {result['target_agent']}(置信度 {result['confidence']})"}]
    return {**result, "think": think}


# ── 节点2:主 Agent 执行(动态分发到 5 个主 Agent) ──
def node_main_agent(state: ClaimState) -> dict:
    agent_name = state.get("target_agent") or "ClaimMate"
    role = state.get("role") or "employee"
    telemetry.hit(agent_name)  # 真实埋点:主 Agent 被实际分发命中
    handler = MAIN_AGENTS.get(agent_name, MAIN_AGENTS["ClaimMate"])
    result = handler(dict(state))
    # 合并思考链:意图节点的 think + 主Agent的 think
    merged_think = list(state.get("think", [])) + list(result.get("think", []))
    # 权限贯穿:把当前登录者的身份与权限画像注入出口 LLM,
    # 让 AI「知道在为谁服务、他能做什么」,在对话中主动拒绝越权请求
    perm_profile = permissions.describe(role)
    if not result.get("_denied"):
        merged_think.append({"agent": "PermissionGuard", "action": "身份裁决",
                             "detail": f"已识别登录者权限({permissions.ROLE_NAMES.get(role, (role,))[0]}),AI 全程按权限边界应答"})
    # 出口人格化润色:该主 Agent 已分发 LLM 则用其人格重写回复,无绑定原样返回
    raw_reply = result["reply"]
    telemetry.hit("ConversationAgent")  # 真实埋点:出口人格化润色命中
    polished = workers.conversation_agent(agent_name, raw_reply, perm_profile=perm_profile)
    if polished != raw_reply:
        merged_think.append({"agent": agent_name, "action": "人格化润色",
                             "detail": "已分发模型在线,按 Agent 人格润色回复(事实信息保持不变)"})
    return {
        "reply": polished,
        "cards": result.get("cards", []),
        "think": merged_think,
        "needs_human": result.get("needs_human", False),
        "hil_level": result.get("hil_level", "L4"),
        "target_agent": agent_name,
        "done": True,
    }


# ── 条件路由:意图 → 主Agent(此处统一进 main_agent 节点,由其内部分发) ──
def route_after_intent(state: ClaimState) -> str:
    return "main_agent"


def build_graph():
    """构建并编译 LangGraph 状态图"""
    g = StateGraph(ClaimState)
    g.add_node("intent", node_intent)
    g.add_node("main_agent", node_main_agent)

    g.add_edge(START, "intent")
    g.add_conditional_edges("intent", route_after_intent, {"main_agent": "main_agent"})
    g.add_edge("main_agent", END)

    # Checkpoint:短期记忆 + 长事务持久化(MVP 用内存,阶段二换 Postgres)
    checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)


# 全局单例
GRAPH = build_graph()

# "怎么报销/如何提交/能拍照吗"等操作意图关键词 → 主动递上拍照识别入口
_UPLOAD_KEYWORDS = (
    "怎么报销", "如何报销", "怎样报销", "怎么提交", "如何提交", "怎么申请", "如何申请",
    "怎么填", "怎么做", "怎么弄", "拍照", "上传", "发票", "收据", "票据", "扫描", "识别",
    "报销流程", "报销单怎么", "贴发票", "录入",
    "how to claim", "how do i claim", "submit a claim", "upload", "receipt",
    "invoice", "take a photo", "scan", "how to submit",
)


def _wants_upload(text: str) -> bool:
    """轻量意图识别:用户是否在问"怎么报销/能否拍照上传"这类可用 OCR 解决的操作问题。"""
    if not text:
        return False
    low = text.lower()
    return any(kw in text or kw in low for kw in _UPLOAD_KEYWORDS)


def run_turn(user_input: str, thread_id: str = "default", company: str = "sg",
             role: str = "employee") -> dict:
    """执行一轮编排,返回完整结果(含思考链、卡片、回复)。
    role:当前登录者角色 —— 贯穿到状态与 Agent,实现 AI 身份判定与越权裁决。"""
    config = {"configurable": {"thread_id": thread_id}}
    init = {"user_input": user_input, "company": company, "role": role or "employee",
            "messages": [{"role": "user", "content": user_input}]}
    _start = _t.time()
    final = GRAPH.invoke(init, config)
    telemetry.turn((_t.time() - _start) * 1000)  # 真实埋点:整轮编排耗时(ms)
    cards = final.get("cards", [])
    # ── 主动递上"拍照识别"入口 ──
    # 当用户在对话里询问"怎么报销/如何提交/能不能拍照"等操作类意图时,
    # 不止给文字答复,还附一个 upload_action 卡片,前端渲染成醒目的拍照识别按钮。
    if _wants_upload(user_input) and not any(c.get("type") == "upload_action" for c in cards):
        cards = cards + [{
            "type": "upload_action",
            "title": "📷 拍照识别 · 自动填单",
            "data": {
                "hint": "拍张发票/收据照片,我来自动识别商户、金额、类别并帮您填好报销单。",
                "hint_en": "Snap a photo of your receipt — I'll auto-extract the merchant, amount and category and fill the claim for you.",
                "btn": "拍照/上传票据",
                "btn_en": "Snap / Upload Receipt",
            },
        }]
    return {
        "reply": final.get("reply", ""),
        "cards": cards,
        "think": final.get("think", []),
        "agent": final.get("target_agent", "ClaimMate"),
        "module": final.get("module", ""),
        "needs_human": final.get("needs_human", False),
        "hil_level": final.get("hil_level", "L4"),
    }
