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
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.orchestrator import run_turn
from app.core import llm_gateway, permissions, telemetry
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
    role: str = "employee"        # 当前登录者角色(AI 据此判定身份与权限)


class ClaimReq(BaseModel):
    company: str = "sg"
    type_code: str
    merchant: str = ""
    amount: float
    currency: str = ""
    note: str = ""
    emp_id: str = ""
    role: str = "employee"
    receipt_no: str = ""          # 票据编号 (PM-9 重复检测)
    invoice_date: str = ""        # 票据日期 (PM-10 / 过期校验)
    has_attachment: bool = False  # 是否已上传附件


class DecideWfReq(BaseModel):
    decision: str                  # approved / rejected / returned
    by: str = "审批人"
    comment: str = ""
    role: str = "manager"


class PostReq(BaseModel):
    company: str = "sg"
    pay_calendar: str = ""
    role: str = "payroll"


class OcrReq(BaseModel):
    company: str = "sg"
    image_b64: str          # base64(可含 data: 前缀)
    mime: str = "image/jpeg"


class DecideReq(BaseModel):
    status: str            # approved / rejected / paid
    approver: str = "审批副驾"
    role: str = "approver"


class BatchDecideReq(BaseModel):
    company: str = "sg"
    status: str = "approved"
    risk_level: str | None = None
    role: str = "approver"


class FamilyReq(BaseModel):
    company: str = "sg"
    emp_id: str = ""
    relation: str
    name: str
    role: str = "employee"


class ClaimTypeReq(BaseModel):
    company: str = "sg"
    code: str = ""
    name: str = ""
    name_en: str = ""
    grp: str = "日常"
    limit_amt: float = 0
    need_invoice: bool = True
    role: str = "hr_admin"


class ModuleRecordReq(BaseModel):
    module_id: str
    company: str = "sg"
    payload: dict = {}
    role: str = "hr_admin"


class BalanceAdjustReq(BaseModel):
    company: str = "sg"
    emp_id: str = ""
    kind: str = "增加"          # 增加 / 减少 / 转移
    amount: float = 0
    reason: str = ""            # 必填原因(留痕)
    to_emp_id: str = ""         # 转移时的目标员工
    role: str = "finance"


class ReportExportReq(BaseModel):
    company: str = "sg"
    module_id: str = "rpt_claim"
    fmt: str = "excel"          # excel / ppt
    role: str = "finance"


class StatutoryExportReq(BaseModel):
    form_id: str = "payslip"    # payslip / epf_borang_a / ea_form
    company: str = "my"
    period: str = ""            # 工资单/缴款=YYYY-MM, EA=YYYY
    emp_no: str = ""            # 可选:单个员工(payslip)
    fmt: str = "xlsx"           # xlsx / pdf(仅 ea_form 支持官方 PDF 版式)
    role: str = "payroll"


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
    # 把当前登录者角色注入 AI,使其判定身份并拒绝越权请求
    return run_turn(req.message, req.thread_id, req.company, role=req.role)


# ═══════ 真实报销单 CRUD(SQLite 持久化) ═══════
@app.get("/api/claim_types")
def list_claim_types(company: str = "sg"):
    """报销类型(供前端表单下拉)"""
    return {"types": db.get_claim_types(company)}


@app.post("/api/claim_types")
def create_claim_type(req: ClaimTypeReq):
    """新增报销类型(真写库) —— 需 claim_type.create 权限"""
    if not permissions.can(req.role, "claim_type.create"):
        return permissions.deny_payload(req.role, "claim_type.create")
    try:
        ct = db.create_claim_type(req.company, req.code, req.name, req.name_en,
                                  req.grp, req.limit_amt, req.need_invoice)
        return {"ok": True, "type": ct}
    except ValueError as e:
        return {"error": str(e)}


@app.put("/api/claim_types/{code}")
def update_claim_type(code: str, req: ClaimTypeReq):
    """更新报销类型 —— 需 claim_type.update 权限"""
    if not permissions.can(req.role, "claim_type.update"):
        return permissions.deny_payload(req.role, "claim_type.update")
    ct = db.update_claim_type(req.company, code, name=req.name or None,
                              name_en=req.name_en or None, grp=req.grp or None,
                              limit_amt=req.limit_amt, need_invoice=req.need_invoice)
    return {"ok": bool(ct), "type": ct}


@app.delete("/api/claim_types/{code}")
def delete_claim_type(code: str, company: str = "sg", role: str = "hr_admin"):
    """删除报销类型(被引用则拒绝) —— 需 claim_type.delete 权限"""
    if not permissions.can(role, "claim_type.delete"):
        return permissions.deny_payload(role, "claim_type.delete")
    try:
        db.delete_claim_type(company, code)
        return {"ok": True}
    except ValueError as e:
        return {"error": str(e)}


# ═══════ 通用模块记录 CRUD(让所有表格模块都能真新增/删除) ═══════
@app.get("/api/module_records/{module_id}")
def list_module_records(module_id: str, company: str = "sg"):
    return {"records": db.list_module_records(module_id, company)}


@app.post("/api/module_records")
def add_module_record(req: ModuleRecordReq):
    """新增配置记录 —— 需 module_record.create 权限"""
    if not permissions.can(req.role, "module_record.create"):
        return permissions.deny_payload(req.role, "module_record.create")
    rec = db.add_module_record(req.module_id, req.company, req.payload)
    return {"ok": True, "record": rec}


@app.delete("/api/module_records/{rid}")
def delete_module_record(rid: int, company: str = "sg", role: str = "hr_admin"):
    """删除配置记录 —— 需 module_record.delete 权限"""
    if not permissions.can(role, "module_record.delete"):
        return permissions.deny_payload(role, "module_record.delete")
    return {"ok": db.delete_module_record(rid, company)}


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
    """表单提交报销单:7条验证 → 构建审批链(条件路由) → AI预判 → 真写库"""
    from app.core import workflow
    company = req.company
    cur = req.currency or db.COMPANY_CURRENCY.get(company, "CNY")
    emp = db.get_employee(req.emp_id or None, company) or {}
    ctype = db.get_claim_type(req.type_code, company)
    if not ctype:
        return {"error": f"unknown type_code {req.type_code}"}
    base = calc.to_base_currency(req.amount, cur, db.COMPANY_CURRENCY.get(company, "CNY"))
    tax = calc.deductible_tax(base, company)

    # ── 7 条验证规则 (文档 流程3 第2步) ──
    val = calc.validate_claim(
        company=company, emp_id=emp.get("id", ""), ctype=ctype,
        amount=req.amount, amount_base=base,
        receipt_no=req.receipt_no, invoice_date=req.invoice_date,
        confirm_date=emp.get("confirm_date", ""), has_attachment=req.has_attachment)
    risk = calc.risk_score(req.amount, ctype["limit_amt"], exceed=not val["passed"])

    # ── 阻止级错误 → 拒绝入库, 返回明确提示 ──
    if val["blocking"]:
        return {"claim": None, "validation": val, "risk": risk,
                "blocked": True,
                "message": "提交被拦截:" + "；".join(i["zh"] for i in val["issues"])}

    # ── 构建审批链 (按金额条件路由: >2000→财务; >10000→CFO) ──
    chain = workflow.build_chain("claim", {"amount_base": base})
    # ── AI 预判 (审批级别预测 + 风险摘要) ──
    predict = _ai_predict_approval(req.amount, base, ctype, chain, risk, val)

    saved = db.create_claim({
        "company": company, "emp_id": emp.get("id", ""), "emp_name": emp.get("name", ""),
        "type_code": ctype["code"], "type_name": ctype["name"], "merchant": req.merchant,
        "amount": req.amount, "currency": cur, "amount_base": base, "tax_amount": tax,
        "invoice_date": req.invoice_date, "receipt_no": req.receipt_no,
        "note": req.note, "risk_score": risk["score"], "risk_level": risk["level"],
        "risk_reasons": risk["reasons"], "status": "pending", "source": "form",
        "approval_chain": chain, "cur_level": 1,
    })
    return {"claim": saved, "validation": val, "risk": risk,
            "tax_amount": tax, "amount_base": base,
            "approval_chain": chain,
            "chain_summary": workflow.chain_summary(chain),
            "ai_predict": predict}


def _ai_predict_approval(amount: float, base: float, ctype: dict,
                         chain: list, risk: dict, val: dict) -> dict:
    """AI 辅助预判:审批层级解读 + 通过率预测 + 一句话风险摘要。
    规则推理为主(轻量、零延迟); 可后续接 LLM 增强。"""
    levels = len(chain)
    # 通过率: 风险越高 / 越超限 → 概率越低
    score = risk.get("score", 0)
    warn_n = len(val.get("warnings", []))
    prob = max(20, min(98, 95 - score * 0.6 - warn_n * 8))
    if levels == 1:
        route = "仅需直属经理审批(金额在 RM2000 内)"
    elif levels == 2:
        route = "需经理 + 财务两级审批(金额 > RM2000)"
    else:
        route = "需经理 + 财务 + CFO 三级审批(大额 > RM10000)"
    if score >= 60:
        summary = f"⚠️ 高风险单据,建议审批人重点核验票据真实性。预计通过率 {prob:.0f}%。"
    elif warn_n:
        summary = f"提示:存在 {warn_n} 项警告(如缺附件),补齐后通过率更高。当前预计 {prob:.0f}%。"
    else:
        summary = f"✅ 单据规范,预计顺利通过({prob:.0f}%)。{route}。"
    return {"levels": levels, "route": route,
            "pass_prob": round(prob), "summary": summary}


@app.post("/api/ocr")
def ocr_invoice(req: OcrReq):
    """发票识别:有图 + _ocr 已分发 Vision 模型 → 真识票;否则 NL/示例兜底。
    返回结构化字段供前端回填表单(merchant/category/type_code/amount/currency/date/tax_no/engine)。"""
    from app.agents.sub import workers
    res = workers.extraction_agent("", company=req.company,
                                   image_b64=req.image_b64, mime=req.mime)
    ext = res.get("extracted", {})
    engine = ext.get("engine", "sample")
    # 引擎说明(供前端提示用户当前是真识别还是兜底)
    note_map = {
        "vision": {"zh": "AI 视觉模型已识别票据", "en": "Recognized by AI vision model"},
        "nl": {"zh": "未分发视觉模型,按规则解析", "en": "No vision model bound, parsed by rules"},
        "sample": {"zh": "未分发视觉模型,返回示例数据", "en": "No vision model bound, sample data"},
    }
    return {"extracted": ext, "engine": engine,
            "engine_note": note_map.get(engine, note_map["sample"])}


@app.post("/api/claims/{claim_id}/decide")
def decide_claim(claim_id: str, req: DecideReq):
    """审批:真改状态 + 留痕 —— 需 claim.approve 权限(最高权限可裁决)"""
    if not permissions.can(req.role, "claim.approve"):
        return permissions.deny_payload(req.role, "claim.approve")
    cl = db.decide_claim(claim_id, req.status, req.approver)
    return cl or {"error": "not found"}


@app.post("/api/claims/batch_decide")
def batch_decide(req: BatchDecideReq):
    """批量审批 —— 需 claim.batch_approve 权限"""
    if not permissions.can(req.role, "claim.batch_approve"):
        return permissions.deny_payload(req.role, "claim.batch_approve")
    n = db.batch_decide(req.company, req.status, risk_level=req.risk_level)
    return {"affected": n, "stats": db.claim_stats(req.company)}


@app.post("/api/claims/{claim_id}/advance")
def advance_claim_wf(claim_id: str, req: DecideWfReq):
    """审批流推进 (多级状态机) —— 需 claim.approve 权限。
    decision ∈ approved/rejected/returned;同意后自动流转下一级。"""
    if not permissions.can(req.role, "claim.approve"):
        return permissions.deny_payload(req.role, "claim.approve")
    res = db.advance_claim(claim_id, req.decision, req.by, req.comment)
    return res or {"error": "not found"}


@app.get("/api/claims/{claim_id}/chain")
def get_claim_chain(claim_id: str):
    """查看单据审批链当前状态。"""
    cl = db.get_claim(claim_id)
    if not cl:
        return {"error": "not found"}
    from app.core import workflow
    chain = json.loads(cl.get("approval_chain") or "[]")
    return {"claim_id": claim_id, "status": cl["status"],
            "cur_level": cl.get("cur_level", 0), "chain": chain,
            "summary": workflow.chain_summary(chain)}


@app.get("/api/payroll/postable")
def list_postable(company: str = "sg"):
    """待对接薪资的已批准报销单 (文档 流程3 第5步)。"""
    rows = db.list_postable_claims(company)
    total = round(sum(float(r["amount_base"]) for r in rows), 2)
    return {"claims": rows, "count": len(rows), "total": total}


@app.post("/api/payroll/post")
def post_payroll(req: PostReq):
    """报销对接处理: 批量过账至发薪日历 —— 需 payroll.process 权限。"""
    if not permissions.can(req.role, "payroll.run"):
        return permissions.deny_payload(req.role, "payroll.run")
    cal = req.pay_calendar or datetime.now().strftime("%Y-%m")
    res = db.post_to_payroll(req.company, cal, by="薪资管理员")
    return res


@app.get("/api/payroll/batches")
def list_batches(company: str = "sg"):
    """已过账批次汇总。"""
    return {"batches": db.list_batches(company)}


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
    """新增家属 —— 需 family.manage 权限"""
    if not permissions.can(req.role, "family.manage"):
        return permissions.deny_payload(req.role, "family.manage")
    emp = db.get_employee(req.emp_id or None, req.company) or {}
    return db.add_family(emp.get("id", ""), req.company, req.relation, req.name)


# ═══════ 余额调整(增/减/转移 · 必填原因 · 全留痕) ═══════
@app.post("/api/balance/adjust")
def balance_adjust(req: BalanceAdjustReq):
    """审核调整报销余额 —— 需 balance.adjust 权限(财务/审计/系统管理员)"""
    if not permissions.can(req.role, "balance.adjust"):
        return permissions.deny_payload(req.role, "balance.adjust")
    if not (req.reason or "").strip():
        return {"error": "调整原因必填 / reason is required"}
    if req.amount is None or req.amount <= 0:
        return {"error": "调整金额需大于 0 / amount must be > 0"}
    try:
        res = db.adjust_balance(req.company, req.emp_id or None, req.kind,
                                req.amount, req.reason, req.to_emp_id or None, req.role)
        return {"ok": True, **res}
    except ValueError as e:
        return {"error": str(e)}


@app.get("/api/balance/history")
def balance_history(company: str = "sg", emp_id: str | None = None):
    return {"history": db.balance_history(company, emp_id)}


# ═══════ 报表导出 PPT / Excel(真生成文件) ═══════
@app.post("/api/report/export")
def report_export(req: ReportExportReq):
    """导出报表 —— 需 report.export 权限。真生成 .xlsx / .pptx 文件并返回下载路径。"""
    if not permissions.can(req.role, "report.export"):
        return permissions.deny_payload(req.role, "report.export")
    from app.core import reporting
    try:
        out = reporting.export_report(req.module_id, req.company, req.fmt)
        return {"ok": True, **out}
    except Exception as e:
        return {"error": str(e)}


# ═══════ 马来西亚法定合规表格(Payslip / EPF Borang A / EA Form) ═══════
@app.post("/api/statutory/export")
def statutory_export(req: StatutoryExportReq):
    """导出马来西亚国家级法定表格 —— 需 report.export 权限。真生成 .xlsx。"""
    if not permissions.can(req.role, "report.export"):
        return permissions.deny_payload(req.role, "report.export")
    try:
        # EA Form 官方 PDF 版式(HASiL C.P.8A)
        if req.form_id == "ea_form" and req.fmt == "pdf":
            from app.core import ea_pdf
            year = int(req.period) if req.period.isdigit() else None
            out = ea_pdf.build_ea_pdf(req.company, year, req.emp_no)
            if out.get("error"):
                return out
            return {"ok": True, **out}
        from app.core import statutory
        out = statutory.export_statutory(req.form_id, req.company, req.period, req.emp_no)
        if out.get("error"):
            return out
        return {"ok": True, **out}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/payroll/run")
def payroll_run(company: str = "my", role: str = "payroll"):
    """月度薪资跑批预览: 加班分级 / 按比例工资 / 企业总成本+HRDF (FRS 流程2)。"""
    if not permissions.can(role, "payroll.run"):
        return permissions.deny_payload(role, "payroll.run")
    from app.data import payroll_data as P
    rows, tot = [], {"gross": 0.0, "net": 0.0, "employer": 0.0, "cost": 0.0,
                     "hrdf": 0.0, "ot": 0.0, "pcb": 0.0, "epf_emp": 0.0, "epf_er": 0.0}
    for e in P.PAYROLL_EMPLOYEES:
        m = P.compute_monthly(e)
        rows.append({
            "emp_no": m["emp_no"], "name": m["name"], "dept": m.get("dept", ""),
            "basic": m["basic_pay"], "prorated": m["prorate"]["prorated"],
            "worked_days": m["prorate"]["worked_days"], "month_days": m["prorate"]["month_days"],
            "ot_amount": m["ot_amount"], "ot_breakdown": m["ot_detail"]["breakdown"],
            "hourly": m["ot_detail"]["hourly"],
            "gross": m["gross_total"], "epf_emp": m["epf_emp"], "epf_er": m["epf_er"],
            "socso_emp": m["socso_emp"], "socso_er": m["socso_er"],
            "eis_emp": m["eis_emp"], "eis_er": m["eis_er"],
            "pcb": m["pcb"], "hrdf": m["hrdf"],
            "net_pay": m["net_pay"], "employer_contrib": m["employer_contrib"],
            "total_cost": m["total_cost"],
        })
        tot["gross"] += m["gross_total"]; tot["net"] += m["net_pay"]
        tot["employer"] += m["employer_contrib"]; tot["cost"] += m["total_cost"]
        tot["hrdf"] += m["hrdf"]; tot["ot"] += m["ot_amount"]; tot["pcb"] += m["pcb"]
        tot["epf_emp"] += m["epf_emp"]; tot["epf_er"] += m["epf_er"]
    tot = {k: round(v, 2) for k, v in tot.items()}
    return {"ok": True, "company": company, "count": len(rows), "rows": rows, "totals": tot,
            "ot_rates": P.OT_RATES, "hrdf_rate": P.HRDF_RATE}


# ═══════ AI 老板驾驶舱 + AI 异常稽查 (共享 analytics 引擎) ═══════
@app.get("/api/cockpit/overview")
def cockpit_overview(company: str = "my", month: str = "2026-05", role: str = "finance"):
    """驾驶舱聚合: 企业总成本/HRDF/PCB/加班/部门分布 + 6月趋势 —— 需 cockpit.view。"""
    if not permissions.can(role, "cockpit.view"):
        return permissions.deny_payload(role, "cockpit.view")
    from app.core import analytics
    return analytics.build_overview(company, month)


@app.get("/api/cockpit/anomalies")
def cockpit_anomalies(company: str = "my", month: str = "2026-05", role: str = "finance"):
    """AI 异常稽查: 加班/报销/薪资跳变/总成本突增 + 健康分 —— 需 cockpit.view。"""
    if not permissions.can(role, "cockpit.view"):
        return permissions.deny_payload(role, "cockpit.view")
    from app.core import analytics
    return analytics.detect_anomalies(company, month)


@app.get("/api/cockpit/explain")
def cockpit_explain(company: str = "my", month: str = "2026-05", lang: str = "zh", role: str = "finance"):
    """AI 解读「这个月人力成本为什么涨了」归因分析 —— 需 cockpit.view。"""
    if not permissions.can(role, "cockpit.view"):
        return permissions.deny_payload(role, "cockpit.view")
    from app.core import analytics
    return analytics.explain_cost_change(company, month, lang)


# ═══════ 员工自助门户「我的」(employee 权限) ═══════
# 演示绑定:登录员工 = 薪资名单第一人(MY001)。生产环境应由会话/JWT 注入 emp_no。
DEMO_SELF_EMP = "MY001"


def _self_employee(emp_no: str | None = None):
    """取得当前登录员工的薪资档案(默认演示员工)。"""
    from app.data import payroll_data as P
    target = emp_no or DEMO_SELF_EMP
    for e in P.PAYROLL_EMPLOYEES:
        if e["emp_no"] == target:
            return e
    return P.PAYROLL_EMPLOYEES[0]


@app.get("/api/me/payslip")
def me_payslip(role: str = "employee", emp_no: str | None = None, month: str = "2026-05"):
    """员工自助·我的薪资单(仅本人,不暴露他人) —— 需 payslip.self_view。"""
    if not permissions.can(role, "payslip.self_view"):
        return permissions.deny_payload(role, "payslip.self_view")
    from app.data import payroll_data as P
    e = _self_employee(emp_no)
    m = P.compute_monthly(e)
    # 收入明细
    earnings = [
        {"label_zh": "基本工资", "label_en": "Basic Salary", "amount": m["basic_pay"]},
        {"label_zh": "固定津贴", "label_en": "Fixed Allowance", "amount": m["allow_fixed"]},
        {"label_zh": "免税津贴", "label_en": "Tax-exempt Allowance", "amount": m["allow_taxexempt"]},
        {"label_zh": "加班费", "label_en": "Overtime", "amount": m["ot_amount"]},
        {"label_zh": "佣金", "label_en": "Commission", "amount": m.get("commission", 0)},
        {"label_zh": "奖金", "label_en": "Bonus", "amount": m.get("bonus_month", 0)},
    ]
    earnings = [x for x in earnings if x["amount"]]
    # 扣除明细
    deductions = [
        {"label_zh": "EPF 公积金(员工)", "label_en": "EPF (Employee)", "amount": m["epf_emp"]},
        {"label_zh": "SOCSO 社险(员工)", "label_en": "SOCSO (Employee)", "amount": m["socso_emp"]},
        {"label_zh": "EIS 就业保险(员工)", "label_en": "EIS (Employee)", "amount": m["eis_emp"]},
        {"label_zh": "PCB 预扣税", "label_en": "PCB (MTD)", "amount": m["pcb"]},
        {"label_zh": "天课 Zakat", "label_en": "Zakat", "amount": m.get("zakat", 0)},
    ]
    deductions = [x for x in deductions if x["amount"]]
    return {
        "ok": True, "month": month,
        "emp": {"emp_no": m["emp_no"], "name": m["name"], "designation": m["designation"],
                "dept": m["dept"], "ic_no": m["ic_no"], "epf_no": m["epf_no"],
                "bank_code": m.get("bank_code", ""), "bank_acct": m.get("bank_acct", "")},
        "earnings": earnings, "deductions": deductions,
        "gross_total": m["gross_total"], "total_deduction": m["total_deduction"],
        "net_pay": m["net_pay"],
        "ot_detail": m.get("ot_detail", {}),
    }


@app.get("/api/me/summary")
def me_summary(role: str = "employee", company: str = "my", emp_no: str | None = None):
    """员工自助首屏聚合: 本月净发 + 年度额度 + 报销进度统计 + 待办计数。"""
    if not permissions.can(role, "claim.self_view"):
        return permissions.deny_payload(role, "claim.self_view")
    from app.data import payroll_data as P
    e = _self_employee(emp_no)
    m = P.compute_monthly(e)
    # 真实报销库统计(按公司,演示员工无独立 emp_id 时取全公司聚合作为"我的")
    db_emp = db.get_employee(None, company)
    db_emp_id = db_emp["id"] if db_emp else None
    bal = db.get_balance(db_emp_id, company)
    my_claims = db.list_claims(company, emp_id=db_emp_id) if db_emp_id else db.list_claims(company)
    by_status = {"pending": 0, "approved": 0, "rejected": 0, "paid": 0}
    for c in my_claims:
        st = c.get("status", "")
        by_status[st] = by_status.get(st, 0) + 1
    pending = by_status.get("pending", 0)
    return {
        "ok": True,
        "emp": {"emp_no": m["emp_no"], "name": m["name"], "designation": m["designation"], "dept": m["dept"]},
        "payslip": {"net_pay": m["net_pay"], "gross_total": m["gross_total"],
                    "total_deduction": m["total_deduction"], "month": "2026-05"},
        "balance": {"annual": bal.get("annual", 0), "used": bal.get("used", 0),
                    "remaining": bal.get("remaining", 0), "currency": bal.get("currency", "MYR")},
        "claims": {"total": len(my_claims), "by_status": by_status},
        "todos": pending,
        "family_count": len(db.get_family(db_emp_id, company)),
    }


@app.get("/api/statutory/forms")
def statutory_forms():
    """法定表格清单(供前端渲染)。"""
    from app.core import statutory
    from app.data import payroll_data
    return {
        "forms": [{"id": k, "name_zh": v[0], "name_en": v[1]}
                  for k, v in statutory.STATUTORY_FORMS.items()],
        "employer": payroll_data.EMPLOYER,
        "employee_count": len(payroll_data.PAYROLL_EMPLOYEES),
    }


# ═══════ 员工薪资名单 Excel 导入 ═══════
@app.get("/api/payroll/import/template")
def payroll_import_template(role: str = "payroll"):
    """下载员工薪资名单导入模板 —— 需 report.export 权限。"""
    if not permissions.can(role, "report.export"):
        return permissions.deny_payload(role, "report.export")
    from app.core import payroll_import
    try:
        return {"ok": True, **payroll_import.build_template()}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/payroll/import/parse")
async def payroll_import_parse(file: UploadFile = File(...), role: str = Form("payroll")):
    """上传薪资名单 Excel，解析+校验+精确PCB试算预览 —— 需 report.export 权限。"""
    if not permissions.can(role, "report.export"):
        return permissions.deny_payload(role, "report.export")
    from app.core import payroll_import
    try:
        content = await file.read()
        res = payroll_import.parse_and_validate(content)
        return res
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/report/download/{fname}")
def report_download(fname: str):
    import os
    from app.core import reporting
    path = os.path.join(reporting.EXPORT_DIR, os.path.basename(fname))
    if not os.path.exists(path):
        return {"error": "file not found"}
    return FileResponse(path, filename=fname)


@app.get("/api/audit")
def audit(company: str = "sg"):
    return {"logs": db.recent_audit(company)}


@app.get("/api/whoami")
def whoami(role: str = "employee", lang: str = "zh"):
    """返回当前角色的权限画像(供前端隐藏越权按钮 + 调试)"""
    acts = permissions.ROLE_ACTIONS.get(role, set())
    allowed = list(permissions.ACTIONS.keys()) if "*" in acts else sorted(acts)
    return {"role": role, "allowed": allowed,
            "is_admin": "*" in acts, "describe": permissions.describe(role, lang)}


@app.get("/api/telemetry")
def telemetry_snapshot():
    """AI 中枢实时遥测 —— 供侧边栏「活体仪表盘」轮询。
    返回 13 个 Agent 的真实命中状态(recent/count/since_ms) + 整体吞吐(tps/avg_latency)。"""
    return telemetry.snapshot()


# ═══════════════════════════════════════════════════════════
#  统一配置后台 API —— 基础配置 / 模型管理 / 分发应用
# ═══════════════════════════════════════════════════════════

# 可被分发的 Agent 目标:5 个主 Agent + 3 个内部能力节点
BINDABLE_AGENTS = [
    {"id": "_intent", "name": "意图识别(路由)", "name_en": "Intent Routing", "emoji": "🧭", "scope": "core",
     "desc": "把用户话术路由到正确的主 Agent", "desc_en": "Route user input to the right agent"},
    {"id": "_ocr", "name": "票据 OCR 抽取", "name_en": "Invoice OCR", "emoji": "📸", "scope": "core",
     "desc": "拍照识别发票金额/商户/品类(Vision)", "desc_en": "Vision OCR for invoices"},
    {"id": "_policy", "name": "政策推理", "name_en": "Policy Reasoning", "emoji": "📐", "scope": "core",
     "desc": "复杂规则与配置建议生成", "desc_en": "Complex rules & config advice"},
    {"id": "ClaimMate", "name": "报销伙伴", "name_en": "ClaimMate", "emoji": "🙋", "scope": "main",
     "desc": "对话报销 · 余额 · 差旅", "desc_en": "Chat claim · Balance · Travel"},
    {"id": "ApprovalCopilot", "name": "审批副驾", "name_en": "ApprovalCopilot", "emoji": "✅", "scope": "main",
     "desc": "风险分级 · 批量审批", "desc_en": "Risk grading · Batch approve"},
    {"id": "HRStrategist", "name": "HR战略顾问", "name_en": "HR Strategist", "emoji": "🧠", "scope": "main",
     "desc": "对话式配置 · 政策推理", "desc_en": "Chat config · Policy"},
    {"id": "PayrollNavigator", "name": "薪资领航员", "name_en": "Payroll Navigator", "emoji": "⚙️", "scope": "main",
     "desc": "跑批 · 对账 · 汇率", "desc_en": "Batch · Reconcile · FX"},
    {"id": "InsightOracle", "name": "洞察先知", "name_en": "Insight Oracle", "emoji": "📊", "scope": "main",
     "desc": "NL2SQL · 报表 · 洞察", "desc_en": "NL2SQL · Report · Insight"},
]


class ProviderReq(BaseModel):
    id: str = ""               # 留空则用 preset / 自定义
    preset: str = ""           # tokenhot / deepseek / claude / openai
    name: str = ""
    kind: str = "openai_compatible"
    base_url: str = ""
    api_key: str = ""          # 提交新 Key;留空表示不改


class BindingReq(BaseModel):
    agent_id: str
    provider_id: str | None = None
    model_id: str | None = None


class ModelToggleReq(BaseModel):
    model_pk: int
    enabled: bool


@app.get("/api/admin/presets")
def admin_presets():
    """内置平台预设 + 可分发 Agent 清单(前端下拉用)"""
    return {"presets": llm_gateway.PROVIDER_PRESETS, "agents": BINDABLE_AGENTS}


# ── ① 基础配置:平台 CRUD ──
@app.get("/api/admin/providers")
def admin_list_providers():
    return {"providers": db.list_providers()}


@app.post("/api/admin/providers")
def admin_upsert_provider(req: ProviderReq):
    """新增/更新平台。支持 preset 一键带出 base_url/kind。"""
    pid = req.id
    name, kind, base_url = req.name, req.kind, req.base_url
    if req.preset and req.preset in llm_gateway.PROVIDER_PRESETS:
        ps = llm_gateway.PROVIDER_PRESETS[req.preset]
        pid = pid or req.preset
        name = name or ps["name"]
        kind = ps["kind"]
        base_url = base_url or ps["base_url"]
    if not pid:
        return {"error": "缺少平台标识 id 或 preset"}
    p = db.upsert_provider(pid, name or pid, kind, base_url, req.api_key or None)
    return {"provider": p}


@app.delete("/api/admin/providers/{pid}")
def admin_delete_provider(pid: str):
    db.delete_provider(pid)
    return {"ok": True}


# ── ① 基础配置:Key 验证与激活 ──
@app.post("/api/admin/providers/{pid}/verify")
def admin_verify_provider(pid: str):
    """验证 Key → 通过则置 verified;并自动拉模型列表入库。"""
    p = db.get_provider(pid, with_key=True)
    if not p:
        return {"error": "not found"}
    res = llm_gateway.verify_key(p["kind"], p["base_url"], p.get("api_key", ""))
    if res["ok"]:
        db.set_provider_status(pid, "verified", res["msg"])
        # 顺带拉模型
        try:
            models = llm_gateway.list_models(p["kind"], p["base_url"], p.get("api_key", ""))
            db.replace_models(pid, models)
            res["models_pulled"] = len(models)
        except Exception as e:
            res["models_pulled"] = 0
            res["pull_msg"] = str(e)
    else:
        db.set_provider_status(pid, "error", res["msg"])
    return {"verify": res, "provider": db.get_provider(pid)}


@app.post("/api/admin/providers/{pid}/activate")
def admin_activate_provider(pid: str, on: bool = True):
    """激活/停用平台(只有 verified/active 才能被 Agent 使用)。"""
    p = db.get_provider(pid)
    if not p:
        return {"error": "not found"}
    if on and p["status"] not in ("verified", "active"):
        return {"error": "请先验证 Key 通过后再激活"}
    db.set_provider_status(pid, "active" if on else "verified", "已激活" if on else "已停用")
    return {"provider": db.get_provider(pid)}


# ── ② 模型管理:拉取 / 认定 ──
@app.post("/api/admin/providers/{pid}/models/pull")
def admin_pull_models(pid: str):
    """重新拉取平台模型列表入库。"""
    p = db.get_provider(pid, with_key=True)
    if not p:
        return {"error": "not found"}
    try:
        models = llm_gateway.list_models(p["kind"], p["base_url"], p.get("api_key", ""))
        n = db.replace_models(pid, models)
        return {"count": n, "models": db.list_models(pid)}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/admin/models")
def admin_list_models(provider_id: str | None = None, enabled_only: bool = False):
    return {"models": db.list_models(provider_id, enabled_only)}


@app.post("/api/admin/models/toggle")
def admin_toggle_model(req: ModelToggleReq):
    """认定/取消认定某模型(enabled)。"""
    db.set_model_enabled(req.model_pk, req.enabled)
    return {"ok": True}


# ── ③ 分发应用:Agent ↔ 模型 绑定 ──
@app.get("/api/admin/bindings")
def admin_list_bindings():
    return {"bindings": db.list_bindings(), "agents": BINDABLE_AGENTS}


@app.post("/api/admin/bindings")
def admin_set_binding(req: BindingReq):
    b = db.set_binding(req.agent_id, req.provider_id, req.model_id)
    return {"binding": b, "resolved": db.resolve_binding(req.agent_id) is not None}


@app.get("/api/admin/status")
def admin_status():
    """配置健康总览:有几个激活平台、几个启用模型、几个 Agent 已绑定可用。"""
    providers = db.list_providers()
    active = [p for p in providers if p["status"] == "active" and p["enabled"]]
    models = db.list_models(enabled_only=True)
    bound = [a for a in BINDABLE_AGENTS if db.resolve_binding(a["id"])]
    return {
        "providers_total": len(providers), "providers_active": len(active),
        "models_enabled": len(models), "agents_bound": len(bound),
        "agents_total": len(BINDABLE_AGENTS),
    }


@app.get("/api/chat/stream")
async def chat_stream(message: str, thread_id: str = "default", company: str = "sg",
                      role: str = "employee"):
    """SSE 流式:先推送思考过程,再逐字推送回复(打字机)。
    role:当前登录者身份 —— 贯穿到 AI,实现身份判定与越权裁决。"""
    async def gen():
        result = run_turn(message, thread_id, company, role=role)

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
    # index.html 永不缓存:确保浏览器每次都拿到最新引用(内含静态资源版本号),彻底避免旧缓存
    return FileResponse("static/index.html", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache", "Expires": "0",
    })


class _NoCacheStatic(StaticFiles):
    """静态资源强制每次校验(no-cache),配合 index.html 的 ?v= 版本号彻底杜绝旧缓存"""
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False  # 永不返回 304,始终回传最新内容

    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp


app.mount("/static", _NoCacheStatic(directory="static"), name="static")
