"""
PermissionGuard —— AI 权限贯穿核心层
═══════════════════════════════════════════════════════════════
把"权限"从静态菜单过滤,升级为贯穿全系统的【身份判定 + 操作裁决】:

  1. 操作能力矩阵(ACTIONS):细到具体写操作(审批/余额调整/建类型/导出…),
     而非只到菜单级。每个角色拥有一组 action。
  2. can(role, action):任意一处写操作前的统一裁决闸门(后端兜底)。
  3. describe(role):生成 AI 可读的"当前登录者身份与权限画像",
     注入到 Agent 系统提示,让 AI 知道"你在为谁服务、他能做什么",
     从而在对话中【主动拒绝越权请求】(如普通员工让 AI 帮他审批)。

设计原则:最高权限(sys_admin)可处理一切,含审批裁决;
         越权一律 deny,并给出"谁可以做"的引导(AI 友好)。
"""
from __future__ import annotations

# ── 全部受控操作(写操作 / 高敏操作)──
# key: 操作码  value: (中文名, 英文名, 归属域)
ACTIONS: dict[str, tuple[str, str, str]] = {
    # 个人报销
    "claim.create":        ("提交报销", "Submit claim", "my"),
    "claim.self_view":     ("查看本人报销", "View own claims", "my"),
    "family.manage":       ("维护家属信息", "Manage family", "my"),
    "travel.apply":        ("差旅申请", "Travel request", "my"),
    # 审批(核心权力)
    "claim.approve":       ("审批/驳回报销", "Approve/Reject claim", "approve"),
    "claim.batch_approve": ("批量审批", "Batch approve", "approve"),
    # 规则配置(HR/管理员)
    "claim_type.create":   ("新增报销类型", "Create claim type", "settings"),
    "claim_type.update":   ("修改报销类型", "Update claim type", "settings"),
    "claim_type.delete":   ("删除报销类型", "Delete claim type", "settings"),
    "module_record.create":("新增配置记录(组/权益/汇率等)", "Create config record", "settings"),
    "module_record.delete":("删除配置记录", "Delete config record", "settings"),
    "entitlement.generate":("生成年度权益", "Generate entitlement", "settings"),
    # 财务 / 审计(高敏)
    "balance.adjust":      ("调整报销余额(增/减/转移)", "Adjust balance", "audit"),
    "audit.interface":     ("审核接口数据", "Audit interface data", "audit"),
    # 薪资接口
    "payroll.run":         ("执行薪资跑批", "Run payroll batch", "flow"),
    # 报表导出
    "report.export":       ("导出报表(PPT/Excel)", "Export report", "report"),
}

# ── 角色 → 操作集合(* 表示全权)──
ROLE_ACTIONS: dict[str, set[str]] = {
    "employee": {
        "claim.create", "claim.self_view", "family.manage", "travel.apply",
    },
    "approver": {
        "claim.create", "claim.self_view", "family.manage", "travel.apply",
        "claim.approve", "claim.batch_approve",
    },
    "hr_admin": {
        "claim.create", "claim.self_view", "family.manage", "travel.apply",
        "claim.approve", "claim.batch_approve",
        "claim_type.create", "claim_type.update", "claim_type.delete",
        "module_record.create", "module_record.delete", "entitlement.generate",
        "report.export",
    },
    "payroll": {
        "audit.interface", "payroll.run", "report.export",
    },
    "finance": {
        "balance.adjust", "audit.interface", "report.export",
        "claim.approve", "claim.batch_approve",   # 财务负责人参与多级审批 (文档 L2)
    },
    # 系统管理员:全权(含审批裁决) —— 最高权限可把审批操作处理掉
    "sys_admin": {"*"},
}

ROLE_NAMES = {
    "employee": ("普通员工", "Employee"),
    "approver": ("审批人", "Approver"),
    "hr_admin": ("HR 管理员", "HR Admin"),
    "payroll": ("薪资专员", "Payroll Officer"),
    "finance": ("财务/审计", "Finance/Audit"),
    "sys_admin": ("系统管理员", "System Admin"),
}


def can(role: str, action: str) -> bool:
    """裁决:该角色是否可执行某操作。未知角色/操作一律 deny。"""
    role = (role or "").strip() or "employee"
    acts = ROLE_ACTIONS.get(role)
    if acts is None:
        return False
    return "*" in acts or action in acts


def who_can(action: str, lang: str = "zh") -> list[str]:
    """哪些角色可执行该操作(用于越权时给出引导)。"""
    out = []
    for r, acts in ROLE_ACTIONS.items():
        if "*" in acts or action in acts:
            out.append(ROLE_NAMES[r][0 if lang == "zh" else 1])
    return out


def action_name(action: str, lang: str = "zh") -> str:
    info = ACTIONS.get(action)
    if not info:
        return action
    return info[0] if lang == "zh" else info[1]


def deny_payload(role: str, action: str, lang: str = "zh") -> dict:
    """统一的越权拒绝响应体(后端写操作兜底用)。"""
    rn = ROLE_NAMES.get(role, (role, role))[0 if lang == "zh" else 1]
    an = action_name(action, lang)
    allowed = "、".join(who_can(action, lang)) if lang == "zh" else ", ".join(who_can(action, lang))
    if lang == "en":
        msg = f"Permission denied: role 「{rn}」 cannot perform 「{an}」. Allowed roles: {allowed}."
    else:
        msg = f"权限不足:当前身份「{rn}」无权执行「{an}」。可执行该操作的角色:{allowed}。"
    return {"error": msg, "denied": True, "action": action, "role": role,
            "allowed_roles": who_can(action, lang)}


def describe(role: str, lang: str = "zh") -> str:
    """生成 AI 可读的【身份与权限画像】,注入 Agent 系统提示。
    让 AI 知道'登录的是谁、权限如何',据此主动拒绝越权请求。"""
    role = (role or "employee").strip()
    rn = ROLE_NAMES.get(role, (role, role))[0 if lang == "zh" else 1]
    acts = ROLE_ACTIONS.get(role, set())
    if "*" in acts:
        if lang == "en":
            return (f"[Identity] Logged-in user role: {rn} (highest privilege). "
                    f"Can perform ALL operations including approving/rejecting claims, "
                    f"balance adjustment, rule config, payroll and exports. No restriction.")
        return (f"[身份] 当前登录者角色:{rn}(最高权限)。可执行系统全部操作,"
                f"包括审批/驳回报销、余额调整、规则配置、薪资跑批与报表导出,无限制。")
    names = [action_name(a, lang) for a in sorted(acts)]
    can_list = "、".join(names) if lang == "zh" else ", ".join(names)
    # 明确列出"不可做"的高敏操作,便于 AI 拒绝
    forbidden = [action_name(a, lang) for a in ACTIONS if a not in acts and "*" not in acts]
    cant_list = "、".join(forbidden) if lang == "zh" else ", ".join(forbidden)
    if lang == "en":
        return (f"[Identity] Logged-in user role: {rn}. "
                f"ALLOWED operations: {can_list}. "
                f"FORBIDDEN (must refuse if requested): {cant_list}. "
                f"If the user asks you to perform a forbidden operation, politely refuse, "
                f"explain the permission boundary, and tell them which role can do it.")
    return (f"[身份] 当前登录者角色:{rn}。"
            f"【可执行】{can_list}。"
            f"【禁止执行,被请求时须拒绝】{cant_list}。"
            f"若用户要求你执行禁止操作(如越权审批),须礼貌拒绝、说明权限边界,并告知应由哪个角色处理。")
