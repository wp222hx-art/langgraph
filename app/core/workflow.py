"""
审批流引擎 (Workflow Engine)
═══════════════════════════════════════════════════════════════════
对应《业务流程与财务报表格式规范》第二部分 · 审批流机制。

模块无关设计 (module-agnostic)：请假 / 加班 / 报销 / 费用 共用同一引擎。

核心实体
  · 审批定义 (ApprovalDefinition)  —— 编码 / 模块 / 多级
  · 审批级别 (ApprovalLevel)       —— 级别号 / 审批人类型 / 条件
  · 审批条件 (ApprovalCondition)   —— 字段 / 运算符 / 阈值 → 路由动作
  · 委托审批人 (Delegation)        —— 原审批人 / 委托人 / 时间范围

状态机
  submitted → in_review(L1 → L2 → L3 …) → approved | rejected | returned

文档关键业务规则:
  · 多级审批: 一级→二级→三级, 每级可配置条件和审批人
  · 条件路由: 请假>3天需二级; >10天需三级 (报销>金额阈值同理)
  · 审批人类型: 角色 / 职位 / 指定用户 / 汇报线
  · 委托代理: 审批人可设代理人和时间范围
  · 退回修改: 保留已通过审批步骤, 重新提交后继续
"""
from __future__ import annotations
from datetime import date, datetime

# ════════════════ 审批定义 (内置默认配置, 可被租户覆盖) ════════════════
# 文档: 模块 ∈ {请假 | 加班 | 报销 | 费用}; 条件路由按金额/天数阈值升级级别
APPROVAL_DEFINITIONS: dict[str, dict] = {
    "claim": {
        "code": "AP-CLAIM",
        "name": "报销审批流", "name_en": "Claim Approval",
        "module": "报销",
        "levels": [
            {"level": 1, "approver_type": "role", "approver_value": "manager",
             "name": "直属经理", "name_en": "Line Manager", "condition": None},
            {"level": 2, "approver_type": "role", "approver_value": "finance",
             "name": "财务负责人", "name_en": "Finance Head",
             "condition": {"field": "amount_base", "op": ">", "value": 2000}},
            {"level": 3, "approver_type": "role", "approver_value": "sys_admin",
             "name": "总监 / CFO", "name_en": "Director / CFO",
             "condition": {"field": "amount_base", "op": ">", "value": 10000}},
        ],
    },
    "leave": {
        "code": "AP-LEAVE",
        "name": "请假审批流", "name_en": "Leave Approval",
        "module": "请假",
        "levels": [
            {"level": 1, "approver_type": "role", "approver_value": "manager",
             "name": "直属主管", "name_en": "Supervisor", "condition": None},
            {"level": 2, "approver_type": "role", "approver_value": "hr_admin",
             "name": "部门负责人", "name_en": "Dept Head",
             "condition": {"field": "total_days", "op": ">", "value": 3}},
            {"level": 3, "approver_type": "role", "approver_value": "sys_admin",
             "name": "总监 / HR", "name_en": "Director / HR",
             "condition": {"field": "total_days", "op": ">", "value": 10}},
        ],
    },
    "overtime": {
        "code": "AP-OT",
        "name": "加班审批流", "name_en": "Overtime Approval",
        "module": "加班",
        "levels": [
            {"level": 1, "approver_type": "role", "approver_value": "manager",
             "name": "直属主管", "name_en": "Supervisor", "condition": None},
            {"level": 2, "approver_type": "role", "approver_value": "hr_admin",
             "name": "部门负责人", "name_en": "Dept Head",
             "condition": {"field": "ot_hours", "op": ">", "value": 24}},
        ],
    },
}

# 委托审批人 (内存态, 演示用; 生产可落库)
_DELEGATIONS: list[dict] = []


# ════════════════ 条件求值 ════════════════
def _eval_condition(cond: dict | None, ctx: dict) -> bool:
    """求值单条审批条件。无条件 → 恒为 True (该级别始终启用)。"""
    if not cond:
        return True
    field, op, val = cond.get("field"), cond.get("op"), cond.get("value")
    actual = ctx.get(field)
    if actual is None:
        return False
    try:
        actual = float(actual); val = float(val)
    except (TypeError, ValueError):
        return str(actual) == str(val)
    return {
        ">": actual > val, "<": actual < val, "=": actual == val,
        ">=": actual >= val, "<=": actual <= val,
    }.get(op, False)


# ════════════════ 委托代理 ════════════════
def add_delegation(from_approver: str, to_approver: str,
                   start: str, end: str, scope: str = "all") -> dict:
    """登记委托代理。scope = 'all' 或具体审批编码。"""
    d = {"from": from_approver, "to": to_approver,
         "start": start, "end": end, "scope": scope, "active": True}
    _DELEGATIONS.append(d)
    return d


def resolve_delegate(approver_role: str, module: str,
                     on: str | None = None) -> str:
    """若 approver_role 在指定日期有生效委托 → 返回委托人, 否则原值。"""
    today = on or date.today().isoformat()
    code = APPROVAL_DEFINITIONS.get(module, {}).get("code", "")
    for d in _DELEGATIONS:
        if not d["active"] or d["from"] != approver_role:
            continue
        if d["scope"] not in ("all", code):
            continue
        if d["start"] <= today <= d["end"]:
            return d["to"]
    return approver_role


# ════════════════ 审批链构建 (核心) ════════════════
def build_chain(module: str, ctx: dict) -> list[dict]:
    """
    根据审批定义 + 上下文(金额/天数等)按条件路由动态构建审批链。
    返回: [{level, approver_type, approver_value(已解析委托), name, status}, ...]
    文档: 条件路由 —— 仅当满足条件的级别才纳入链路 (如 >RM2000 才进二级)。
    """
    defi = APPROVAL_DEFINITIONS.get(module)
    if not defi:
        # 无审批定义 → 单级兜底 (文档: 无规则 → 直接进审批中由经理裁决)
        return [{"level": 1, "approver_type": "role", "approver_value": "manager",
                 "name": "审批人", "name_en": "Approver", "status": "pending"}]
    chain: list[dict] = []
    seq = 0
    for lv in defi["levels"]:
        if not _eval_condition(lv.get("condition"), ctx):
            continue
        seq += 1
        approver = resolve_delegate(lv["approver_value"], module)
        chain.append({
            "level": seq,
            "approver_type": lv["approver_type"],
            "approver_value": approver,
            "delegated": approver != lv["approver_value"],
            "name": lv["name"], "name_en": lv["name_en"],
            "status": "pending", "decided_by": None,
            "decided_at": None, "comment": None,
        })
    return chain or [{"level": 1, "approver_type": "role",
                      "approver_value": "manager", "name": "审批人",
                      "name_en": "Approver", "status": "pending"}]


# ════════════════ 状态机推进 ════════════════
def advance(chain: list[dict], decision: str, by: str,
            comment: str = "") -> dict:
    """
    推进审批链状态机。
      decision ∈ {approved | rejected | returned}
      返回: {overall, chain, current_level, finished}
        overall ∈ {in_review | approved | rejected | returned}

    文档状态机:
      · 同意 → 检查下一级; 无下级 → 已批准
      · 拒绝 → 终态 已拒绝
      · 退回修改 → 终态 退回员工修改 (保留已通过步骤)
    """
    # 找当前待处理级别 (第一个 pending)
    cur = next((s for s in chain if s["status"] == "pending"), None)
    if cur is None:
        return {"overall": "approved", "chain": chain,
                "current_level": None, "finished": True}

    cur["decided_by"] = by
    cur["decided_at"] = datetime.now().isoformat(timespec="seconds")
    cur["comment"] = comment

    if decision == "rejected":
        cur["status"] = "rejected"
        return {"overall": "rejected", "chain": chain,
                "current_level": cur["level"], "finished": True}

    if decision == "returned":
        cur["status"] = "returned"
        # 文档: 退回修改保留已通过审批步骤 (前序 approved 不变)
        return {"overall": "returned", "chain": chain,
                "current_level": cur["level"], "finished": True}

    # approved → 看是否还有下一级
    cur["status"] = "approved"
    nxt = next((s for s in chain if s["status"] == "pending"), None)
    if nxt is None:
        return {"overall": "approved", "chain": chain,
                "current_level": cur["level"], "finished": True}
    return {"overall": "in_review", "chain": chain,
            "current_level": nxt["level"], "finished": False}


def chain_summary(chain: list[dict], lang: str = "zh") -> str:
    """生成审批链的一句话可读摘要 (供 UI / AI 复述)。"""
    parts = []
    for s in chain:
        name = s["name"] if lang == "zh" else s.get("name_en", s["name"])
        icon = {"approved": "✅", "rejected": "❌",
                "returned": "↩️", "pending": "⏳"}.get(s["status"], "•")
        tag = "(代)" if s.get("delegated") else ""
        parts.append(f"L{s['level']} {name}{tag} {icon}")
    return " → ".join(parts)


# ════════════════ 通知模板渲染 (文档第二部分末) ════════════════
NOTIFY_TEMPLATE = {
    "subject": "[{{COMPANY}}] {{APPROVAL_CODE}} - {{REQUESTOR}} 提交的{{MODULE}}申请",
    "body": ("各位 {{APPROVER_NAME}}，\n"
             "{{REQUESTOR}} 已提交{{MODULE}}申请，详情如下：\n"
             "- 金额/时长：{{DURATION}}\n- 原因：{{REASON}}\n"
             "- 当前状态：{{STATUS}}\n请及时审批。"),
}


def render_notify(variables: dict) -> dict:
    """变量替换渲染通知 (文档: {{COMPANY}}/{{APPROVAL_CODE}}/… )。"""
    def fill(tpl: str) -> str:
        for k, v in variables.items():
            tpl = tpl.replace("{{" + k + "}}", str(v))
        return tpl
    return {"subject": fill(NOTIFY_TEMPLATE["subject"]),
            "body": fill(NOTIFY_TEMPLATE["body"])}
