"""
ClaimGPT 核心状态模型
定义 LangGraph 编排过程中流转的全局状态(State)。
所有主 Agent / 子 Agent 共享这个状态结构。
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


# 5 大主 Agent 标识
MainAgent = Literal[
    "ClaimMate",        # 员工报销伙伴
    "ApprovalCopilot",  # 审批副驾
    "HRStrategist",     # HR 战略顾问
    "PayrollNavigator", # 薪资领航员
    "InsightOracle",    # 数据洞察先知
]


class ThinkStep(TypedDict):
    """Agent 思考过程的单步(用于前端思考可视化)"""
    agent: str        # 哪个子 Agent 在工作
    action: str       # 正在做什么
    detail: str       # 细节


class Card(TypedDict, total=False):
    """混合界面卡片(报销单/审批/图表等结构化输出)"""
    type: str         # claim | approval | chart | entitlement | payroll | report | family | table
    title: str
    data: dict[str, Any]


class ClaimState(TypedDict, total=False):
    """全局编排状态 —— 在 Orchestrator 与各 Agent 之间流转"""
    # 对话消息(使用 LangGraph 的 add_messages reducer 累加)
    messages: Annotated[list, add_messages]

    # 路由相关
    user_input: str                 # 当前用户输入
    intent: str                     # 识别出的意图
    module: str                     # 命中的 18 模块之一
    target_agent: Optional[str]     # 路由到哪个主 Agent
    confidence: float               # 意图置信度
    company: str                    # 当前租户公司(sg/my/th/vn/id/hk/cn)

    # 业务上下文(各子 Agent 填充)
    extracted: dict[str, Any]       # 抽取结果(OCR 等)
    validation: dict[str, Any]      # 校验结果
    risk: dict[str, Any]            # 风险评分
    policy: dict[str, Any]          # 政策推理结果

    # 人机协同(Human-in-the-loop)
    needs_human: bool               # 是否需要人工审批
    hil_level: str                  # L0~L4 协同等级
    approved: Optional[bool]        # 人工审批结果

    # 输出
    reply: str                      # 给用户的自然语言回复
    cards: list[Card]               # 结构化卡片
    think: list[ThinkStep]          # 思考过程(可视化)
    done: bool                      # 本轮是否完成
