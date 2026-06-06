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
from app.data import enterprise, navigation, mock_db, paydaes_modules, db, calc

app = FastAPI(title="Paydaes ClaimGPT", version="3.0")

# 启动即初始化真实持久化层(建表 + 首次播种)
db.init_db()

# ── 5 主 Agent 元信息 ──
AGENTS = [
    {"id": "ClaimMate", "name": "报销伙伴", "name_en": "ClaimMate", "emoji": "🙋", "color": "#10b981",
     "desc": "拍照报销 · 对话提交 · 余额查询 · 差旅 · 家属",
     "desc_en": "Photo claim · Chat submit · Balance · Travel · Family", "modules": ["报销申请-自助", "商务差旅申请-自助", "商务差旅报销-自助", "家庭信息"],
     "samples": ["我打车花了88块要报销", "我要去上海出差申请预审批", "我还能报销多少钱", "登记我的家属信息"],
     "samples_en": ["I spent $88 on a taxi to claim", "I want to apply pre-approval for a Shanghai trip", "How much can I still claim", "Register my family info"]},
    {"id": "ApprovalCopilot", "name": "审批副驾", "name_en": "ApprovalCopilot", "emoji": "✅", "color": "#3b82f6",
     "desc": "风险分级 · 一键批量 · 异常检测 · 人机协同",
     "desc_en": "Risk grading · Batch approve · Anomaly detect · HITL", "modules": ["报销申请-管理", "差旅申请-管理", "差旅报销-管理"],
     "samples": ["帮我审批待审单据", "批量通过低风险报销", "差旅审批有哪些待处理"],
     "samples_en": ["Help me approve pending claims", "Batch approve low-risk claims", "What travel approvals are pending"]},
    {"id": "HRStrategist", "name": "HR战略顾问", "name_en": "HR Strategist", "emoji": "🧠", "color": "#8b5cf6",
     "desc": "对话式配置 · 权益优化 · 政策推理",
     "desc_en": "Chat config · Entitlement tuning · Policy reasoning", "modules": ["报销类型", "报销组", "报销权益", "生成权益流程", "余额调整"],
     "samples": ["帮我配置报销类型", "管理报销组", "推荐权益预算方案", "生成年度权益", "做一次余额调整"],
     "samples_en": ["Help me configure claim types", "Manage claim groups", "Recommend an entitlement budget plan", "Generate annual entitlements", "Do a balance adjustment"]},
    {"id": "PayrollNavigator", "name": "薪资领航员", "name_en": "Payroll Navigator", "emoji": "⚙️", "color": "#f59e0b",
     "desc": "自主跑批 · 异常预警 · 对账 · 汇率",
     "desc_en": "Auto batch · Anomaly alert · Reconcile · FX", "modules": ["报销接口流程", "审核接口数据", "汇率"],
     "samples": ["执行薪资跑批", "审核接口数据", "查一下美元汇率"],
     "samples_en": ["Run payroll batch", "Review interface data", "Check the USD exchange rate"]},
    {"id": "InsightOracle", "name": "洞察先知", "name_en": "Insight Oracle", "emoji": "📊", "color": "#ec4899",
     "desc": "NL2SQL · 预测分析 · 自动报表 · PPT生成",
     "desc_en": "NL2SQL · Forecast · Auto report · PPT gen", "modules": ["福利使用报表", "差旅申请报表", "报销申请报表"],
     "samples": ["看一下福利使用报表", "分析差旅报表", "生成报销月度总结PPT"],
     "samples_en": ["Show the benefits usage report", "Analyze the travel report", "Generate a monthly expense summary PPT"]},
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
    company: str = "sg"


class ClaimReq(BaseModel):
    company: str = "sg"
    type_code: str
    merchant: str = ""
    amount: float
    currency: str = ""
    note: str = ""
    emp_id: str = ""


class DecideReq(BaseModel):
    status: str            # approved / rejected / paid
    approver: str = "审批副驾"


class FamilyReq(BaseModel):
    company: str = "sg"
    emp_id: str = ""
    relation: str
    name: str


@app.get("/api/agents")
def get_agents():
    return {"agents": AGENTS}


# ═══════ 企业级 API ═══════
@app.get("/api/bootstrap")
def bootstrap():
    """前端启动时一次性拉取:集团/公司、角色、语言、导航树"""
    return {
        "groups": enterprise.GROUPS,
        "roles": enterprise.ROLES,
        "languages": enterprise.LANGUAGES,
        "nav": navigation.NAV_TREE + paydaes_modules.PAYDAES_NAV,
        "agents": AGENTS,
    }


@app.get("/api/dashboard")
def dashboard(company: str = "sg"):
    return {
        "kpi": navigation.dashboard_kpi(company),
        "todos": navigation.TODOS,
        "chart": navigation.DASHBOARD_CHART,
    }


@app.get("/api/compliance")
def compliance(country: str | None = None):
    if country:
        return enterprise.COUNTRIES.get(country.upper(), {})
    return {"countries": enterprise.COUNTRIES}


@app.get("/api/module/{module_id}")
def module_data(module_id: str, company: str = "sg", lang: str = "zh"):
    """返回某个模块的工作区数据(表格/卡片)"""
    # 先查 Paydaes 6 大域(税务/假期/考勤/财务/主数据/法定表单)
    cur = "MYR"
    for g in enterprise.GROUPS:
        for c in g["companies"]:
            if c["id"] == company:
                cur = c.get("currency", "MYR")
    pm = paydaes_modules.get_paydaes_module(module_id, cur, lang)
    if pm is not None:
        return pm
    # 回退原 18 模块逻辑
    from app.data.module_views import get_module_view
    return get_module_view(module_id, company)


@app.get("/api/modules")
def get_modules():
    return {"modules": MODULES, "count": len(MODULES)}


@app.post("/api/chat")
def chat(req: ChatReq):
    return run_turn(req.message, req.thread_id, req.company)


# ═══════ 真实报销单 CRUD(SQLite 持久化) ═══════
@app.get("/api/claims")
def list_claims(company: str = "sg", status: str | None = None, emp_id: str | None = None):
    """真实报销单列表(来自数据库)"""
    rows = db.list_claims(company, status=status, emp_id=emp_id)
    return {"claims": rows, "count": len(rows), "stats": db.claim_stats(company)}


@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: str):
    cl = db.get_claim(claim_id)
    return cl or {"error": "not found"}


@app.post("/api/claims")
def create_claim(req: ClaimReq):
    """表单提交报销单:真走计算引擎 + 真写库"""
    company = req.company
    cur = req.currency or db.COMPANY_CURRENCY.get(company, "CNY")
    emp = db.get_employee(req.emp_id or None, company) or {}
    ctype = db.get_claim_type(req.type_code, company)
    if not ctype:
        return {"error": f"unknown type_code {req.type_code}"}
    base = calc.to_base_currency(req.amount, cur, db.COMPANY_CURRENCY.get(company, "CNY"))
    tax = calc.deductible_tax(base, company)
    val = calc.validate_limit(req.amount, ctype["limit_amt"], ctype["name"])
    risk = calc.risk_score(req.amount, ctype["limit_amt"], exceed=not val["passed"])
    saved = db.create_claim({
        "company": company, "emp_id": emp.get("id", ""), "emp_name": emp.get("name", ""),
        "type_code": ctype["code"], "type_name": ctype["name"], "merchant": req.merchant,
        "amount": req.amount, "currency": cur, "amount_base": base, "tax_amount": tax,
        "note": req.note, "risk_score": risk["score"], "risk_level": risk["level"],
        "risk_reasons": risk["reasons"], "status": "pending", "source": "form",
    })
    return {"claim": saved, "validation": val, "risk": risk,
            "tax_amount": tax, "amount_base": base}


@app.post("/api/claims/{claim_id}/decide")
def decide_claim(claim_id: str, req: DecideReq):
    """审批:真改状态 + 留痕"""
    cl = db.decide_claim(claim_id, req.status, req.approver)
    return cl or {"error": "not found"}


@app.post("/api/claims/batch_decide")
def batch_decide(company: str = "sg", status: str = "approved", risk_level: str | None = None):
    n = db.batch_decide(company, status, risk_level=risk_level)
    return {"affected": n, "stats": db.claim_stats(company)}


@app.get("/api/balance")
def balance(company: str = "sg", emp_id: str | None = None):
    return db.get_balance(emp_id, company)


@app.get("/api/fx")
def fx(base: str = "CNY"):
    """真实交叉汇率表"""
    majors = ["USD", "EUR", "CNY", "SGD", "MYR", "THB", "VND", "IDR", "HKD", "JPY", "GBP"]
    return {"base": base, "rates": {m: calc.fx_rate(m, base) for m in majors}}


@app.get("/api/tax_calc")
def tax_calc(company: str = "sg", amount: float = 0):
    """真实可抵扣税额计算"""
    info = calc.tax_info(company)
    return {**info, "amount": amount, "deductible": calc.deductible_tax(amount, company)}


@app.post("/api/family")
def add_family(req: FamilyReq):
    emp = db.get_employee(req.emp_id or None, req.company) or {}
    return db.add_family(emp.get("id", ""), req.company, req.relation, req.name)


@app.get("/api/audit")
def audit(company: str = "sg"):
    return {"logs": db.recent_audit(company)}


@app.get("/api/chat/stream")
async def chat_stream(message: str, thread_id: str = "default", company: str = "sg"):
    """SSE 流式:先推送思考过程,再逐字推送回复(打字机)"""
    async def gen():
        result = run_turn(message, thread_id, company)

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
