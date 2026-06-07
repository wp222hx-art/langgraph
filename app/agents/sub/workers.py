"""
8 个能力子 Agent (Capability Workers)
对应文档 L4 子 Agent 层:Intent / Extraction / Validation / Risk / Policy / Workflow / Insight / Conversation
每个子 Agent 是一个可被主 Agent 子图调用的能力单元。
MVP 阶段用规则 + Mock 实现,阶段二可平滑替换为真实 LLM 调用。
"""
from __future__ import annotations

import re
from typing import Any

from app.data import mock_db, db, calc
from app.core import llm_gateway


def _llm_cfg(agent_id: str) -> dict | None:
    """解析某 Agent 是否已分发可用模型(配置后台绑定)。"""
    try:
        return db.resolve_binding(agent_id)
    except Exception:
        return None


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


def _intent_by_rules(text: str) -> dict[str, Any]:
    text_l = text.lower()
    for keywords, agent, module in _INTENT_RULES:
        for kw in keywords:
            if kw.lower() in text_l:
                return {"intent": module, "module": module, "target_agent": agent,
                        "confidence": 0.95, "engine": "rule"}
    return {"intent": "通用咨询", "module": "报销申请-自助", "target_agent": "ClaimMate",
            "confidence": 0.6, "engine": "rule"}


_VALID_AGENTS = {"ClaimMate", "ApprovalCopilot", "HRStrategist", "PayrollNavigator", "InsightOracle"}


def intent_agent(text: str) -> dict[str, Any]:
    """意图识别:已分发 LLM 则走 LLM,否则关键词规则兜底。"""
    cfg = _llm_cfg("_intent")
    if cfg:
        try:
            sys = (
                "你是企业报销系统的意图路由器。根据用户输入,判断应路由到哪个主Agent。\n"
                "可选 target_agent: ClaimMate(员工报销/余额/差旅/家属), ApprovalCopilot(审批/批量通过),"
                " HRStrategist(配置报销类型/权益/政策), PayrollNavigator(跑批/对账/汇率),"
                " InsightOracle(报表/分析/洞察)。\n"
                '只输出 JSON: {"target_agent":"...","module":"...","confidence":0.0~1.0}'
            )
            r = llm_gateway.chat_json(cfg, sys, text)
            agent = r.get("target_agent", "")
            if agent in _VALID_AGENTS:
                return {"intent": r.get("module", agent), "module": r.get("module", "报销申请-自助"),
                        "target_agent": agent, "confidence": float(r.get("confidence", 0.9)),
                        "engine": "llm"}
        except Exception:
            pass  # LLM 失败 → 规则兜底
    return _intent_by_rules(text)


# ─────────────────────────────────────────────
# ② ExtractionAgent — 多模态 OCR / 自然语言抽取
# 有图 + _ocr 已分发 Vision 模型 → 走真照片识票
# 否则 → 自然语言真抽金额 + 本地分类(查真表限额) / 示例 OCR 兜底
# ─────────────────────────────────────────────
def _vision_extract(image_b64: str, mime: str, company: str) -> dict | None:
    """有图且 _ocr 已分发多模态模型时,走真 Vision 识票;否则返回 None。"""
    cfg = _llm_cfg("_ocr")
    if not (cfg and image_b64):
        return None
    try:
        r = llm_gateway.vision_ocr(cfg, image_b64, mime=mime)
        cur = r.get("currency") or db.COMPANY_CURRENCY.get(company, "CNY")
        ct = db.get_claim_type(r.get("category", ""), company)
        try:
            amount = float(r.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        return {
            "merchant": r.get("merchant", "") or (ct["name"] if ct else "票据"),
            "category": (ct["name"] if ct else (r.get("category") or "其他")),
            "type_code": ct["code"] if ct else "",
            "amount": amount, "currency": cur,
            "date": r.get("date", "") or "", "tax_no": r.get("tax_no", "") or "",
            "engine": "vision",
        }
    except Exception:
        return None  # Vision 失败 → 上层 NL/示例兜底


def extraction_agent(text: str, company: str = "sg",
                     image_b64: str = "", mime: str = "image/jpeg") -> dict[str, Any]:
    # ① 有图 + 已分发 Vision → 真识票
    v = _vision_extract(image_b64, mime, company)
    if v:
        return {"extracted": v}
    # ② 自然语言真抽金额 + 本地分类
    amt = calc.parse_amount(text)
    ctype = calc.guess_type(text, company)
    cur = db.COMPANY_CURRENCY.get(company, "CNY")
    if ctype:
        extracted = {
            "merchant": _guess_merchant(text) or ctype["name"],
            "category": ctype["name"], "type_code": ctype["code"],
            "amount": amt if amt is not None else 0.0,
            "currency": cur, "date": "", "tax_no": "", "engine": "nl",
        }
    else:
        # ③ 未能本地分类:退回示例 OCR
        ocr = mock_db.mock_ocr_invoice()
        ct = db.get_claim_type(ocr.get("category", ""), company)
        ocr["type_code"] = ct["code"] if ct else ""
        ocr["currency"] = cur
        if amt is not None:
            ocr["amount"] = amt
        ocr["engine"] = "sample"
        extracted = ocr
    return {"extracted": extracted}


_MERCHANT_KWS = {
    "海底捞": "海底捞火锅", "滴滴": "滴滴出行", "打车": "滴滴出行",
    "酒店": "酒店住宿", "机票": "携程机票", "京东": "京东商城",
}


def _guess_merchant(text: str) -> str | None:
    for kw, name in _MERCHANT_KWS.items():
        if kw in text:
            return name
    return None


# ─────────────────────────────────────────────
# ③ ValidationAgent — 业务规则合规校验(真实限额比对)
# ─────────────────────────────────────────────
def validation_agent(extracted: dict, company: str = "sg") -> dict[str, Any]:
    cat = extracted.get("category", "")
    code = extracted.get("type_code", "")
    amount = extracted.get("amount", 0) or 0
    ctype = db.get_claim_type(code, company) or db.get_claim_type(cat, company)
    if not ctype:
        return {"validation": {"passed": False, "issues": [
            {"code": "NO_TYPE", "zh": f"未匹配到报销类型「{cat}」",
             "en": f"No matching claim type for {cat}"}], "type": None}}
    res = calc.validate_limit(amount, ctype["limit_amt"], ctype["name"])
    res["type"] = ctype
    return {"validation": res}


# ─────────────────────────────────────────────
# ④ RiskAgent — 风险评分与反欺诈(多因子真加权)
# ─────────────────────────────────────────────
def risk_agent(extracted: dict, validation: dict) -> dict[str, Any]:
    amount = extracted.get("amount", 0) or 0
    ctype = validation.get("type") or {}
    limit_amt = ctype.get("limit_amt", 0)
    exceed = not validation.get("passed", True) and bool(validation.get("issues"))
    no_invoice = not extracted.get("tax_no")
    return {"risk": calc.risk_score(amount, limit_amt, exceed=exceed, no_invoice=no_invoice)}


# ─────────────────────────────────────────────
# ⑤ PolicyAgent — 政策推理与复杂规则
# ─────────────────────────────────────────────
_POLICY_RULES = {
    "报销权益": "建议 P7 及以上年度权益设为 3.5 万,P5-P6 设为 2.5 万,与市场 75 分位对齐。",
    "生成权益流程": "检测到 3 名员工本年度晋升,建议按新职级重新核算年度权益包。",
    "报销类型": "建议新增类型时关联税务编码与单笔限额,并设置是否强制上传发票。",
    "余额调整": "调整需记录理由并留痕,单次调整超 5000 元建议触发二级审批。",
}


def _policy_by_rules(module: str) -> dict[str, Any]:
    return {"policy": {"suggestion": _POLICY_RULES.get(module, "已应用标准政策规则。"),
                       "engine": "rule"}}


def policy_agent(module: str, text: str) -> dict[str, Any]:
    """政策推理:已分发 LLM 则走 LLM 生成专业政策建议,否则规则兜底。"""
    cfg = _llm_cfg("_policy")
    if cfg:
        try:
            sys = (
                "你是企业报销政策顾问。基于用户场景给出一条简明、可执行的政策建议(限80字内),"
                "覆盖额度/税务/审批/留痕/合规角度。只输出建议正文,不要前缀、不要 JSON。"
            )
            reply = llm_gateway.chat(cfg, [
                {"role": "system", "content": sys},
                {"role": "user", "content": f"场景模块:{module}\n用户输入:{text}"},
            ], temperature=0.3, max_tokens=200)
            reply = (reply or "").strip()
            if reply:
                return {"policy": {"suggestion": reply, "engine": "llm"}}
        except Exception:
            pass  # LLM 失败 → 规则兜底
    return _policy_by_rules(module)


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
def insight_agent(module: str, text: str, company: str = "sg") -> dict[str, Any]:
    # 阶段A: 从真实报销库聚合出报表(而非 mock)
    claims = db.list_claims(company, limit=500)
    if not claims:
        return {"report": mock_db.mock_report_data(module + text)}
    cur = db.COMPANY_CURRENCY.get(company, "CNY")
    if "差旅" in module:
        buckets = {}
        for c in claims:
            if c["type_code"] in ("FLIGHT", "HOTEL", "TRAIN"):
                buckets[c["type_name"]] = buckets.get(c["type_name"], 0) + c["amount_base"]
        labels = list(buckets.keys()) or ["机票", "住宿"]
        data = [round(buckets.get(l, 0), 2) for l in labels]
        total = round(sum(data), 2)
        return {"report": {"labels": labels,
                           "series": [{"name": f"差旅支出({cur})", "data": data}],
                           "insight": f"差旅类报销合计 {total} {cur},其中 {labels[0] if labels else ''} 占比最高。"}}
    # 默认: 按部门聚合报销总额
    by_dept = {}
    for c in claims:
        emp = db.get_employee(c["emp_id"], company)
        dept = emp["dept"] if emp else "其他"
        by_dept[dept] = by_dept.get(dept, 0) + c["amount_base"]
    labels = list(by_dept.keys())
    data = [round(by_dept[l], 2) for l in labels]
    top = labels[data.index(max(data))] if data else "-"
    return {"report": {"labels": labels,
                       "series": [{"name": f"报销总额({cur})", "data": data}],
                       "insight": f"{top} 报销额最高。共 {len(claims)} 笔单据,合计 {round(sum(data),2)} {cur}。"}}


# ─────────────────────────────────────────────
# ⑧ ConversationAgent — 多轮对话与人格化风格
# ─────────────────────────────────────────────
_PERSONA = {
    "ClaimMate": "😊 报销伙伴,亲切、高效,帮员工快速搞定报销/余额/差旅。",
    "ApprovalCopilot": "🛡️ 审批副驾,严谨、果断,为审批把关并给出处置建议。",
    "HRStrategist": "🧠 HR 战略顾问,专业、有数据洞察,擅长权益与政策设计。",
    "PayrollNavigator": "⚙️ 薪资领航员,精确、流程化,负责跑批/对账/汇率换算。",
    "InsightOracle": "📊 数据洞察先知,洞察敏锐,善于把数据转成决策建议。",
}


def conversation_agent(agent: str, content: str, perm_profile: str = "") -> str:
    """人格化润色:主 Agent 已分发 LLM 则用其人格重写回复,无绑定则原样返回(零回归)。
    perm_profile:当前登录者的身份与权限画像 —— 注入系统提示,让 AI 全程知道'在为谁服务、
    他能做什么',从而在对话里主动守住权限边界、拒绝越权请求(权限贯穿)。"""
    if not content or not content.strip():
        return content
    cfg = _llm_cfg(agent)
    if cfg:
        try:
            persona = _PERSONA.get(agent, "企业报销助手")
            perm_block = ""
            if perm_profile:
                perm_block = (
                    f"\n{perm_profile}\n"
                    "你必须始终遵守上述权限边界:若回复内容涉及当前登录者无权执行的操作,"
                    "应明确指出其权限不足、并告知应由哪个角色处理,绝不擅自越权代办。\n"
                )
            sys = (
                f"你的人格设定:{persona}\n"
                f"{perm_block}"
                "请用该人格的语气润色下面这段系统回复,使其更自然、专业、有温度。"
                "严格保留所有数字、金额、单据编号、状态等事实信息,不得编造或删改。"
                "保持简洁,不要加多余寒暄,直接输出润色后的正文。"
            )
            reply = llm_gateway.chat(cfg, [
                {"role": "system", "content": sys},
                {"role": "user", "content": content},
            ], temperature=0.4, max_tokens=600)
            reply = (reply or "").strip()
            if reply:
                return reply
        except Exception:
            pass  # LLM 失败 → 原文返回
    return content
