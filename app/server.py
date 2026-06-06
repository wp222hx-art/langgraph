"""
ClaimGPT FastAPI 后端
- POST /api/chat       : 一次性返回(含思考链/卡片/回复)
- GET  /api/chat/stream: SSE 流式输出(打字机效果 + 思考过程实时推送)
- GET  /api/agents     : 5 主 Agent 元信息
- GET  /api/modules    : 18 模块清单
- GET  /                : 前端页面
"""
from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.orchestrator import run_turn

app = FastAPI(title="Paydaes ClaimGPT", version="3.0")

# ── 5 主 Agent 元信息 ──
AGENTS = [
    {"id": "ClaimMate", "name": "报销伙伴", "emoji": "🙋", "color": "#10b981",
     "desc": "拍照报销 · 对话提交 · 余额查询 · 差旅 · 家属", "modules": ["报销申请-自助", "商务差旅申请-自助", "商务差旅报销-自助", "家庭信息"],
     "samples": ["我打车花了88块要报销", "我要去上海出差申请预审批", "我还能报销多少钱", "登记我的家属信息"]},
    {"id": "ApprovalCopilot", "name": "审批副驾", "emoji": "✅", "color": "#3b82f6",
     "desc": "风险分级 · 一键批量 · 异常检测 · 人机协同", "modules": ["报销申请-管理", "差旅申请-管理", "差旅报销-管理"],
     "samples": ["帮我审批待审单据", "批量通过低风险报销", "差旅审批有哪些待处理"]},
    {"id": "HRStrategist", "name": "HR战略顾问", "emoji": "🧠", "color": "#8b5cf6",
     "desc": "对话式配置 · 权益优化 · 政策推理", "modules": ["报销类型", "报销组", "报销权益", "生成权益流程", "余额调整"],
     "samples": ["帮我配置报销类型", "管理报销组", "推荐权益预算方案", "生成年度权益", "做一次余额调整"]},
    {"id": "PayrollNavigator", "name": "薪资领航员", "emoji": "⚙️", "color": "#f59e0b",
     "desc": "自主跑批 · 异常预警 · 对账 · 汇率", "modules": ["报销接口流程", "审核接口数据", "汇率"],
     "samples": ["执行薪资跑批", "审核接口数据", "查一下美元汇率"]},
    {"id": "InsightOracle", "name": "洞察先知", "emoji": "📊", "color": "#ec4899",
     "desc": "NL2SQL · 预测分析 · 自动报表 · PPT生成", "modules": ["福利使用报表", "差旅申请报表", "报销申请报表"],
     "samples": ["看一下福利使用报表", "分析差旅报表", "生成报销月度总结PPT"]},
]

MODULES = [
    "报销类型", "报销组", "报销权益", "汇率", "报销申请-自助", "商务差旅申请-自助",
    "商务差旅报销-自助", "报销申请-管理", "差旅申请-管理", "差旅报销-管理",
    "报销接口流程", "生成权益流程", "审核接口数据", "余额调整",
    "福利使用报表", "差旅申请报表", "报销申请报表", "家庭信息",
]


class ChatReq(BaseModel):
    message: str
    thread_id: str = "default"


@app.get("/api/agents")
def get_agents():
    return {"agents": AGENTS}


@app.get("/api/modules")
def get_modules():
    return {"modules": MODULES, "count": len(MODULES)}


@app.post("/api/chat")
def chat(req: ChatReq):
    return run_turn(req.message, req.thread_id)


@app.get("/api/chat/stream")
async def chat_stream(message: str, thread_id: str = "default"):
    """SSE 流式:先推送思考过程,再逐字推送回复(打字机)"""
    async def gen():
        result = run_turn(message, thread_id)

        # 1) 路由信息
        yield _sse("route", {"agent": result["agent"], "module": result["module"],
                             "needs_human": result["needs_human"], "hil_level": result["hil_level"]})
        await asyncio.sleep(0.15)

        # 2) 思考过程逐条推送(可视化)
        for step in result["think"]:
            yield _sse("think", step)
            await asyncio.sleep(0.35)

        # 3) 回复逐字推送(打字机)
        reply = result["reply"]
        buf = ""
        for ch in reply:
            buf += ch
            yield _sse("token", {"char": ch})
            await asyncio.sleep(0.012)

        # 4) 卡片
        for card in result["cards"]:
            yield _sse("card", card)
            await asyncio.sleep(0.1)

        # 5) 结束
        yield _sse("done", {"full": reply})

    return StreamingResponse(gen(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/")
def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
