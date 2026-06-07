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
from app.core.schema import ClaimState


# ── 节点1:意图识别与路由(IntentAgent) ──
def node_intent(state: ClaimState) -> dict:
    result = workers.intent_agent(state["user_input"])
    think = [{"agent": "IntentAgent", "action": "意图识别",
              "detail": f"命中模块「{result['module']}」→ 路由到 {result['target_agent']}(置信度 {result['confidence']})"}]
    return {**result, "think": think}


# ── 节点2:主 Agent 执行(动态分发到 5 个主 Agent) ──
def node_main_agent(state: ClaimState) -> dict:
    agent_name = state.get("target_agent") or "ClaimMate"
    handler = MAIN_AGENTS.get(agent_name, MAIN_AGENTS["ClaimMate"])
    result = handler(dict(state))
    # 合并思考链:意图节点的 think + 主Agent的 think
    merged_think = list(state.get("think", [])) + list(result.get("think", []))
    # 出口人格化润色:该主 Agent 已分发 LLM 则用其人格重写回复,无绑定原样返回
    raw_reply = result["reply"]
    polished = workers.conversation_agent(agent_name, raw_reply)
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


def run_turn(user_input: str, thread_id: str = "default", company: str = "sg") -> dict:
    """执行一轮编排,返回完整结果(含思考链、卡片、回复)"""
    config = {"configurable": {"thread_id": thread_id}}
    init = {"user_input": user_input, "company": company,
            "messages": [{"role": "user", "content": user_input}]}
    final = GRAPH.invoke(init, config)
    return {
        "reply": final.get("reply", ""),
        "cards": final.get("cards", []),
        "think": final.get("think", []),
        "agent": final.get("target_agent", "ClaimMate"),
        "module": final.get("module", ""),
        "needs_human": final.get("needs_human", False),
        "hil_level": final.get("hil_level", "L4"),
    }
