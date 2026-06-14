# Paydaes ClaimGPT · 集团级 AI Native 报销智能平台 V3.0

> "不再是一个让你填表的系统,而是一群替你思考的智能体。"

## 项目概述
- **名称**:Paydaes ClaimGPT —— 集团级 AI Native 报销智能平台
- **目标**:用 AI Agent 架构重构传统报销 SaaS,把 18 个填表模块进化为 5 个会对话的智能体,并以**企业级集团控制台**承载多租户、多公司、多角色、全球合规
- **核心理念**:左侧专业 SaaS 控制台(看得见、管得住),右侧 AI 智能体抽屉(用得爽、随时唤起)
- **技术底座**:LangGraph 编排引擎(Orchestrator-Worker 双层架构)

## ✅ 已完成功能

### 💰 薪资精度引擎 · FRS 流程2(最新 · 第二波)
对照《规范》流程2「薪资计算步骤 A~H」全面提精度:
- **加班分级费率** (`payroll_data.compute_ot`):平日 **1.5 倍** / 休息日 **2.0 倍** / 公假 **3.0 倍**;基本时薪 = 月基本工资 / 26 / 8。员工可填分级时数 `{normal, rest, holiday}`,旧 `ot` 数字字段自动向后兼容。
- **入/离职月按比例工资** (`prorate_basic`):基本工资 = 月薪 / 当月总天数 × 实际在职天数(演示员工 MY004 在职 18/30 天,基本工资按比例折算 2280)。
- **企业总成本 + HRDF** (FRS 步骤H):**HRDF 人力资源发展征费 1%** 计提;雇主缴纳 = EPF雇主 + SOCSO雇主 + EIS雇主 + HRDF;**企业总成本 = 总收入 + 雇主缴纳**(老板视角真实人力成本)。
- **新增 API**:`GET /api/payroll/run`(月度薪资跑批预览,逐人加班分级 / 按比例 / 企业总成本 + 全员合计)。

### 🇲🇾 政府法定文件中心 · FRS 报表规范(最新 · 第三波)
新增 5 份国家级法定文件,自动出现在「合规报表中心」可一键下载:
- **CP39**(LHDN PCB 月度汇缴表):仅含有 PCB 的员工、月度报酬 / EPF / 当月PCB / 年度累计、缴税人数与合计、证明签章区。
- **SOCSO Form 8A**(PERKESO 社保月报):SIP 工伤 + SPK 残疾、员工/雇主部分、员工总数 / 员工总额 / 雇主总额 / 总计、付款方式区。
- **银行文件 IBG/GIRO**(`.txt` 定长):表头(类型1,**80字符**) + 明细(类型2,**100字符**) + 表尾(类型9,**80字符**),含账号散列总计,无符号纯ASCII,直接对接银行批量出粮。
- **薪资凭证分类账**(借贷平衡):按 FRS 第8节要素分组映射 COA(61000工资费用 / 62000~62003雇主费用 / 21000~23002应付),**借方总额 = 贷方总额**(会计平衡原则,自动校验 + 浮点尾差兜底)。
- **LHDN 审计文件**(`.txt`):税档号 / 姓名 / IC / Gross / EPF / PCB 明细 + 合计,供税务审计存档。
- **勾稽验证**:企业总成本 = 凭证借方 = 凭证贷方(实测 38857.75 三方完全勾稽)。

### 🔄 业务流程引擎 · 对齐 FRS 规范(第一波)
对照《Paydaes 业务流程与财务报表格式规范》落地三大核心流程:
- **审批流引擎** (`app/core/workflow.py`):模块无关设计(报销/请假/加班共用),**多级条件路由**(报销 >RM2000 进财务、>RM10000 进 CFO;请假 >3天/>10天 升级)、**委托代理**、**状态机**(submitted→in_review→approved/rejected/returned,退回保留已通过步骤)。
- **报销 7 条验证规则** (`calc.validate_claim`):单次限额 / 年度限额防护 / **重复票据 PM-9** / **票据日期 PM-10** / 过期报销 / 未来日期 / 必填附件(警告级)。阻止级错误直接拦截入库。
- **报销对接薪资** (文档流程3 第5步):已批准+未过账单据 → **批次过账**(生成 BATCH 批次号)→ 绑定发薪日历 → 纳入薪资。一旦过账不可撤销。
- **AI 辅助预判**:提交即给出审批层级解读 + 通过率预测 + 一句话风险摘要(规则推理,零延迟,可接 LLM 增强)。
- **新增 API**:`POST /api/claims/{id}/advance`(多级审批推进)、`GET /api/claims/{id}/chain`(审批链查询)、`GET /api/payroll/postable`(待对接)、`POST /api/payroll/post`(批次过账)、`GET /api/payroll/batches`(批次汇总)。
- **数据库迁移**:claims 表新增 receipt_no / approval_chain / cur_level / batch_code / posted / pay_calendar / posted_at(老库自动 ALTER 兼容)。

### 📱 移动端用户模式 · 切换即变手机 App
- **角色驱动**:切到 **普通员工(employee)** 角色即进入移动端模式(`MOBILE_ROLES=['employee']`),`body.mode-mobile` 一键触发。
- **手机外壳**:桌面预览时居中 430px 圆角阴影"手机外框"+ 深色衬底;真机(≤480px)自动全屏。隐藏左侧导航树,topbar 收成青色状态栏。
- **底部 Tab Bar**:首页 / 报销 / 我的 + 凸起的 **AI 助手**圆形主按钮,替代桌面导航。
- **「我的」页**:渐变 hero(头像+角色+公司)+ 卡片式列表(我的额度 / 我的报销 / 家属信息 / 帮助 / 切换身份),大点击区、移动手势友好。
- **管理角色无感**:经理/HR/财务/系统管理员等仍是桌面工作台,切换瞬时无刷新。

### 🪶 前端轻量化重构(最新)
- **统一 `api(url, body, method)` 辅助**:自动 GET/POST 判定 + JSON 头 + 解析,替换 14 处冗长 `fetch().then()` 模板(Content-Type 模板 14→1)。
- **统一 `dl(url, name)` 下载辅助**:替换 3 处重复的 `createElement('a')` 下载块。
- **结果**:app.js 冗余收敛、可维护性提升,语法校验通过、桌面+移动端零报错。

### 🇲🇾 合规报表中心 · 马来西亚法定表格(最新)
- **薪资三件套一键导出**(报表模块内,需 hr_admin/payroll/finance/sys_admin 权限):
  - **工资单 Payslip** —— 含 EPF(11%)/SOCSO/EIS/PCB/Zakat 法定扣除明细,逐员工独立 Sheet
  - **EPF Borang A (KWSP 6)** —— 月度公积金缴款表,雇员/雇主缴款 + 合计 + 申报抬头
  - **EA Form (C.P.8A)** —— 年度个人薪酬扣税表,完整 Part A~F(雇员资料/总薪酬/BIK&VOLA/退休金/扣除/免税津贴)
    - **官方 PDF 版式(HASiL C.P.8A)** —— 还原 LHDN 政府版双语(Bahasa+English)表单,蓝底分节 + 表号框 + 签署栏,每员工一页 → 可直接交付 LHDN/员工
- **精确 PCB(MTD)计算引擎** `app/core/pcb_engine.py`:
  - 采用 LHDN 官方电脑化计算公式 `MTD = [(P−M)×R + B − (Z+X)] / (n+1)`
  - 2024 税阶 M/R/B 全表 + 法定宽免(个人 9000 / EPF 4000 / 配偶 4000 / 普通子女 2000 / 高教子女 8000)+ TP1 其他宽免 + Zakat 抵扣 + YTD 已缴 PCB
- **员工薪资名单 Excel 导入** `app/core/payroll_import.py`:
  - 下载 18 列标准模板(说明页 + 数据页 + 示例行 + 必填高亮 + 冻结表头)
  - 上传解析 + 逐行校验(必填/IC 格式/婚姻枚举/数值范围/编号去重)
  - 通过校验的行用精确 PCB 引擎实时试算 gross/EPF/PCB/Zakat/net 预览
- **法定费率**:依 2024 马来西亚现行标准(EPF/SOCSO/EIS/PCB),数据源 `app/data/payroll_data.py`
- **API**:
  - `POST /api/statutory/export` (form_id: payslip/epf_borang_a/ea_form;`fmt: xlsx|pdf`,ea_form 支持官方 PDF)
  - `GET /api/statutory/forms`
  - `GET /api/payroll/import/template` (下载导入模板)
  - `POST /api/payroll/import/parse` (上传名单解析校验预览)
- **真生成 .xlsx / .pdf**:openpyxl 专业排版 + reportlab HASiL 官方版式

### 〇、帮助文档中心(最新)
- **❓问号入口**:主页顶栏问号按钮一键唤起,右侧滑出抽屉(支持 ESC / 点遮罩关闭)
- **中英双语**:跟随全局语言开关实时切换并重渲染
- **6 大板块**:① 系统介绍 ② 快速上手 ③ 角色流程 ④ AI 助手 ⑤ 功能模块 ⑥ 常见问题
- **配套报告**:`SYSTEM_REPORT.md` —— 全系统走查与功能验收汇报报告(45 API/19 模块/6 角色/13 Agent 全绿)

### 一、企业级集团控制台(本次升级)
- **企业级三栏布局**:顶部全局栏 + 左侧导航树 + 中央工作区 + 右侧 AI 抽屉
- **多集团 / 多公司管理**:2 集团(Paydaes / Horizon)、7 家公司,顶栏一键切换,数据随之本地化
- **多角色权限模型**:6 种角色(员工 / 审批人 / HR管理员 / 薪资 / 财务 / 系统管理员),菜单按角色动态显隐
- **多语言 / 多币种**:6 种语言(中/英/马来/泰/越/印尼),公司切换自动适配本地币种
- **🌐 全球合规中心**:调用东南亚 7 国(🇸🇬🇲🇾🇹🇭🇻🇳🇮🇩🇭🇰🇨🇳)税收 / 报销 / 做账体系
- **工作台 Dashboard**:4 张 KPI 卡片 + 报销趋势分析图表 + 待办事项(可一键"交给 AI")
- **18 模块完整工作区**:7 种布局(数据表 / 审批 / 流程 / 报表 / 自助申请 / 余额 / 家庭信息)
- **📱 移动端全适配**:折叠导航、响应式网格、全屏 AI 抽屉

### 二、AI 智能体引擎(阶段一 MVP 保留并收进右侧抽屉)
- **5 主 Agent + 8 子 Agent** 双层编排,基于 LangGraph StateGraph 实现
- **18 个业务模块全部跑通**(模块路由命中率 18/18 = 100%)
- **对话式流畅交互**:5 智能体切换、SSE 流式打字机、思考过程可视化、卡片混合界面
- **人机协同(Human-in-the-loop)**:高风险单据触发 L2 协同,人类最终审批
- **Checkpoint 持久化**:基于 MemorySaver,支持会话记忆与长事务断点续跑

### 三、真实业务功能(告别演示,全面落地)
- **SQLite 持久化**(`app/data/db.py`,零新增依赖):员工 / 报销类型 / 报销单 / 家属 / 审计日志,WAL 模式 + 线程安全
- **真实计算引擎**(`app/data/calc.py`):
  - **跨币种汇率**(以 CNY 为锚的交叉汇率换算)
  - **价内税反算**(`税额 = 金额 × r/(1+r)`,东南亚 7 国真实税率:SG GST 9% / MY SST 6% / TH VAT 7% / VN VAT 10% / ID PPN 11% / HK 0% / CN 6%·13%)
  - **限额校验** + **多因子风险评分**(超限 45 / 大额 22 / 整百 10 / 缺票 18)
- **AI 对话真入库**:对话提交 → 真实落库生成单据编号 → 余额联动扣减
- **批量审批真改状态** + 审计留痕
- **全面中英文 i18n**:`t(key)` 点路径查找,`data-i18n` DOM 扫描,localStorage 记忆语言

### 四、AI 配置后台(统一管理 API · 模型 · Agent 分发)
- **基础配置**:接入 TokenHot.cn / DeepSeek / Claude(Anthropic) / OpenAI,Key **提交 → 验证 → 激活** 三段式
  - 双协议网关(`app/core/llm_gateway.py`):`openai_compatible`(Bearer)+ `anthropic`(x-api-key)
  - **Key 加密存储**:XOR + sha256 + base64,**绝不外泄前端**(前端只见 `key_tail` 后 4 位、不进 git)
- **模型管理**:一键拉取平台支持的全部模型接口,逐模型认定(启用 / 停用)+ 能力自动识别
- **分发应用**:8 个可分发 Agent(3 核心能力节点 + 5 主 Agent),为每个 Agent 指派"平台 + 模型"
  - **分发真正生效**:`intent_agent` / `policy_agent` / `conversation_agent` 接入网关
  - **优雅降级**:**有绑定走 LLM,无绑定 / 调用失败自动回退内置规则引擎**(零回归,系统永不挂)

### 五、OCR Vision 识票 + 前端真功能闭环
- **多模态识票**(`llm_gateway.vision_ocr`):为 `_ocr` 节点分发视觉模型(如 GPT-4o / Claude Sonnet)后,**上传发票照片即真识别**
  - 双协议传图:openai_compatible(`image_url` data URI)/ anthropic(`image` base64 source)
  - 输出结构化字段(商户/类别/金额/币种/日期/税号)自动回填表单
  - **三级降级**:有图+有 Vision → 真识别(`vision`);无 Vision → NL 规则解析(`nl`);兜底示例(`sample`)
- **前端真功能闭环**(自助报销页 `my_claim`):
  - **实时报销记录**:读 `/api/claims` 真库,彩色风险徽章 + 状态 + 统计,一键刷新
  - **真表单提交**:类型下拉(`/api/claim_types`)+ 金额/商户/备注 → `POST /api/claims` → 真入库 + 实时计算(风险分/可抵扣税)+ 列表自动刷新
  - **发票上传 OCR**:拖拽上传 → `POST /api/ocr` → AI 识别回填(并提示当前是真识别还是兜底)

### 六、全模块真操作闭环(本次升级 · 告别演示按钮)
对**全部前端工作台模块**做了功能审计与实操补齐,实现"打开即可用、内部可操作":
- **Playwright 全量扫描**:20 个模块逐个打开,**零 JS 错误**,均正常渲染。
- **报销类型(claim_type)真 CRUD**(用户点名场景):
  - 读真实数据库 `claim_types` 表渲染(不再写死)
  - **新增类型**:点「新增类型」→ 真表单模态框(编码/名称/英文名/分组/限额/需发票)→ `POST /api/claim_types` → 真写库 + 列表实时刷新
  - **删除类型**:每行删除按钮 → `DELETE /api/claim_types/{code}`;**被报销单引用则拒绝删除**(数据完整性保护)
  - 编码同公司内唯一,重复报错
- **通用模块记录(module_records)**:报销组 / 报销权益 / 汇率 / 差旅申请 / 差旅报销 等表格模块**全部可真新增**
  - 统一模态框按 `crud.fields` 动态生成表单 → `POST /api/module_records`(JSON payload 持久化)→ 新增行置顶显示(带删除句柄)
  - 任意自定义行可 `DELETE /api/module_records/{id}` 删除
- **审批端真审批**(mgr_claim / mgr_travel_req / mgr_travel_claim):
  - 读真库 `status=pending` 待审单(不再读 mock),风险分级汇总(低/中/高)
  - 每行「通过 / 驳回」→ `POST /api/claims/{id}/decide` → **真改状态 + 审计留痕**
  - 「一键批量通过低风险」→ `POST /api/claims/batch_decide`
- **家庭信息(family)真档案**:读真库 `family` 表;内联「新增家属」→ `POST /api/family` → 真写库 + 列表刷新
- **moduleAction 重构**:废弃 `alert("演示功能")`,改为智能分流(AI 动作→对话;新增动作→真表单模态框;其余→轻提示 toast)
- 全程 **zh/en 双语**(新增 `crud.*` / `fam.*` i18n 词条),LLM 平台/绑定配置 `force_seed` 时**完整保留**(8/8 Agent 不受影响)

### 七、AI 权限贯穿层(本次升级 · 让 AI 成为身份判定者)
把"权限"从静态菜单过滤,升级为**贯穿全系统的【身份判定 + 操作裁决】**——这是猫哥点名的核心架构:
- **操作级能力矩阵**(`app/core/permissions.py`):细到 16 个具体写操作(`claim.approve` / `balance.adjust` / `claim_type.create` / `report.export` …),`ROLE_ACTIONS` 为 6 角色各配一组能力,**`sys_admin = {"*"}` 最高权限可处理一切(含审批裁决)**。
- **三层防护,处处兜底**:
  1. **后端写操作闸门**:每个 mutating 端点先 `permissions.can(role, action)`,越权返回 `deny_payload`(含"谁可以做"引导)。
  2. **Agent handler 硬拦截**:无审批权角色让 AI 代办审批,**写库前即拦截、绝不落库**(`approval_copilot` batch 分支)。
  3. **AI 身份注入(贯穿核心)**:`role` 从前端 → API → `run_turn` → `ClaimState` → `conversation_agent`,把 `permissions.describe(role)` 身份画像注入 LLM 系统提示。**AI 全程"知道登录者是谁、能做什么",在对话中主动拒绝越权请求**(如普通员工让 AI 帮他审批 → AI 礼貌拒绝并告知应由审批人/HR/系统管理员处理)。
- **前端权限自适应**:`/api/whoami` 驱动越权按钮隐藏(余额调整面板、报表导出按钮按角色显隐),后端 403 时 toast 兜底提示。

### 八、三项功能接真(本次升级)
- **余额调整接真 API + 必填原因留痕**:`balance_adj` 工作台真表单(员工选择 / 增·减·转移 / 金额 / **必填原因**)→ `POST /api/balance/adjust` → 真改员工 `annual_quota` + 写 `balance_adjust` 流水表(全程审计留痕);`GET /api/balance/history` 真历史。**仅 finance / sys_admin 可调**。
- **报表导出 PPT / Excel 接真生成**(`app/core/reporting.py`):`openpyxl` 生成真 `.xlsx`(报销明细 + 状态汇总双 sheet),`python-pptx` 生成真 `.pptx`(封面 + KPI + 明细表三页,Paydaes 青色主题)→ `POST /api/report/export` → `GET /api/report/download/{file}` 真下载。读真库数据。**hr_admin / payroll / finance / sys_admin 可导**。
- **报销类型「编辑」模态框**:类型行新增「编辑」按钮 → 预填模态框(编码锁定) → `PUT /api/claim_types/{code}` 真更新。

## 🔌 配置后台 API 一览
| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/admin/presets` | GET | 预置平台 + 可分发 Agent 清单 |
| `/api/admin/providers` | GET/POST | 平台列表 / 新增平台(Key 加密) |
| `/api/admin/providers/{pid}/verify` | POST | 验证 Key(并自动拉模型) |
| `/api/admin/providers/{pid}/activate` | POST | 激活 / 停用平台 |
| `/api/admin/providers/{pid}/models/pull` | POST | 拉取平台全部模型 |
| `/api/admin/models/toggle` | POST | 模型启用 / 停用 |
| `/api/admin/bindings` | GET/POST | Agent 分发绑定 |
| `/api/ocr` | POST | 发票识别(Vision / 规则兜底) |
| `/api/claims` | GET/POST | 报销单列表 / 真提交 |
| `/api/claims/{id}/decide` | POST | 审批通过/驳回(真改状态+留痕) |
| `/api/claims/batch_decide` | POST | 一键批量通过(按风险等级) |
| `/api/claim_types` | GET/POST | 报销类型 列表 / **新增** |
| `/api/claim_types/{code}` | PUT/DELETE | 报销类型 更新 / **删除(引用保护)** |
| `/api/module_records/{id}` | GET | 某模块自定义记录列表 |
| `/api/module_records` | POST | **通用模块真新增**(组/权益/汇率/差旅) |
| `/api/module_records/{id}` | DELETE | 删除自定义记录 |
| `/api/family` | POST | 新增家属(真写库) |

## 🌍 全球合规体系(东南亚 7 国)
| 国家 | 税种 | 税率 | 会计准则 |
|------|------|------|---------|
| 🇸🇬 新加坡 | GST 商品服务税 | 9% | SFRS |
| 🇲🇾 马来西亚 | SST 销售服务税 | 6% | MFRS |
| 🇹🇭 泰国 | VAT 增值税 | 7% | TFRS |
| 🇻🇳 越南 | VAT 增值税 | 10% | VAS |
| 🇮🇩 印尼 | PPN 增值税 | 11% | PSAK |
| 🇭🇰 香港 | 无销售税/增值税 | 0% | HKFRS |
| 🇨🇳 中国 | 增值税 VAT | 6%/13% | CAS |

## 🤖 5 主 Agent × 18 模块映射
| 主 Agent | 承接模块 |
|---------|---------|
| 🙋 ClaimMate 报销伙伴 | 报销申请-自助、商务差旅申请-自助、商务差旅报销-自助、家庭信息 |
| ✅ ApprovalCopilot 审批副驾 | 报销申请-管理、差旅申请-管理、差旅报销-管理 |
| 🧠 HRStrategist HR战略顾问 | 报销类型、报销组、报销权益、生成权益流程、余额调整 |
| ⚙️ PayrollNavigator 薪资领航员 | 报销接口流程、审核接口数据、汇率 |
| 📊 InsightOracle 洞察先知 | 福利使用报表、差旅申请报表、报销申请报表 |

## 🌐 功能入口 URI
- `GET  /` —— 企业级控制台主页面(三栏布局)
- `GET  /api/bootstrap` —— 集团/角色/语言/导航树/Agent 初始化数据
- `GET  /api/dashboard?company=` —— 工作台 KPI + 图表 + 待办(按公司本地化)
- `GET  /api/compliance?country=` —— 单国完整合规体系(税收/报销规则/做账)
- `GET  /api/module/{module_id}?company=` —— 18 模块业务数据(7 种布局)
- `GET  /api/agents` —— 5 主 Agent 元信息
- `GET  /api/modules` —— 18 模块清单
- `POST /api/chat` —— 一次性对话(body: `{message, thread_id}`)
- `GET  /api/chat/stream?message=&thread_id=` —— SSE 流式对话(思考链 + 打字机 + 卡片)
- `GET  /api/telemetry` —— **AI 中枢实时遥测**:13 Agent(5主+8子)真实命中状态(`recent`/`count`/`since_ms`)+ 整体吞吐(`tps`/`avg_latency_ms`)。供侧边栏「活体仪表盘」每 1.5s 轮询,**某 Agent 被 `run_turn` 实际命中 → 对应 LED 真的爆闪**

## 📡 真·实时可观测面板(Telemetry 埋点)
侧边栏底部的「AI 中枢状态面板」已从视觉装饰升级为**真实可观测仪表盘**:
- **零侵入埋点**:`app/core/telemetry.py` 线程安全内存计数器,`hit()`/`turn()`/`snapshot()`,静默失败(零回归)
- **天然中枢点**:子 Agent 在 `handlers._think()` 处统一埋点(一行捕获全部 8 子 Agent);主 Agent + IntentAgent + ConversationAgent 在 `orchestrator` 编排节点埋点
- **13 Agent 归一化**:5 主 + 8 子,内部别名(`ValidationAgent→RiskAgent` 等)自动映射到前端 LED canonical id
- **效果**:不同业务请求点亮不同灯路 —— 报销链路亮 `ClaimMate+Risk+Extract+Workflow+Conv`,薪资跑批亮 `PayrollNavigator+Workflow+Conv`,真实反映 Agent 调用路径。既是科技感卖点,又是运维价值。

## 🏗️ 技术架构(轻量化重构后)
```
前端: HTML + TailwindCSS + Chart.js (纯CDN,零构建)
  · 企业级三栏: 顶部全局栏 + 左侧导航树 + 工作区 + 右侧 AI 抽屉
  · 478 行单页 SPA, 响应式移动端适配
  ↓ SSE 流式
AI编排: Python + FastAPI + LangGraph StateGraph
  · Orchestrator 意图路由 → 5主Agent → 8子Agent → 人机协同
  · MemorySaver Checkpoint 持久化
数据: Mock内存(阶段二替换为 Supabase Postgres+pgvector)
  · enterprise.py  : 2集团/7公司/6角色/7国合规/6语言
  · navigation.py  : 企业导航树 + Dashboard 数据
  · module_views.py: 18 模块业务视图(7 种布局)
  · mock_db.py     : 报销/权益/汇率/家属等业务 Mock
```

## 数据架构
- **企业数据模型**:GROUPS(集团-公司)/ ROLES(角色-菜单权限)/ COUNTRIES(国别合规)/ LANGUAGES
- **AI 状态模型**:`ClaimState`(消息/意图/抽取/校验/风险/政策/审批/卡片/思考链)
- **当前存储**:内存 Mock(报销类型、员工权益、待审单据、汇率、家属、合规体系等)
- **阶段二**:Supabase(Postgres + pgvector)替换 Mock,实现三层记忆

## 🚀 本地运行
```bash
cd /home/user/claimgpt
pm2 start ecosystem.config.cjs   # 启动(端口 3000)
curl http://localhost:3000/api/bootstrap  # 健康检查
pm2 logs claimgpt --nostream     # 查看日志
```

## 📋 用户指南
1. **顶部全局栏**:切换公司(数据/币种/合规自动本地化)、切换角色(菜单动态变化)、切换语言、进入全球合规中心
2. **左侧导航树**:工作台 / 设置 / 我的 / 报销数据 / 报销流程 / 审核 / 报表 / 核心HR / 全球合规中心
3. **工作台**:看 KPI、趋势图、待办;点"交给 AI"直接唤起对应智能体
4. **18 模块**:点击导航进入,不同模块呈现不同专业布局(表格/审批/流程/报表…)
5. **右侧 AI 抽屉**:点"AI 助手"唤起 5 个智能体团队,用大白话对话即可完成报销全流程
6. **移动端**:汉堡菜单展开导航,AI 抽屉全屏,所有网格自适应

## 🔜 未实现 / 下一步
- 接入真实 LLM(Claude/GPT/DeepSeek 多模型路由)替换规则引擎
- 接入 Supabase 实现三层记忆与状态持久化(阶段二)
- 接入真实 OCR、汇率 API、薪资接口工具(MCP)
- `interrupt()` 真正暂停-恢复的审批流(当前为标志位演示)
- 后台自定义排布(拖拽式 Dashboard / 菜单编排)
- 生产部署(FastAPI 上云 + 前端 Cloudflare Pages)

## 部署
- **平台**:沙盒(阶段一 + 企业级升级)
- **状态**:✅ 运行中
- **技术栈**:Python 3.13 + FastAPI + LangGraph 1.2.4 + TailwindCSS + Chart.js
- **验证**:后端 18/18 模块 + 2集团 + 6角色 + 7国合规全绿;前端桌面+移动端零 JS 错误
- **最后更新**:2026-06-14(三波迭代对齐 FRS:Wave1 业务流程引擎 + Wave2 薪资精度引擎(加班分级/按比例/HRDF/企业总成本) + Wave3 政府法定文件(CP39/SOCSO 8A/银行IBG/凭证分类账/LHDN审计))

## 🆕 Paydaes HR-Payroll 套件(Pro 方案 · 全量铺开)

基于真实 Paydaes 生产系统(uat-fe.pydco.com)52 张截图,提炼「7 块积木」模板引擎,数据驱动复刻 **6 大业务域 / 20 个功能页**:

### 设计语言:Paydaes 青色(#20c997 / #2BD9C2)
全栈换肤完成(前端 CSS/HTML/JS + 后端数据均已切青)。

### 7 块积木模板(layout 类型)
| 积木 | layout | 说明 |
|------|--------|------|
| ① 列表页 | `p_list` | 搜索筛选 + Download/+Add + 绿点状态 + 分页 |
| ② 详情页 | `p_detail` | 只读主键 + 表单网格 + Back/Save |
| ③ Tab 详情 | `p_tabset` | 内部横向子 Tab + 表单 |
| ④ Inline 行编辑 | `p_inline` | 行尾 ⊕/垃圾桶 + 头字段 + 分页 |
| ⑤ 穿梭框 | `p_shuttle` | 双栏候选/已选 + 箭头 |
| ⑥ Formula 公式 | `p_formula` | 代码编辑器 + 变量芯片 + AI 自然语言生成 |
| ⑦ 地图定位 | `p_map` | 图钉 + 半径圈 + GPS |

### 6 大域功能页(API: GET /api/module/{id})
- **税务合规** tax: tax_rate / tax_param / tax_tp1 / tax_receipt / ea_setting / ec_setting
- **假期管理** leave: leave_entitlement(Formula)/ leave_type / leave_group
- **考勤管理** ta: shift / schedule_group / holiday / attendance_loc(地图)/ overtime
- **财务做账** accounting: coa / element_group / gl_account
- **主数据** master: bank / payroll_var

### 🤖 AI 注入预埋点(下一阶段接真 LLM)
- Leave Entitlement → 「自然语言生成公式」按钮
- Tax Rate → 「AI 自动算税」
- Schedule Group → 「AI 智能排班」
- Overtime → 「AI 异常检测」
- EA Setting → 「AI 自动归集」
- COA → 「AI 科目映射」
