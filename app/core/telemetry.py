"""
Telemetry —— Agent 真实调用埋点(轻量·零依赖·线程安全)
═══════════════════════════════════════════════════════════════
把"灯阵"从拟真装饰升级为【真·实时可观测面板】:
  每当某个 Agent 在 run_turn 真实链路中被命中,这里记一笔。
  前端轮询 /api/telemetry,把"刚刚命中"的 Agent 对应的灯真的点亮。

设计原则:
  - 纯内存环形统计,绝不阻塞编排主流程(失败静默,零回归)
  - 13 个 Agent(5 主 + 8 子)统一登记,与前端灯阵一一对应
  - 同时累计:总调用数、各 Agent 命中次数、最近命中时间、最近时延
"""
from __future__ import annotations

import threading
import time
from collections import deque

# ── 13 个 Agent 规范化标识(与前端灯阵一一对应)──
# 5 主 Agent
MAIN_AGENTS = ["ClaimMate", "ApprovalCopilot", "HRStrategist",
               "PayrollNavigator", "InsightOracle"]
# 8 子 Agent(规范名 → 前端短标识由前端映射)
SUB_AGENTS = ["IntentAgent", "PolicyAgent", "RiskAgent", "ExtractionAgent",
              "WorkflowAgent", "EntitlementAgent", "ConversationAgent", "AuditAgent"]
ALL_AGENTS = MAIN_AGENTS + SUB_AGENTS

# 把 handlers 里出现的各种 Agent 名,归一到上面 13 个标识
_ALIAS = {
    "ValidationAgent": "RiskAgent",       # 校验并入风险域灯
    "InsightAgent": "InsightOracle",      # 洞察子 = 洞察先知主
    "PermissionGuard": "AuditAgent",      # 权限裁决并入审计灯
    "Entitlement": "EntitlementAgent",
    "Conv": "ConversationAgent",
}

_lock = threading.Lock()
_counts: dict[str, int] = {a: 0 for a in ALL_AGENTS}
_last_hit: dict[str, float] = {a: 0.0 for a in ALL_AGENTS}
_total_turns = 0
_total_hits = 0
# 最近 50 次 turn 的时延(ms),用于真实 tps / 平均时延
_latencies: deque[float] = deque(maxlen=50)
_turn_times: deque[float] = deque(maxlen=50)   # 每个 turn 的时间戳,算 tps
_started_at = time.time()


def normalize(agent: str) -> str | None:
    """把任意 Agent 名归一到 13 标识之一;无法归一返回 None(忽略)。"""
    if not agent:
        return None
    if agent in _counts:
        return agent
    return _ALIAS.get(agent)


def hit(agent: str) -> None:
    """记录一次 Agent 命中(在 _think / 主 Agent 分发处调用,失败静默)。"""
    try:
        a = normalize(agent)
        if not a:
            return
        with _lock:
            global _total_hits
            _counts[a] += 1
            _last_hit[a] = time.time()
            _total_hits += 1
    except Exception:
        pass


def turn(latency_ms: float) -> None:
    """记录一轮完整 run_turn(总轮次 + 时延 + 时间戳用于 tps)。"""
    try:
        with _lock:
            global _total_turns
            _total_turns += 1
            _latencies.append(float(latency_ms))
            _turn_times.append(time.time())
    except Exception:
        pass


def snapshot(active_window: float = 6.0) -> dict:
    """导出当前遥测快照(供 /api/telemetry)。
    active_window:多少秒内命中过算"刚刚活跃"(前端据此爆闪对应灯)。"""
    now = time.time()
    with _lock:
        agents = []
        for a in ALL_AGENTS:
            last = _last_hit[a]
            agents.append({
                "id": a,
                "kind": "main" if a in MAIN_AGENTS else "sub",
                "count": _counts[a],
                "since_ms": int((now - last) * 1000) if last else None,
                "recent": bool(last and (now - last) <= active_window),
            })
        # 真实平均时延
        avg_lat = round(sum(_latencies) / len(_latencies)) if _latencies else None
        # 真实 tps:最近 10 秒内的 turn 数 / 10
        recent_turns = [t for t in _turn_times if now - t <= 10.0]
        tps = round(len(recent_turns) / 10.0, 1)
        return {
            "agents": agents,
            "total_turns": _total_turns,
            "total_hits": _total_hits,
            "avg_latency_ms": avg_lat,
            "tps": tps,
            "uptime_s": int(now - _started_at),
            "active_window_s": active_window,
        }
