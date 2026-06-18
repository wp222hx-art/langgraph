# Paydaes ClaimGPT · 集团级 AI Native 报销智能平台 V3.0

> "不再是一个让你填表的系统,而是一群替你思考的智能体。"

## 项目概述
- **名称**:Paydaes ClaimGPT —— 集团级 AI Native 报销智能平台
- **目标**:用 AI Agent 架构重构传统报销 SaaS,把 18 个填表模块进化为 5 个会对话的智能体,并以**企业级集团控制台**承载多租户、多公司、多角色、全球合规
- **核心理念**:左侧专业 SaaS 控制台(看得见、管得住),右侧 AI 智能体抽屉(用得爽、随时唤起)
- **技术底座**:LangGraph 编排引擎(Orchestrator-Worker 双层架构)

## ✅ 已完成功能

### 🔗 数据流一致性体检与修复 · 全链路同源(最新 · 第十五波)
做完多国驾驶舱后做了一次**全链路数据流体检**(用户要求:"整体数据流是否都有效关联、一致,不是割裂的,也不是死的"),发现并修复 3 处割裂/死数据 + 1 个隐藏 bug:
- **🔴 修复 A(最大割裂)·公式发薪 ⇄ 驾驶舱 统一数据世界**:此前「公式驱动批量发薪」`payroll_batch` 永远用 5 个 MY 员工 + 纯 MY 法定引擎,与驾驶舱的「本地化花名册 + 国别法定引擎」是**两套割裂数据世界**(切到中国:驾驶舱显示「陈静 + 五险一金 + ¥」,发薪却还是「Ahmad + EPF + RM」)。现已让 `run_batch(company)` 改走 `intl_roster.localized_roster(国别)`,法定计算按国分流(**MY → `compute_monthly` 保留 LHDN MTD 精确 PCB/Zakat/EA Form 链路;其他国 → `statutory_intl`**)。实测**发薪算出的单人 total_cost = 驾驶舱样本聚合 = 100.000% 同源**(7 国全部 0.000% 偏差)。
- **🔴 修复隐藏 bug · `/api/payroll/run` 重复定义**:server.py 中该路由被定义了两次,FastAPI 以后定义者(旧版纯 MY、不带 `formulas` key)覆盖前者,导致前端「公式驱动发薪」实际拿到旧格式 → `r.formulas.leave_active` 取不到。已删除旧版,统一由公式驱动版(`batch_summary`)提供。
- **🔴 修复 · 工资单端点本地化**:`/api/payroll/payslip/{emp_no}` 也改用本地化花名册定位员工(CN005 → 陈静 · CNY · 五险一金;MY001 → Ahmad 仍走精确 PCB 引擎)。
- **🟡 修复 B · 工作台待办/趋势图从"死常量"变"活数据"**:此前 `TODOS` / `DASHBOARD_CHART` 是全公司一模一样的硬编码。现改为 `dashboard_todos(company)` / `dashboard_chart(company)`,待办数量(高风险笔数/晋升员工/超标差旅)与图表 6 月曲线**锚定该公司真实 KPI 规模 + 币种 + 税率**确定性派生。实测 CN 10 笔高风险 + 图表[118…] vs HK 1 笔 + 图表[23…],各公司全不同。
- **🟢 重构 C · 消除逻辑重复**:抽取 `statutory_intl.employer_buckets(er)` 共享 helper,让 analytics(驾驶舱)与 payroll_batch(发薪)复用同一套「雇主缴纳归并到通用桶」逻辑,杜绝"改一个忘改另一个"。
- Playwright 跨模块 E2E **13 项断言全过 · 0 JS 错误**:切中国/香港,驾驶舱 + 公式发薪 + 工作台三处展示的币种/人名/法定体系/待办/图表全部同源且互不相同。

### 🛡️ 多国法定引擎 + 员工本地化 · 全球合规护城河(第十四波)
把驾驶舱从"MY 引擎 + 汇率换算"升级为**各国真实法定结构驱动**,既上护城河(里子)又一眼可信(面子):
- **新建多国法定引擎 `app/core/statutory_intl.py`**:为 7 国各自实现真实法定扣除/雇主缴纳 ——
  🇲🇾 EPF/SOCSO/EIS/PCB · 🇸🇬 **CPF**(EE20%/ER17%,普通工资上限 6800)+ SDL · 🇨🇳 **五险一金**(养老/医疗/失业/工伤/生育 + 住房公积金)+ 个税 · 🇹🇭 **SSF**(5%,月上限 750)+ PIT · 🇭🇰 **MPF**(5%,月上限 1500)+ 薪俸税 · 🇻🇳 SI/HI/UI(10.5%)+ PIT · 🇮🇩 BPJS + PPh21。每国含累进个税估算,返回 EE/ER 明细 + 企业总成本。
- **新建本地化花名册 `app/data/intl_roster.py`**:7 国各 5 名员工,**名字/职位/银行/证件按国本地化**(中文名「王建国/陈静」· 泰文名「สมชาย วงศ์สว่าง」· 越南名「Nguyễn Văn Hùng」· 印尼名「Budi Santoso」· 港式「Chan Tai Man」),HR 维度(性别/司龄/职级/部门/加班)跨国保持可比结构;基本工资以**各国本币真实薪资量级**给出。
- **驾驶舱大脑改造 `analytics.py`**:`_company_snapshot(company)` 改走「本地化花名册 → 国别法定引擎 → 按真实编制规模放大」,使**币种 × 数值 × 法定结构三者全部自洽**。实测 CN ¥18,339,190(560人,五险一金显性高用工成本)· SG S$2,530,647(CPF 有上限,成本克制)· HK HK$3,281,846(MPF 封顶+高薪)· TH ฿11,689,623 · VN ₫6,111,999,559 —— 量级与各国现实一致。
- **本地化 + 国别化全覆盖**:部门名中文化(技术部/财务部)· 异常稽查员工名本地化 · 加班法定上限按国(MY 104h / CN 36h / TH 36h / VN 40h / ID 56h)· KPI/归因术语去 MY 化(雇主养老金/公积金、社保/医保、个税预扣)。
- **前端「法定体系徽章」**:驾驶舱副标题旁展示 `币种 · 法定体系`(如「CNY · 五险一金 + 个税」「SGD · CPF + SDL」「HKD · MPF + 薪俸税」),把全球合规护城河可视化。`/api/cockpit/overview` 新增 `lang` 参数驱动部门名本地化。
- **零侵入**:全程未触碰 MY 真实合规链路(EPF Borang A / EA Form / PCB 精确引擎),国际引擎独立服务驾驶舱。
- Playwright E2E 全绿(切 cn/hk/th/vn/sg → 5 国数值互不相同 + 币种正确 + 法定徽章可见 + 本地化员工名 + 0 JS 错误)。

### 🌍 AI 老板驾驶舱多公司数据 + 币种一致性(第十三波)
让 AI 老板驾驶舱**真正"跟随筛选的公司体系"**——切到哪家公司,就看哪家公司的数据与币种,不再所有公司千篇一律的 MY 数据 + 统一 RM:
- **每家公司不同数值**:驾驶舱大脑 `analytics.py` 新增 `_company_meta()` 反查公司真实编制(SG 320 / MY 256 / TH 198 / VN 174 / ID 412 / HK 88 / CN 560),`_company_snapshot(company)` 按"真实编制规模 × 本币汇率 × 公司确定性扰动"缩放,使每家公司产出**互不相同、且与其规模/币种逻辑自洽**的总成本/薪资/加班/HRDF/PCB/部门分布/环比趋势。部门人头也按真实编制等比放大。
- **币种代名词全程一致**:引入 `_FX_TO_LOCAL`(MYR↔各国汇率)+ `_CURRENCY_PREFIX`(RM / S\$ / HK\$ / ¥ / ฿ / ₫ / Rp)。三大出口 `build_overview / detect_anomalies / explain_cost_change` 均输出 `currency` + `currency_prefix`;**彻底消灭硬编码 "RM"**——KPI 卡、人均成本、AI 归因解读、异常稽查金额、趋势图 Y 轴、部门环图 tooltip 全部跟随公司本币。
- **量级符合各国货币习惯**:实测 CN ¥7,080,737 / HK HK\$1,229,648 / SG S\$826,600 / MY RM2,309,544 / VN ₫7,270,123,221 —— VND/IDR 十亿级、SGD 偏小、CNY 中等,与现实货币量级一致。
- **前端**:`fmtRM` 重构为 `fmtCur(v, prefix)` + `ckPrefix(ov)`,驾驶舱所有金额渲染从后端返回的 `currency_prefix` 取币种,中英双语。
- Playwright E2E 全绿(切换 cn/hk/sg/my/vn → 5 家公司数值互不相同 + 币种前缀正确 + AI 解读币种跟随 + 0 JS 错误)。

### 💸 公式引擎接真实薪资批算 · 公式驱动每张工资单(第十二波)
把公式引擎从"单条规则计算器"升级为**批量发薪管线的真实驱动核心**——让用户在公式编辑器里配的规则,真正决定每个员工工资单上的数字:
- **新建批算管线 `app/core/payroll_batch.py`**:遍历公司员工 → 逐人把 HR 维度(性别/婚姻/司龄/职级/加班时数)映射成公式变量空间 → 读取该公司落库公式 → `formula_engine.evaluate` 求值 → 驱动「应享假期天数」与「加班费」→ 再走成熟的法定扣除引擎(EPF/SOCSO/EIS/PCB/Zakat/HRDF)→ 出工资单。
- **公式真正改变工资单**:实测 —— 配置司龄阶梯公式后,MY001(12年)应享天数 `14→18`、MY002(7年)`→16`、MY003(3年)`→14`;配置加班公式后加班费由 `1050.48→913.46`,**净薪同步联动变化**。无公式时优雅回退到默认天数/分级费率。
- **公式溯源(formula_trace)**:每张工资单都记录"用了哪条公式 / 喂了哪些变量(SERVICE.YEARS=12, ENTITLEMENT.DAYS=14)/ 算出什么值",前端点「溯源」图标弹层查看,实现「公式 → 工资单」的**可解释闭环**。
- **员工花名册扩展**:`PAYROLL_EMPLOYEES` 5 名员工新增 `gender/service_years/grade/base_entitlement` 维度,有区分度,体现公式驱动效果。
- **前端入口**:报销接口流程(payroll_if)等 flow 页新增「公式驱动批量发薪」按钮,一键跑批 → 工资单表格(工号/姓名/职级/基本/加班/应享天数/应发/扣除/实发)+ 公式状态徽章(已驱动/默认)+ 逐人溯源。中英双语。
- **API**:`GET /api/payroll/run?company=&period=&role=`(批算摘要)、`GET /api/payroll/payslip/{emp_no}?company=`(单员工完整工资单+溯源),均需 `payroll.run` 权限。
- Playwright E2E 全绿(默认 5 行工资单;配公式后 12年→18天/公式徽章"已驱动"/溯源弹层结果→18;0 JS 错误)。

### 🔗 Company Code 全域联动 + 公式查询体系(第十一波)
把"写死值"彻底消灭,并把公式编辑器升级为**可查询的帮助系统**:
- **Company Code 随公司联动**:此前所有模块的 `Company Code` 硬编码为 `COM01/COM05`,现在改为读取所选公司的真实公司代码(`PDS-SG / PDS-MY / PDS-TH / PDS-VN / PDS-ID / HZN-HK / HZN-CN`)。班次/排班组/假日表/加班/会计科目表的公司代码、假期权益的国家代码(`SG/MY/...`)、打卡地点与银行的国家全名(`Singapore/Malaysia/...`)全部随公司切换实时变化。
- **企业数据层补全**:`enterprise.py` 7 家公司新增 `code` 字段;`get_paydaes_module()` 与各域模块函数(`_leave/_ta/_acc/_master_modules`)接收 `code`/`country` 参数动态注入。
- **全系统串联体检**:审计 19 个导航叶子节点 → 100% 映射到后端模块且均有合法 layout;遍历 7 公司 × 18 模块,确认公司/国家相关字段全部联动(唯会计科目 Entity 维度按业务正常保留固定)。
- **公式查询助手(Formula Helper)**:原"自然语言生成公式"按钮(只是丢给通用 AI 聊天)重做为内置查询体系浮层 —— **6 个场景化公式模板**(司龄阶梯/已婚女性额外假/Pro Rata 折算/结转封顶/加班费/职级津贴)+ **10 个函数手册**(IF/AND/OR/NOT/ROUND/MIN/MAX/ABS/CEIL/FLOOR,含中英签名+示例)+ **12 个变量字典**;支持中英文关键词检索(如"加班/overtime/司龄"),点击模板/函数示例/变量名直接插入公式编辑器,再配合"运行试算"实时计算。
- **API**:`GET /api/formula/help?q=<关键词>`(返回 templates/functions/variables + 检索命中)。
- **只读字段修复**:`ro` 类型字段改 `disabled`→`readonly` 并补 `data-label`,使 Company Code 等关键标识可被收集/回显/定位。
- 全程中英双语;Playwright E2E 全绿(SG→PDS-SG / CN→HZN-CN;助手 6 模板/搜索命中/插入成功;0 JS 错误)。

### 📱 员工自助门户「我的」· 手机端深度适配(最新 · 第五波)
针对普通员工(employee 角色 = 移动 App 体验)重做个人中心,从"空壳入口列表"升级为**真数据驱动的自助门户**:

- **个人中心**(`renderMeView`,异步拉 `/api/me/summary`):
  - **本月薪资卡**(渐变青→蓝主视觉):实发工资 RM 9,710.31 + 应发/扣除,点击进薪资单详情。
  - **年度报销额度条**:剩余/已用/总额可视化进度。
  - **报销进度四宫格**:审批中 / 已批准 / 已发放 / 已驳回 实时计数(读真库)。
  - **待办提醒条**:`你有 N 笔报销待处理`,一键跳报销页。
  - **快捷入口**:我的薪资单 / 我的报销 / 问 AI 额度 / 家属信息(带人数徽章)/ 帮助 / 切换身份。
- **我的薪资单详情页**(`renderMyPayslip`,拉 `/api/me/payslip`):手机友好的明细页 = 实发大卡(含银行卡尾号)+ 收入项明细(基本/津贴/加班/佣金/奖金)+ 扣除项明细(EPF/SOCSO/EIS/PCB/Zakat)+ 应发/扣除合计,所有数字由 Paydaes 薪资引擎按马来西亚法定标准实时核算。
- **新增 API**(员工权限,仅返回本人数据,不暴露他人):
  - `GET /api/me/summary?role=&company=&emp_no=` — 个人首屏聚合(薪资概览+额度+报销统计+待办+家属数)
  - `GET /api/me/payslip?role=&emp_no=&month=` — 我的薪资单(收入/扣除明细+实发)—— 需 `payslip.self_view`
- **新增权限** `payslip.self_view`(授予 employee/approver/hr_admin/sys_admin,人人可查本人薪资单)。

### 🧾 员工手机端「报销」页打通(最新 · 第六波)
修复员工移动 App 底部「报销」tab 与「我的报销」入口点进去显示 **"my / 模块开发中"空壳**的问题:

- **路由根因**:底部 tab 与各处「我的报销」链接误指向 `my`(导航**分组**节点,非真实模块)→ `renderModule('my')` 命中通用占位符。已将全部 13 处 `mobileGo('my')` + 底部 tab 统一改指真实自助报销模块 **`my_claim`**(layout `self_claim`)。
- **页面内容**:现正确渲染完整自助报销页 = 年度额度卡(RM 21,400/30,000 + 进度条)+ 拍照报销(AI)+ 发票 OCR 上传 + 真提交表单 + 实时报销记录(读真库:亚航/客户宴请/滴滴/全季/携程/海底捞)。
- **货币与公司一致性**:员工(employee)登录默认锁定**马来西亚公司(my)**,额度/报销/薪资单全链路统一 **RM**(`selfClaimView` 手机端币种归一化为 RM);补 `claim.st_posted`(已入账/Posted)i18n,消除状态列未翻译 key。
- **手机端样式优化**:`self_claim` 视图单列堆叠 + 圆角卡片 + 44px 触控输入 + 46px 主按钮 + 报销记录区横向可滑(`overflow-x:auto`)。

### 🧩 数据一致化 + 手机端布局防溢出(最新 · 第七波)
解决两个跨页面顽疾:

- **布局防溢出(治本)**:手机壳是 430px 容器嵌在大屏中,而 Tailwind `lg:grid-cols-3` 看的是**整个浏览器窗口宽度**,平板/横屏(>1024px)会误触发 3 列把卡片挤成竖排文字。修复:
  - `body.mode-mobile #view .grid` **强制单列**(`grid-template-columns:1fr !important`),无视 Tailwind 断点;
  - 解除 grid/flex 子项默认 `min-width:auto`(改 `min-width:0`),否则内部内容会把 panel 撑破列宽(实测 panel 被撑到 691px → 修复后严丝合缝 390/430px);
  - 全元素 `box-sizing:border-box` + `max-width:100%`,固定宽 `w-24/w-36`(币种/日期框)改弹性,双视口(390px 真机 + 1024px 平板)实测**横向零溢出**。
- **数据一致化(`effCompany()`)**:新增有效公司 helper —— 员工(手机端)演示员工 MY001 隶属马来西亚公司,所有数据源**强制锁 `my`**;其余角色回退各自选中公司(`S.company.id`),**零副作用**(sys_admin 仍用 sg)。统一改造的数据入口:报销记录 `/api/claims`、报销类型 `/api/claim_types`、模块数据 `/api/module/*`、家属 `/api/module/family`、提交报销、OCR、**AI 对话流 `/api/chat/stream`**。
- **AI 助手数据与角色体系一致**:AI 对话的 `company` 参数改用 `effCompany()`,后端 orchestrator→reporting 按公司拉真实 claims/stats。实测员工问"报销情况",AI 引用的全是马来西亚真实数据(单号 CMY、货币 MYR、餐饮费限额 200 MYR),与前端报销页同一套规则,不再出现 SGD/CSG 串档。

### 📷 AI 助手·对话式拍照识别(最新 · 第八波)
让 AI 助手具备"拍照上传→视觉识别→自动填单"的对话式能力,真正 AI-Native:

- **输入区相机按钮**:AI 抽屉输入框左侧新增 📷 按钮(`#ai-cam`),`capture="environment"` 调起后置摄像头/相册。随时可在对话里拍票据。
- **对话式识别流程**(`aiOcrUpload`):
  1. 用户气泡显示上传票据的**缩略图**;
  2. AI "视觉识别中"动效;
  3. 识别完成 → 复用 `/api/ocr`(真实 Vision 引擎,约 5s)→ 输出**票据识别结果卡片**(类型/商户/金额/日期);
  4. 卡片底部「✨ 一键填入报销单」按钮 → `aiFillClaim()` 关闭抽屉、跳转 `my_claim` 自助报销页、自动回填表单字段并平滑滚动定位。
- **主动递上传入口**(后端 `orchestrator._wants_upload`):当用户在对话里问"怎么报销/如何提交/能拍照吗/上传发票"等操作意图(中英文关键词识别),`run_turn` 在 SSE 流里追加 `upload_action` 卡片,前端渲染成醒目的"📷 拍照识别·自动填单"按钮卡片 —— 不止文字回答,直接把工具递到用户手上。
- **新增卡片类型** `upload_action`(`renderAICard` 分支)+ i18n(`ai.cam_*` zh/en):cam_btn/cam_uploaded/cam_reading/cam_done/cam_card_title/cam_fill/cam_filled。
- **货币一致**:识别卡片在手机端统一显示 RM,回填时遵循 `effCompany()` 锁定的马来西亚体系。
- **移动导航**:底部 Tab(首页/报销/我的/AI)+ 虚拟路由 `__me`/`__payslip`,"我的"tab 在个人中心与薪资单详情间保持高亮;`go()` 拦截虚拟 nav 避免误入模块加载。

### 🗺️ 系统架构图谱 + 完整说明书(最新 · 第九波)
一份"可视化产品白皮书 + 架构蓝图",**点击左上角集团 Logo / 集团名即可进入**:

- **入口**:`renderTopbar()` 给 `#group-logo` / `#group-name` 绑定 `onclick=go('__arch')`,`go()` 新增 `__arch` 虚拟路由 → `renderArchitecture()`,带 `arch.enter` i18n title 提示。
- **页面内容**(全双语内联,跟随语言切换):
  1. **品牌头图**:深色渐变 + 集团 Logo + 4 项核心统计(5+8 智能体 / 18 模块 / 6 角色 / 8 波次);
  2. **一次请求的旅程**:6 段数据流泳道(用户提问→意图路由→Agent 协作→引擎计算→合规校验→卡片返回);
  3. **五层架构图谱**:体验层 / 编排层 / 智能体层 / 引擎层 / 数据层,层间箭头递进,每层列要点;
  4. **AI 智能体团队**:5 主 Agent 卡片(读取 `S.agents` 真实数据,emoji/配色/职责)+ 8 子 Agent 彩色 chip;
  5. **18 业务模块**:按报销与权益/申请与审批/薪资与接口/报表与数据 4 组归类;
  6. **6 角色权限模型** + **技术栈**(FastAPI·Pydantic / LangGraph / 多供应商网关·视觉 OCR / Vanilla JS·Tailwind·Chart.js);
  7. **合规与精度内核**:EPF/SOCSO/EIS/PCB · CP39/SOCSO 8A/IBG · LHDN 审计 · 加班分级/HRDF;
  8. **迭代历程**:八波进化时间线(当前波次高亮)。
- **样式**:`app.css` 新增 `.arch-*` 全套(头图渐变/层级卡/泳道/智能体网格/时间线),响应式 + `body.mode-mobile` 适配,顶部「返回工作台」按钮。
- **数据真实**:Agent / 角色直接读取 bootstrap 注入的 `S.agents`/`S.roles`,与系统实际配置同源。

### 📖 说明书升级:中英双语并排 · 功能精确详解(最新增强)
将架构页从"概览"升级为"详尽功能手册",中英文**同屏并排对照**(中文实色在上、English 灰斜体在下,不需切换语言即可双语阅读):

- **双语并排引擎**:新增 `biRow(zh,en)` / `biH2(icon,zh,en)` / `biH2cap` 辅助,全页 83+ 处中英对照行。
- **锚点导航**:页面顶部 6 个锚点(请求旅程/五层架构/智能体手册/18模块/角色权限/技术合规),`scroll-margin-top` 平滑定位。
- **智能体功能手册**(5 张详卡,替代原概览):每张卡含 ① 中英名称 + 一句话定位 ② **使用者标签**(员工/审批人/HR/薪资/财务) ③「能做什么」精确能力清单(每个 Agent 4 条,共 20 条) ④ 典型对话 ⑤ 产出物。
- **18 模块逐条详解**:按报销与权益(5)/申请与审批(6)/薪资与接口(3)/报表与数据(4)四组归类,**每个模块都有精确功能说明**(做什么/谁用/产出),中英对照。
- **6 角色权责详解**:每个角色补充精确权责描述(如 employee=提交报销/查额度/看本人薪资单;sys_admin=全局管理/跨公司切换/全权限),读取 bootstrap 真实 `S.roles`。
- **技术栈 / 合规内核 / 九波迭代**:全部升级为双语对照,迭代时间线新增 Wave9(架构图谱+双语说明书)。
- **样式**:`app.css` 新增 `.bi-row`/`.arch-amx-*`(智能体手册卡)/`.arch-mmx-*`(模块手册)/`.arch-rolex-*`/`.arch-toc`(锚点)全套,响应式 + mobile 单列。

### 🧠 AI 老板驾驶舱 + AI 异常稽查(第四波 · 共享分析引擎)
基于薪资精度引擎(第二波)的数据飞轮,新增**一个分析引擎服务两个产品**——老板看大屏(①)、系统自己揪异常(④):

- **共享分析引擎** (`app/core/analytics.py`):一个引擎三种输出,消费 `payroll_data.compute_monthly()` 全员快照;用 md5 确定性伪历史(`_seed`)生成可复现的演示趋势。
  - `build_overview()` — 驾驶舱聚合:企业总成本 / 总收入 / 净发 / 雇主缴纳 / HRDF / PCB / 加班 / 人数,每项带**环比 MoM%**、6 个月趋势、部门成本分布、人均成本、加班占比。
  - `detect_anomalies()` — 异常稽查:个人级(加班时数 crit>72h / warn>40h、加班成本占比>30%、按比例工资提示)+ 公司级(总成本突增>10%、加班突增>15%),输出**健康分** `health = max(0, 100 - crit×20 - warn×8 - info×2)`。
  - `explain_cost_change()` — AI 解读「这个月人力成本为什么涨了」:对基本工资/加班/EPF雇主/SOCSO雇主/EIS雇主/HRDF/PCB 做因子归因(各因子贡献额 + 占比%),生成中英文自然语言结论(`model: rule-based-v1`)。

- **① AI 老板驾驶舱**(`renderCockpit`):实时大屏 = KPI 卡(企业总成本 hero + MoM 徽章)+ 趋势图(Chart.js bar+line 组合)+ 部门成本环图(doughnut)+ 健康分环(conic-gradient)+ AI 解读条(渐变青→蓝,因子拆解)。
- **④ AI 异常稽查**:驾驶舱右侧异常雷达列表,按严重度 critical/warning/info 分级着色 + 脉冲点动画,实时显示揪出的加班异常 / 薪资跳变 / 总成本突增。
- **新增 API**(权限 `cockpit.view`,授予 payroll/finance/hr_admin/sys_admin):
  - `GET /api/cockpit/overview?company=&month=&role=` — 驾驶舱聚合数据
  - `GET /api/cockpit/anomalies?...` — 异常清单 + 健康分
  - `GET /api/cockpit/explain?...&lang=zh|en` — AI 成本变动解读
- **演示数据**:MY005 加班拉满 80h(60平日+12休息日+8公假)触发 1 critical + 1 warning + 1 info,健康分 70,企业总成本 RM 40,698、环比 +4.1%,AI 解读「最大推手是基本工资/加班」。

### 💰 薪资精度引擎 · FRS 流程2(第二波)
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
- **最后更新**:2026-06-17(六波迭代对齐 FRS:Wave1 业务流程引擎 + Wave2 薪资精度引擎(加班分级/按比例/HRDF/企业总成本) + Wave3 政府法定文件(CP39/SOCSO 8A/银行IBG/凭证分类账/LHDN审计) + ①④ AI 老板驾驶舱(实时大屏+AI解读为何涨了)+ AI 异常稽查(加班/薪资跳变/总成本突增+健康分,共享 analytics 引擎) + 员工自助门户「我的」手机端深度适配(个人中心+我的薪资单,/api/me/summary+/api/me/payslip+payslip.self_view) + 第六波:员工手机端「报销」页打通(mobileGo→my_claim、员工默认锁定马来西亚公司、全链路 RM 统一、self_claim 手机端样式优化、claim.st_posted i18n) + 第七波:数据一致化(effCompany() 统一所有数据源含 AI 对话流) + 手机端布局防溢出(强制单列/解除 grid min-width:auto/box-sizing,双视口零溢出) + 第八波:AI 助手对话式拍照识别(输入区相机按钮→aiOcrUpload 缩略图气泡+视觉识别动画+票据识别结果卡片+一键填入报销单;后端 _wants_upload 意图检测,用户问"怎么报销"时主动递上 upload_action 卡片) + 第九波:系统架构图谱+完整说明书(点击左上角集团 Logo 进入 renderArchitecture,品牌头图+数据流泳道+五层架构+13智能体矩阵+18模块+6角色+技术栈+合规内核+九波时间线)+ 说明书双语并排增强(biRow/biH2,83+处中英对照,锚点导航,5智能体功能手册卡含使用者/能力清单/典型对话/产出,18模块逐条精确说明,6角色权责详解,arch-amx/arch-mmx/arch-rolex/arch-toc CSS 全套))

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

---

## 🌀 第十波 · 代码冗余清理 + 前端混淆加固 (2026-06-17)

### 冗余清理
- 删除未使用导入 ×4(`mock_db`/`Any`/`datetime`/`re`)
- 删除未使用局部变量 ×6(`head_fill`/`tax`/`cc`/`country`/`annual_basic`/`text`)
- 过时验收报告 `SYSTEM_REPORT.md` 归档至 `docs/archive/`
- pyflakes 全量扫描:冗余清零 ✅

### 前端混淆加固(防逆向)
- **可读源码**:保留在 `static/src/*.js`(仅仓库,不发布)
- **混淆产物**:输出到 `static/*.js`(浏览器实际加载)
- **流水线**:`node obfuscate.cjs`(terser 压缩 → javascript-obfuscator 混淆)
- **混淆手段**:标识符乱码化、字符串数组 Base64/RC4 编码、控制流扁平化、死代码注入、反调试、自我保护
- **缓存版本**:`?v=20260614k`

> ⚠️ 安全说明:Web 前端 JS 必须下载到浏览器才能运行,故**无法做到绝对不可逆**。
> 真正的机密(薪资算法/合规规则/Agent 编排)全部在 Python 后端,浏览器永不可见。
> 前端混淆的目标是把逆向成本拉到极高,劝退山寨者——这是行业实战级防护策略。

### 重新混淆命令
```bash
# 修改 static/src/ 下的源码后,运行:
node obfuscate.cjs
# 然后更新 index.html 的 ?v= 缓存版本号,重启 PM2
```
