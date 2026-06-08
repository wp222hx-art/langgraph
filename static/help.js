// ═══════════════════════════════════════════════════════════
//  Paydaes ClaimGPT · 帮助中心(中英双语)
//  数据驱动:HELP_DOC[lang] → 渲染选项卡 + 内容
// ═══════════════════════════════════════════════════════════

const HELP_DOC = {
  zh: {
    tabs: [
      { id: 'intro', icon: 'fa-circle-info', label: '系统介绍' },
      { id: 'quick', icon: 'fa-rocket', label: '快速上手' },
      { id: 'roles', icon: 'fa-users-gear', label: '角色流程' },
      { id: 'ai', icon: 'fa-robot', label: 'AI 助手' },
      { id: 'modules', icon: 'fa-cubes', label: '功能模块' },
      { id: 'faq', icon: 'fa-circle-question', label: '常见问题' },
    ],
    intro: `
<h2>🏢 Paydaes ClaimGPT 是什么</h2>
<p><b>Paydaes ClaimGPT</b> 是一套<b>AI 原生(AI-Native)的集团级智能报销与人力资源平台</b>。它把传统"填表 → 审批 → 跑批"的报销流程,升级为<b>用一句话对话即可完成</b>的智能体验。</p>
<div class="hp-card">
  <b>核心理念:</b>不是给旧系统加一个 AI 聊天框,而是<b>以 AI 为中枢重新设计整个工作流</b>——13 个 Agent(5 主 + 8 子)在后台协同,把你的大白话翻译成结构化操作。
</div>
<h3>🎯 三大价值</h3>
<ul>
  <li><b>对话式报销</b>:拍张发票、说一句话,AI 自动识别、校验、提交,无需填表。</li>
  <li><b>AI 风险副驾</b>:审批时 AI 自动分级风险、批量处理,把审批人从重复劳动中解放。</li>
  <li><b>全球合规</b>:内置新加坡/马来西亚等多国税务、报销、做账规则,跨境企业开箱即用。</li>
</ul>
<h3>🧠 技术架构</h3>
<ul>
  <li><b>AI 编排</b>:LangGraph StateGraph 状态图,意图路由 → 主 Agent → 子 Agent → 人机协同</li>
  <li><b>13 个 Agent</b>:5 主(报销伙伴/审批副驾/HR 战略顾问/薪资领航员/洞察先知)+ 8 子(意图/政策/风险/抽取/流程/权益/对话/审计)</li>
  <li><b>权限贯穿</b>:AI 全程"知道你是谁、能做什么",主动拒绝越权请求</li>
  <li><b>实时可观测</b>:侧边栏 AI 中枢面板,真实反映每个 Agent 的调用状态</li>
</ul>`,
    quick: `
<h2>🚀 三步上手</h2>
<div class="hp-step"><span class="hp-num">1</span><div><b>选择你的身份</b><br>点击右上角头像,切换角色(员工/审批人/HR/薪资/财务/系统管理员)。不同角色看到不同功能与权限。</div></div>
<div class="hp-step"><span class="hp-num">2</span><div><b>选择公司与语言</b><br>左上角切换集团下的子公司(🇸🇬 新加坡 / 🇲🇾 马来西亚等),右上角切换中英文。系统自动加载对应国家的合规规则。</div></div>
<div class="hp-step"><span class="hp-num">3</span><div><b>呼出 AI 助手</b><br>点击右上角 <i class="fas fa-robot"></i> <b>AI 助手</b>,用大白话描述你的需求,比如"我要报销一张 200 元的出租车票",AI 会自动完成。</div></div>
<h3>💡 最快的报销方式</h3>
<div class="hp-card">
  打开 AI 助手 → 直接说 <b>"帮我报销 [金额] 的 [类型]"</b> → AI 识别、校验、生成报销单 → 完成 ✅<br>
  例如:"报销一张 200 元的出租车票"、"提交今天午餐 80 元的餐饮费"
</div>
<h3>🧭 界面导览</h3>
<ul>
  <li><b>顶栏</b>:集团/公司切换、全球合规、语言、帮助、通知、角色、AI 助手</li>
  <li><b>左侧导航</b>:报销、差旅、税务、假期、薪资、做账等全功能模块树</li>
  <li><b>左下角</b>:AI 中枢状态面板(实时显示 13 个 Agent 的工作状态)</li>
  <li><b>主工作区</b>:当前模块的数据表格、卡片、图表</li>
  <li><b>右侧抽屉</b>:AI 助手对话窗(含思考链、数据卡片)</li>
</ul>`,
    roles: `
<h2>👥 6 种角色的使用流程</h2>
<p>系统按角色划分权限,每个角色有专属的工作流。下面是完整的"该角色一天怎么用"。</p>

<div class="hp-role"><b>🙋 员工 (Employee)</b><span class="hp-perm">权限:提交报销/查询/家属登记/对话</span>
<ol>
  <li>呼出 AI 助手,说"我要报销出租车票 200 元"</li>
  <li>AI 自动识别金额、类型、校验额度限额,生成报销单</li>
  <li>或:进入「报销申请」模块,拍照上传发票 → AI OCR 自动填表</li>
  <li>登记家属信息(用于家属医疗等权益报销)</li>
  <li>查询自己的报销状态与剩余额度</li>
</ol></div>

<div class="hp-role"><b>✅ 审批人 (Approver)</b><span class="hp-perm">权限:单笔/批量审批、风险查看</span>
<ol>
  <li>对 AI 说"帮我分析待审批单据的风险"</li>
  <li>AI(审批副驾)自动对所有待审单据做风险分级(🟢低/🟡中/🔴高)</li>
  <li>对低风险单据说"批量通过",AI 一键批准</li>
  <li>高风险单据进入人机协同(HIL),需人工确认</li>
</ol></div>

<div class="hp-role"><b>🧑‍💼 HR 管理员 (HR Admin)</b><span class="hp-perm">权限:最广(13 项)报销类型/权益/假期/政策配置</span>
<ol>
  <li>用大白话配置规则:"P7 以上员工年度培训额度 35000 元"</li>
  <li>AI(HR 战略顾问)把自然语言翻译成结构化权益规则</li>
  <li>管理报销类型、报销组、假期权益、假期类型</li>
  <li>一键生成全员年度权益包(由 WorkflowAgent 后台跑批)</li>
</ol></div>

<div class="hp-role"><b>⚙️ 薪资专员 (Payroll)</b><span class="hp-perm">权限:薪资跑批、汇率、接口数据</span>
<ol>
  <li>对 AI 说"执行本月薪资跑批"</li>
  <li>AI(薪资领航员)自主校验所有单据 → 生成付款文件 → 推送薪资系统</li>
  <li>管理汇率、薪资变量、银行信息</li>
</ol></div>

<div class="hp-role"><b>💰 财务 (Finance)</b><span class="hp-perm">权限:额度调整、报表导出</span>
<ol>
  <li>调整员工年度额度(增加/减少/转移,必填理由,全程留痕)</li>
  <li>对 AI 说"生成本季度报销分析报告"</li>
  <li>AI(洞察先知)分析数据 → 一键导出 Excel / PPT 报表</li>
  <li>查看做账科目、总账、税务回单</li>
</ol></div>

<div class="hp-role"><b>🛡️ 系统管理员 (Sys Admin)</b><span class="hp-perm">权限:全部(16 项)+ AI 配置后台</span>
<ol>
  <li>拥有所有功能权限</li>
  <li>进入「AI 配置后台」:接入大模型平台(TokenHot 等)、管理 API Key</li>
  <li>把模型分发给不同 Agent(意图识别 / OCR / 政策推理 / 5 主 Agent)</li>
  <li>查看完整审计日志与 AI 中枢遥测</li>
</ol></div>`,
    ai: `
<h2>🤖 AI 助手怎么用</h2>
<p>AI 助手是整个系统的核心入口。<b>你不需要记菜单、不需要填表</b>,只要用大白话描述需求即可。</p>
<h3>🗣️ 常用指令示例</h3>
<table class="hp-table">
  <tr><th>你说</th><th>AI 做什么</th></tr>
  <tr><td>"报销 200 元出租车票"</td><td>识别 → 校验额度 → 生成报销单</td></tr>
  <tr><td>"帮我批量审批待审单据"</td><td>风险分级 → 批量处理(需审批权限)</td></tr>
  <tr><td>"分析市场部报销情况"</td><td>数据洞察 + 图表卡片</td></tr>
  <tr><td>"P7 员工年度额度 35000"</td><td>自然语言 → 结构化权益规则</td></tr>
  <tr><td>"执行薪资跑批"</td><td>校验 → 生成付款文件(需薪资权限)</td></tr>
</table>
<h3>🧠 思考链(Think Chain)</h3>
<p>每次 AI 回答时,你会看到它的"思考过程"——哪个 Agent 在工作、做了什么决策。这让 AI 的每一步都<b>可解释、可追溯</b>。</p>
<h3>🔒 权限边界</h3>
<div class="hp-card">
  AI <b>全程知道你的身份</b>。如果普通员工让 AI "批量审批",AI 会<b>礼貌拒绝</b>并告知应由审批人处理。这保证了安全与合规。
</div>
<h3>💡 AI 中枢面板</h3>
<p>左下角的科幻面板是<b>真·实时可观测仪表盘</b>:13 个 LED 灯对应 13 个 Agent,某个 Agent 被实际调用时,对应的灯会真的亮起来,并显示真实的响应时延与吞吐量。</p>`,
    modules: `
<h2>📦 功能模块总览</h2>
<p>系统覆盖报销、差旅、税务、假期、薪资、做账六大域,共 19+ 个业务模块。</p>
<h3>💳 报销与差旅</h3>
<ul>
  <li><b>报销类型 / 报销组</b>:定义可报销的类目与分组</li>
  <li><b>报销权益</b>:不同职级的年度额度</li>
  <li><b>报销申请</b>:拍照 OCR / 对话式提交</li>
  <li><b>商务差旅申请 / 报销</b>:差旅全流程</li>
  <li><b>汇率</b>:多币种自动换算</li>
</ul>
<h3>🧾 税务合规</h3>
<ul>
  <li><b>税率表 / 税务参数</b>:各国税率(如新加坡 GST 9%)</li>
  <li><b>免税限额 (TP1) / 税务回单</b>:合规计税</li>
  <li><b>EA 表单 / EC 表单</b>:马来西亚法定税表</li>
</ul>
<h3>🏖️ 假期与考勤</h3>
<ul>
  <li><b>假期权益 / 假期类型 / 假期组</b>:假期政策配置</li>
  <li><b>班次 / 排班组 / 假日表</b>:考勤排班</li>
  <li><b>打卡地点 / 加班设置</b>:考勤规则</li>
</ul>
<h3>📒 薪资与做账</h3>
<ul>
  <li><b>会计科目表 (COA) / 总账科目 / 要素分组</b>:做账结构</li>
  <li><b>银行 / 薪资变量</b>:发薪配置</li>
</ul>
<div class="hp-card">💡 提示:大部分配置都可以<b>直接对 AI 说大白话</b>完成,无需手动进入模块填表。</div>`,
    faq: `
<h2>❓ 常见问题</h2>
<div class="hp-q"><b>Q: 我不知道某个功能在哪,怎么办?</b><br>A: 直接呼出 AI 助手,用大白话问,比如"我在哪里设置假期权益?"AI 会引导你。</div>
<div class="hp-q"><b>Q: 报销额度不够了怎么办?</b><br>A: 联系财务调整额度。财务可在系统中增加/减少/转移额度,全程留痕。</div>
<div class="hp-q"><b>Q: AI 拒绝了我的请求?</b><br>A: 说明该操作超出你当前角色的权限。请切换到对应角色,或联系有权限的同事。</div>
<div class="hp-q"><b>Q: 支持哪些国家的合规规则?</b><br>A: 当前内置新加坡、马来西亚等。每个国家有独立的税务、报销、做账规则。</div>
<div class="hp-q"><b>Q: 拍照报销识别不准?</b><br>A: 确保发票清晰、光线充足。识别后可手动修正 AI 填写的字段再提交。</div>
<div class="hp-q"><b>Q: 怎么切换语言?</b><br>A: 点击右上角语言按钮,支持中文/English 全量切换。</div>
<div class="hp-card">还有问题?直接问 AI 助手,它 7×24 在线 🤖</div>`,
  },

  en: {
    tabs: [
      { id: 'intro', icon: 'fa-circle-info', label: 'Overview' },
      { id: 'quick', icon: 'fa-rocket', label: 'Quick Start' },
      { id: 'roles', icon: 'fa-users-gear', label: 'Role Flows' },
      { id: 'ai', icon: 'fa-robot', label: 'AI Assistant' },
      { id: 'modules', icon: 'fa-cubes', label: 'Modules' },
      { id: 'faq', icon: 'fa-circle-question', label: 'FAQ' },
    ],
    intro: `
<h2>🏢 What is Paydaes ClaimGPT</h2>
<p><b>Paydaes ClaimGPT</b> is an <b>AI-Native enterprise platform</b> for intelligent expense claims and HR management. It upgrades the traditional "fill form → approve → run payroll" flow into a <b>conversational experience where one sentence gets the job done</b>.</p>
<div class="hp-card">
  <b>Core philosophy:</b> Not bolting a chatbot onto a legacy system, but <b>redesigning the entire workflow around AI</b> — 13 Agents (5 main + 8 sub) collaborate behind the scenes to translate your plain language into structured operations.
</div>
<h3>🎯 Three Key Values</h3>
<ul>
  <li><b>Conversational Claims</b>: Snap a receipt, say a sentence — AI recognizes, validates, and submits. No forms.</li>
  <li><b>AI Approval Copilot</b>: AI auto-grades risk and batch-processes approvals, freeing approvers from repetitive work.</li>
  <li><b>Global Compliance</b>: Built-in tax, claim, and accounting rules for Singapore, Malaysia and more — ready out of the box for cross-border companies.</li>
</ul>
<h3>🧠 Architecture</h3>
<ul>
  <li><b>AI Orchestration</b>: LangGraph StateGraph — intent routing → main Agent → sub Agent → human-in-the-loop</li>
  <li><b>13 Agents</b>: 5 main (ClaimMate / ApprovalCopilot / HRStrategist / PayrollNavigator / InsightOracle) + 8 sub (Intent/Policy/Risk/Extraction/Workflow/Entitlement/Conversation/Audit)</li>
  <li><b>Permission Pervasion</b>: AI always knows who you are and what you can do, proactively refusing unauthorized requests</li>
  <li><b>Real-time Observability</b>: Sidebar AI Core panel reflects each Agent's real call status</li>
</ul>`,
    quick: `
<h2>🚀 Three Steps to Start</h2>
<div class="hp-step"><span class="hp-num">1</span><div><b>Pick Your Role</b><br>Click the avatar (top-right) to switch role (Employee / Approver / HR / Payroll / Finance / Sys Admin). Each role sees different features and permissions.</div></div>
<div class="hp-step"><span class="hp-num">2</span><div><b>Choose Company & Language</b><br>Switch sub-company (🇸🇬 Singapore / 🇲🇾 Malaysia, etc.) top-left, and language top-right. The system auto-loads each country's compliance rules.</div></div>
<div class="hp-step"><span class="hp-num">3</span><div><b>Summon the AI Assistant</b><br>Click <i class="fas fa-robot"></i> <b>AI Assistant</b> (top-right) and describe your need in plain language, e.g. "Claim a 200 SGD taxi receipt". AI handles the rest.</div></div>
<h3>💡 The Fastest Way to Claim</h3>
<div class="hp-card">
  Open AI Assistant → say <b>"Claim [amount] for [category]"</b> → AI recognizes, validates, creates the claim → Done ✅<br>
  e.g. "Claim a 200 SGD taxi receipt", "Submit 80 SGD lunch as meal expense"
</div>
<h3>🧭 Interface Tour</h3>
<ul>
  <li><b>Top bar</b>: company switch, global compliance, language, help, notifications, role, AI Assistant</li>
  <li><b>Left nav</b>: full module tree — claims, travel, tax, leave, payroll, accounting</li>
  <li><b>Bottom-left</b>: AI Core panel (live status of all 13 Agents)</li>
  <li><b>Main area</b>: data tables, cards, charts for the current module</li>
  <li><b>Right drawer</b>: AI Assistant chat (with think-chain and data cards)</li>
</ul>`,
    roles: `
<h2>👥 Workflows for 6 Roles</h2>
<p>Permissions are role-based; each role has a dedicated workflow. Below is "how each role uses the system day-to-day".</p>

<div class="hp-role"><b>🙋 Employee</b><span class="hp-perm">Perms: submit claim / query / family / chat</span>
<ol>
  <li>Open AI Assistant, say "Claim a 200 SGD taxi receipt"</li>
  <li>AI auto-detects amount & category, validates limits, creates the claim</li>
  <li>Or: go to "Claim Application", upload a photo → AI OCR auto-fills the form</li>
  <li>Register family members (for dependent medical claims, etc.)</li>
  <li>Check your claim status and remaining quota</li>
</ol></div>

<div class="hp-role"><b>✅ Approver</b><span class="hp-perm">Perms: single/batch approval, risk view</span>
<ol>
  <li>Tell AI "Analyze the risk of pending claims"</li>
  <li>AI (ApprovalCopilot) auto-grades all pending claims (🟢low/🟡med/🔴high)</li>
  <li>Say "Approve all low-risk" for one-click batch approval</li>
  <li>High-risk claims enter Human-in-the-Loop (HIL) for manual confirmation</li>
</ol></div>

<div class="hp-role"><b>🧑‍💼 HR Admin</b><span class="hp-perm">Perms: broadest (13) — types/entitlement/leave/policy</span>
<ol>
  <li>Configure rules in plain language: "P7+ employees get 35000 annual training quota"</li>
  <li>AI (HRStrategist) translates natural language into structured entitlement rules</li>
  <li>Manage claim types, claim groups, leave entitlements & types</li>
  <li>One-click generate company-wide annual entitlement packages (WorkflowAgent runs the batch)</li>
</ol></div>

<div class="hp-role"><b>⚙️ Payroll</b><span class="hp-perm">Perms: payroll run, FX, interface data</span>
<ol>
  <li>Tell AI "Run this month's payroll"</li>
  <li>AI (PayrollNavigator) validates all records → generates payment file → pushes to payroll system</li>
  <li>Manage FX rates, payroll variables, bank info</li>
</ol></div>

<div class="hp-role"><b>💰 Finance</b><span class="hp-perm">Perms: balance adjust, report export</span>
<ol>
  <li>Adjust employee annual quota (add/reduce/transfer; reason required; fully audited)</li>
  <li>Tell AI "Generate this quarter's claim analysis report"</li>
  <li>AI (InsightOracle) analyzes data → one-click export to Excel / PPT</li>
  <li>View accounting codes, general ledger, tax receipts</li>
</ol></div>

<div class="hp-role"><b>🛡️ Sys Admin</b><span class="hp-perm">Perms: all (16) + AI Config Console</span>
<ol>
  <li>Has every feature permission</li>
  <li>Enter "AI Config Console": connect LLM platforms (TokenHot etc.), manage API keys</li>
  <li>Dispatch models to different Agents (intent / OCR / policy / 5 main Agents)</li>
  <li>View full audit logs and AI Core telemetry</li>
</ol></div>`,
    ai: `
<h2>🤖 How to Use the AI Assistant</h2>
<p>The AI Assistant is the core entry point. <b>No menus to memorize, no forms to fill</b> — just describe what you need in plain language.</p>
<h3>🗣️ Common Command Examples</h3>
<table class="hp-table">
  <tr><th>You say</th><th>AI does</th></tr>
  <tr><td>"Claim 200 SGD taxi receipt"</td><td>Recognize → validate quota → create claim</td></tr>
  <tr><td>"Batch approve pending claims"</td><td>Risk grading → batch process (needs approval perm)</td></tr>
  <tr><td>"Analyze Marketing dept claims"</td><td>Data insights + chart cards</td></tr>
  <tr><td>"P7 annual quota 35000"</td><td>Natural language → structured entitlement rule</td></tr>
  <tr><td>"Run payroll"</td><td>Validate → generate payment file (needs payroll perm)</td></tr>
</table>
<h3>🧠 Think Chain</h3>
<p>With each answer, you see the AI's "thinking process" — which Agent worked and what decisions it made. Every step is <b>explainable and traceable</b>.</p>
<h3>🔒 Permission Boundaries</h3>
<div class="hp-card">
  AI <b>always knows your identity</b>. If a regular employee asks AI to "batch approve", AI will <b>politely refuse</b> and explain that an approver should handle it. This ensures security and compliance.
</div>
<h3>💡 AI Core Panel</h3>
<p>The sci-fi panel at the bottom-left is a <b>true real-time observability dashboard</b>: 13 LEDs map to 13 Agents. When an Agent is actually invoked, its light really lights up, showing real latency and throughput.</p>`,
    modules: `
<h2>📦 Module Overview</h2>
<p>The system covers six domains — claims, travel, tax, leave, payroll, accounting — across 19+ business modules.</p>
<h3>💳 Claims & Travel</h3>
<ul>
  <li><b>Claim Types / Groups</b>: define claimable categories and grouping</li>
  <li><b>Claim Entitlement</b>: annual quotas by job level</li>
  <li><b>Claim Application</b>: photo OCR / conversational submission</li>
  <li><b>Business Travel Application / Claim</b>: full travel flow</li>
  <li><b>FX Rate</b>: multi-currency auto-conversion</li>
</ul>
<h3>🧾 Tax Compliance</h3>
<ul>
  <li><b>Tax Rate / Tax Parameters</b>: country tax rates (e.g. Singapore GST 9%)</li>
  <li><b>Tax-free Limit (TP1) / Tax Receipt</b>: compliant tax calc</li>
  <li><b>EA Form / EC Form</b>: Malaysia statutory tax forms</li>
</ul>
<h3>🏖️ Leave & Attendance</h3>
<ul>
  <li><b>Leave Entitlement / Type / Group</b>: leave policy config</li>
  <li><b>Shift / Schedule Group / Holiday</b>: attendance scheduling</li>
  <li><b>Attendance Location / Overtime</b>: attendance rules</li>
</ul>
<h3>📒 Payroll & Accounting</h3>
<ul>
  <li><b>Chart of Accounts (COA) / GL Account / Element Group</b>: accounting structure</li>
  <li><b>Bank / Payroll Variables</b>: payment config</li>
</ul>
<div class="hp-card">💡 Tip: Most configurations can be done by <b>simply telling the AI in plain language</b> — no need to manually open modules and fill forms.</div>`,
    faq: `
<h2>❓ Frequently Asked Questions</h2>
<div class="hp-q"><b>Q: I can't find a feature — what do I do?</b><br>A: Just ask the AI Assistant in plain language, e.g. "Where do I set leave entitlement?" AI will guide you.</div>
<div class="hp-q"><b>Q: My claim quota is insufficient?</b><br>A: Contact Finance to adjust. Finance can add/reduce/transfer quota, fully audited.</div>
<div class="hp-q"><b>Q: AI refused my request?</b><br>A: That operation exceeds your current role's permission. Switch to the right role or contact an authorized colleague.</div>
<div class="hp-q"><b>Q: Which countries' compliance rules are supported?</b><br>A: Currently Singapore, Malaysia and more. Each country has independent tax, claim, and accounting rules.</div>
<div class="hp-q"><b>Q: Photo claim recognition is inaccurate?</b><br>A: Ensure the receipt is clear and well-lit. You can manually correct AI-filled fields before submitting.</div>
<div class="hp-q"><b>Q: How do I switch language?</b><br>A: Click the language button top-right — full Chinese/English switching supported.</div>
<div class="hp-card">Still have questions? Just ask the AI Assistant — it's online 24/7 🤖</div>`,
  },
};

// ── 帮助抽屉逻辑 ──
let _helpTab = 'intro';

function helpLang() {
  return (window.getLang && getLang() === 'en') ? 'en' : 'zh';
}

function openHelp() {
  const mask = document.getElementById('help-mask');
  const drawer = document.getElementById('help-drawer');
  if (!mask || !drawer) return;
  mask.classList.remove('hidden');
  requestAnimationFrame(() => drawer.classList.remove('translate-x-full'));
  renderHelp();
}

function closeHelp() {
  const mask = document.getElementById('help-mask');
  const drawer = document.getElementById('help-drawer');
  if (!mask || !drawer) return;
  drawer.classList.add('translate-x-full');
  setTimeout(() => mask.classList.add('hidden'), 300);
}

function renderHelp() {
  const doc = HELP_DOC[helpLang()];
  if (!doc) return;
  // 渲染选项卡
  const tabsEl = document.getElementById('help-tabs');
  if (tabsEl) {
    tabsEl.innerHTML = doc.tabs.map(t =>
      `<button class="hp-tab ${t.id === _helpTab ? 'active' : ''}" data-htab="${t.id}">
        <i class="fas ${t.icon}"></i><span>${t.label}</span>
      </button>`).join('');
    tabsEl.querySelectorAll('[data-htab]').forEach(b => {
      b.onclick = () => { _helpTab = b.dataset.htab; renderHelp(); };
    });
  }
  // 渲染内容
  const body = document.getElementById('help-body');
  if (body) {
    body.innerHTML = doc[_helpTab] || '';
    body.scrollTop = 0;
  }
}

function initHelp() {
  const btn = document.getElementById('help-btn');
  const close = document.getElementById('help-close');
  const mask = document.getElementById('help-mask');
  if (btn) btn.onclick = openHelp;
  if (close) close.onclick = closeHelp;
  if (mask) mask.onclick = closeHelp;
  // ESC 关闭
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeHelp();
  });
  // 语言切换时若抽屉打开则重渲染（以遮罩是否可见判断，更可靠）
  if (window.onLangChange) {
    onLangChange(() => {
      const m = document.getElementById('help-mask');
      if (m && !m.classList.contains('hidden')) renderHelp();
    });
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initHelp);
} else {
  initHelp();
}

window.openHelp = openHelp;
window.closeHelp = closeHelp;
