// ═══════════════════════════════════════════════════════════
//  Paydaes ClaimGPT · 真 i18n 国际化字典 + 翻译引擎
//  支持 6 语言:zh(简中) / en(English) 全量,ms/th/vi/id 框架
//  用法:
//    - JS 取词:  t('nav.dashboard')
//    - HTML 标记: <span data-i18n="nav.dashboard"></span>
//    - 属性翻译:  <input data-i18n-ph="ai.placeholder">  (placeholder)
//                <button data-i18n-title="...">         (title)
//  切换语言:  setLang('en') → 自动重扫 DOM + 触发 onLangChange 回调
// ═══════════════════════════════════════════════════════════

const I18N = {
  // ─────────────── 简体中文(基准语言) ───────────────
  zh: {
    app: { title: 'Paydaes ClaimGPT · 集团级 AI 报销智能平台', group: 'Paydaes 集团' },
    topbar: {
      global: '全球合规', notifications: '通知', ai_assistant: 'AI 助手',
      switch_company: '切换公司', switch_role: '切换角色', switch_lang: '切换语言',
    },
    nav: {
      footer_engine: 'LangGraph 编排引擎', footer_agents: '5主 + 8子 Agent · 18 模块',
      footer_version: 'Paydaes ClaimGPT · 集团版 V3.0',
      ai_config: 'AI 配置后台',
    },
    core: {
      online: '在线', agents: '智能体', active: '活跃', modules: '模块', running: '运行',
      latency: '时延', tip_active: '运行中',
    },
    help: {
      open: '帮助中心', title: '帮助中心', subtitle: '使用指南 · 系统介绍 · 常见问题',
    },
    aiconf: {
      title: 'AI 配置后台', subtitle: '统一管理 API 平台、模型与 Agent 分发 · Key 加密存储,绝不外泄前端',
      tab_basic: '① 基础配置', tab_model: '② 模型管理', tab_dispatch: '③ 分发应用',
      // 总览
      ov_providers: '已接入平台', ov_active: '已激活', ov_models: '启用模型',
      ov_bound: 'Agent 已分发',
      // 基础配置
      add_provider: '+ 接入新平台', preset: '选择平台', custom: '自定义',
      provider_name: '平台名称', base_url: 'API 基址', api_key: 'API Key',
      api_key_ph: '粘贴 API Key(留空则不修改)', kind: '协议类型',
      submit: '提交保存', verify: '验证 Key', activate: '激活', deactivate: '停用',
      del: '删除', pull_models: '拉取模型',
      st_inactive: '未激活', st_verified: '已验证', st_active: '运行中', st_error: '异常',
      key_tail: 'Key 末位', no_provider: '尚未接入任何平台,点击右上角接入。',
      confirm_del: '确认删除该平台?其模型与绑定将一并清除。',
      verifying: '验证中…', verify_ok: '验证通过 ✅', pulling: '拉取模型中…',
      // 模型管理
      models_of: '的模型', recognize: '认定启用', model_id: '模型标识',
      capability: '能力', enabled: '已启用', disabled: '未启用',
      no_models: '暂无模型,请先在「基础配置」验证 Key 后自动拉取,或点「拉取模型」。',
      cap_chat: '对话', cap_vision: '视觉/OCR', cap_reasoning: '推理',
      filter_provider: '按平台筛选', all_providers: '全部平台',
      // 分发应用
      dispatch_hint: '把已认定的模型分发给各 Agent。未分发的 Agent 自动回退到内置规则引擎。',
      agent: 'Agent', bind_provider: '平台', bind_model: '模型',
      core_agents: '核心能力节点', main_agents: '主智能体',
      unbound: '未分发(用规则)', save_binding: '保存分发', bound_ok: '已分发 ✅',
      select_model: '— 选择模型 —', select_provider: '— 选择平台 —',
    },
    ai: {
      team: 'AI 智能体团队', placeholder: '用大白话告诉我……',
      thinking: '智能体团队协作思考中…', think_done: '思考完成',
      hello: '你好,我是', collab: '智能体团队协作',
      summon: '唤起 AI 智能体', give_to_ai: '交给AI',
    },
    dashboard: {
      title: '工作台', trend: '报销趋势分析', todos: '待办事项',
      modules_count: '个模块',
    },
    compliance: {
      title: '全球合规中心',
      subtitle: '调用全球各国税收、报销、做账体系 · 切换公司自动适配本地合规',
      tax_type: '税种', tax_rate: '税率', accounting_std: '会计准则',
      view_full: '查看完整合规体系', tax_system: '税收体系',
      claim_rules: '报销规则', accounting_system: '做账体系',
      system_suffix: '合规体系', standard: '准则', fiscal: '财年', elements: '科目',
    },
    common: {
      back: 'Back', save: 'Save Changes', search: 'Search', clear: 'Clear',
      download: 'Download', add: '+ Add', action: '操作', all: '全部',
      active_only: '仅显示启用状态', page_of: '页', loading: '加载中…',
      confirm: '确认', cancel: '取消', yes: '是', no: '否',
      high: '高', mid: '中', low: '低',
      passed: '✅ 通过', risk_level: '风险等级', check: '校验',
    },
    table: {
      no: '单号', applicant: '申请人', type: '类型', amount: '金额',
      risk: '风险', note: '备注', status: '状态', date: '日期',
      reason: '原因', operator: '操作人', code: '编码', name: '名称', limit: '限额', group: '分组',
    },
    role: {
      switch_title: '切换角色(体验不同权限)',
    },
    claim: {
      my_quota: '我的年度额度', used: '已用', photo_ai: '拍照报销(AI)',
      new_form: '新建报销单', upload_invoice: '上传发票图片 · AI 自动识别回填',
      ocr_reading: 'AI 正在识别票据…', ocr_err: '识别失败,请手动填写',
      f_type: '请选择报销类型', f_merchant: '商户名称', f_amount: '金额', f_note: '备注说明',
      submit: '提交报销单', submitting: '提交中…', submitted: '已生成单据',
      need_type: '请先选择报销类型', need_amount: '请输入有效金额',
      tax: '可抵扣税', recent_real: '实时报销记录(真实数据库)', refresh: '刷新',
      empty: '暂无报销记录', load_err: '加载失败', total: '合计',
      c_id: '单号', c_type: '类型', c_amount: '金额', c_risk: '风险分', c_status: '状态', c_date: '时间',
      st_pending: '待审批', st_approved: '已批准', st_rejected: '已驳回', st_paid: '已支付',
    },
    crud: {
      ops: '操作', seed: '内置', save: '保存', cancel: '取消', required: '必填',
      saved: '已保存', deleted: '已删除', confirm_del: '确定删除这一行吗?',
      approve: '通过', reject: '驳回', approved: '已通过', rejected: '已驳回',
      batch_low: '一键批量通过低风险', batch_done: '已批量通过笔数:',
      edit: '编辑', not_found: '未找到',
    },
    fam: {
      archive: '家属档案', add: '新增家属', name: '家属姓名', need_name: '请输入家属姓名',
      added: '已新增家属', empty: '暂无家属', linkable: '可关联报销', ai: '对话式登记家属',
      spouse: '配偶', child: '子女', parent: '父母',
    },
    perm: { denied: '权限不足,操作被拒绝' },
    balance: {
      adjust_title: '余额调整', emp: '员工', kind: '调整类型', add: '增加', reduce: '减少', transfer: '转移',
      to_emp: '转移目标员工', amount: '金额', reason: '调整原因', reason_ph: '请填写调整原因(必填留痕)',
      submit: '确认调整', audit_note: '所有调整全程留痕,可审计追溯', remaining: '剩余额度',
      no_perm: '当前身份无权调整余额,仅可查看历史。', allowed_roles: '可执行该操作:财务/审计、系统管理员',
      need_emp: '请选择员工', need_amount: '请输入有效金额', need_reason: '调整原因必填', need_target: '请选择转移目标(不能与本人相同)',
      done: '调整成功', history: '调整历史(审计留痕)', empty: '暂无调整记录',
      h_date: '时间', h_kind: '类型', h_amount: '金额', h_emp: '员工', h_reason: '原因', h_op: '操作人',
    },
    report: {
      export_excel: '导出 Excel', export_ppt: '导出 PPT', exporting: '正在生成报表…', export_done: '导出完成',
      no_perm: '当前身份无权导出报表', ai_insight: 'AI 洞察', deep_analysis: '对话式深度分析',
      statutory_title: '🇲🇾 马来西亚法定合规表格', statutory_desc: '一键生成符合 LHDN / KWSP / PERKESO 国家级要求的法定表格',
      payslip: '工资单 Payslip', epf_borang_a: 'EPF Borang A', ea_form: 'EA Form (C.P.8A)',
      payslip_d: '含 EPF/SOCSO/EIS/PCB 法定扣除明细', epf_borang_a_d: '月度公积金缴款表 (KWSP 6)', ea_form_d: '年度个人薪酬扣税表 · Part A~F',
      statutory_note: '依现行法定费率生成,正式申报请以官方系统为准',
      import_title: '导入真实员工薪资名单', import_desc: '下载标准模板填写后上传,系统将解析校验并用精确 PCB 引擎试算预览',
      import_tpl: '下载导入模板', import_upload: '上传 Excel 名单',
      import_parsing: '正在解析校验…', import_ok: '全部校验通过', import_partial: '部分行有误,请修正后重传',
      import_rows: '数据行', import_valid: '有效', import_invalid: '错误',
      import_preview_ok: '校验通过(精确 PCB 试算预览)', import_preview_err: '错误清单',
      import_row: '第', import_col_no: '编号', import_col_name: '姓名', import_col_gross: '总薪酬', import_col_net: '净薪',
    },
    ct: { code: '编码', name: '名称', name_en: '英文名', grp: '分组', limit: '限额', need_invoice: '需发票' },
  },

  // ─────────────── English(全量) ───────────────
  en: {
    app: { title: 'Paydaes ClaimGPT · Group AI Expense Platform', group: 'Paydaes Group' },
    topbar: {
      global: 'Global Compliance', notifications: 'Notifications', ai_assistant: 'AI Assistant',
      switch_company: 'Switch Company', switch_role: 'Switch Role', switch_lang: 'Language',
    },
    nav: {
      footer_engine: 'LangGraph Orchestration', footer_agents: '5 Main + 8 Sub Agents · 18 Modules',
      footer_version: 'Paydaes ClaimGPT · Enterprise V3.0',
      ai_config: 'AI Config',
    },
    core: {
      online: 'ONLINE', agents: 'Agents', active: 'active', modules: 'Modules', running: 'running',
      latency: 'Latency', tip_active: 'running',
    },
    help: {
      open: 'Help Center', title: 'Help Center', subtitle: 'User Guide · System Overview · FAQ',
    },
    aiconf: {
      title: 'AI Configuration Console', subtitle: 'Manage API providers, models & agent dispatch · Keys encrypted, never exposed to frontend',
      tab_basic: '① Providers', tab_model: '② Models', tab_dispatch: '③ Dispatch',
      ov_providers: 'Providers', ov_active: 'Active', ov_models: 'Enabled Models',
      ov_bound: 'Agents Bound',
      add_provider: '+ Add Provider', preset: 'Select Platform', custom: 'Custom',
      provider_name: 'Provider Name', base_url: 'API Base URL', api_key: 'API Key',
      api_key_ph: 'Paste API Key (leave blank to keep)', kind: 'Protocol',
      submit: 'Save', verify: 'Verify Key', activate: 'Activate', deactivate: 'Deactivate',
      del: 'Delete', pull_models: 'Pull Models',
      st_inactive: 'Inactive', st_verified: 'Verified', st_active: 'Active', st_error: 'Error',
      key_tail: 'Key tail', no_provider: 'No provider yet. Click top-right to add one.',
      confirm_del: 'Delete this provider? Its models and bindings will be removed.',
      verifying: 'Verifying…', verify_ok: 'Verified ✅', pulling: 'Pulling models…',
      models_of: ' models', recognize: 'Enable', model_id: 'Model ID',
      capability: 'Capability', enabled: 'Enabled', disabled: 'Disabled',
      no_models: 'No models yet. Verify a Key in Providers to auto-pull, or click Pull Models.',
      cap_chat: 'Chat', cap_vision: 'Vision/OCR', cap_reasoning: 'Reasoning',
      filter_provider: 'Filter by provider', all_providers: 'All providers',
      dispatch_hint: 'Dispatch enabled models to agents. Unbound agents fall back to the built-in rule engine.',
      agent: 'Agent', bind_provider: 'Provider', bind_model: 'Model',
      core_agents: 'Core Capability Nodes', main_agents: 'Main Agents',
      unbound: 'Unbound (rules)', save_binding: 'Save', bound_ok: 'Bound ✅',
      select_model: '— Select model —', select_provider: '— Select provider —',
    },
    ai: {
      team: 'AI Agent Team', placeholder: 'Tell me in plain words…',
      thinking: 'Agent team collaborating…', think_done: 'Thinking done',
      hello: "Hi, I'm", collab: 'Agent team collaboration',
      summon: 'Summon AI Agents', give_to_ai: 'Ask AI',
    },
    dashboard: {
      title: 'Dashboard', trend: 'Expense Trend Analysis', todos: 'To-do List',
      modules_count: 'modules',
    },
    compliance: {
      title: 'Global Compliance Center',
      subtitle: 'Tax, expense & accounting systems worldwide · Auto-adapt on company switch',
      tax_type: 'Tax Type', tax_rate: 'Tax Rate', accounting_std: 'Accounting Standard',
      view_full: 'View full compliance', tax_system: 'Tax System',
      claim_rules: 'Claim Rules', accounting_system: 'Accounting System',
      system_suffix: 'Compliance', standard: 'Standard', fiscal: 'Fiscal Year', elements: 'Accounts',
    },
    common: {
      back: 'Back', save: 'Save Changes', search: 'Search', clear: 'Clear',
      download: 'Download', add: '+ Add', action: 'Action', all: 'All',
      active_only: 'Active Status only', page_of: 'of', loading: 'Loading…',
      confirm: 'Confirm', cancel: 'Cancel', yes: 'Yes', no: 'No',
      high: 'High', mid: 'Medium', low: 'Low',
      passed: '✅ Passed', risk_level: 'Risk Level', check: 'Validation',
    },
    table: {
      no: 'No.', applicant: 'Applicant', type: 'Type', amount: 'Amount',
      risk: 'Risk', note: 'Note', status: 'Status', date: 'Date',
      reason: 'Reason', operator: 'Operator', code: 'Code', name: 'Name', limit: 'Limit', group: 'Group',
    },
    role: {
      switch_title: 'Switch Role (try different permissions)',
    },
    claim: {
      my_quota: 'My Annual Quota', used: 'Used', photo_ai: 'Snap & Claim (AI)',
      new_form: 'New Claim', upload_invoice: 'Upload invoice · AI auto-fill',
      ocr_reading: 'AI reading invoice…', ocr_err: 'Recognition failed, please fill manually',
      f_type: 'Select claim type', f_merchant: 'Merchant', f_amount: 'Amount', f_note: 'Note',
      submit: 'Submit Claim', submitting: 'Submitting…', submitted: 'Created',
      need_type: 'Please select a claim type', need_amount: 'Enter a valid amount',
      tax: 'Deductible Tax', recent_real: 'Live Claims (Real Database)', refresh: 'Refresh',
      empty: 'No claims yet', load_err: 'Load failed', total: 'Total',
      c_id: 'ID', c_type: 'Type', c_amount: 'Amount', c_risk: 'Risk', c_status: 'Status', c_date: 'Time',
      st_pending: 'Pending', st_approved: 'Approved', st_rejected: 'Rejected', st_paid: 'Paid',
    },
    crud: {
      ops: 'Actions', seed: 'Built-in', save: 'Save', cancel: 'Cancel', required: 'required',
      saved: 'Saved', deleted: 'Deleted', confirm_del: 'Delete this row?',
      approve: 'Approve', reject: 'Reject', approved: 'approved', rejected: 'rejected',
      batch_low: 'Batch approve low-risk', batch_done: 'Batch approved:',
      edit: 'Edit', not_found: 'Not found',
    },
    fam: {
      archive: 'Family Archive', add: 'Add Member', name: 'Member name', need_name: 'Please enter a name',
      added: 'Member added', empty: 'No members', linkable: 'Claim-linkable', ai: 'Register via chat',
      spouse: 'Spouse', child: 'Child', parent: 'Parent',
    },
    perm: { denied: 'Permission denied' },
    balance: {
      adjust_title: 'Balance Adjustment', emp: 'Employee', kind: 'Type', add: 'Increase', reduce: 'Decrease', transfer: 'Transfer',
      to_emp: 'Transfer target', amount: 'Amount', reason: 'Reason', reason_ph: 'Reason is required (audit trail)',
      submit: 'Confirm', audit_note: 'All adjustments are fully audited & traceable', remaining: 'Remaining',
      no_perm: 'Your role cannot adjust balances; history is read-only.', allowed_roles: 'Allowed: Finance/Audit, System Admin',
      need_emp: 'Please select an employee', need_amount: 'Enter a valid amount', need_reason: 'Reason is required', need_target: 'Select a transfer target (not self)',
      done: 'Adjusted', history: 'Adjustment History (Audit)', empty: 'No records yet',
      h_date: 'Time', h_kind: 'Type', h_amount: 'Amount', h_emp: 'Employee', h_reason: 'Reason', h_op: 'Operator',
    },
    report: {
      export_excel: 'Export Excel', export_ppt: 'Export PPT', exporting: 'Generating report…', export_done: 'Export done',
      no_perm: 'Your role cannot export reports', ai_insight: 'AI Insight', deep_analysis: 'Conversational deep analysis',
      statutory_title: '🇲🇾 Malaysia Statutory Forms', statutory_desc: 'One-click generate LHDN / KWSP / PERKESO compliant statutory forms',
      payslip: 'Payslip', epf_borang_a: 'EPF Borang A', ea_form: 'EA Form (C.P.8A)',
      payslip_d: 'With EPF/SOCSO/EIS/PCB statutory deductions', epf_borang_a_d: 'Monthly EPF contribution (KWSP 6)', ea_form_d: 'Annual remuneration statement · Part A~F',
      statutory_note: 'Generated per current statutory rates; file via official systems for submission',
      import_title: 'Import Real Employee Payroll Roster', import_desc: 'Download the template, fill it in & upload — system validates and previews with the precise PCB engine',
      import_tpl: 'Download Template', import_upload: 'Upload Excel Roster',
      import_parsing: 'Parsing & validating…', import_ok: 'All rows valid', import_partial: 'Some rows have errors, please fix & re-upload',
      import_rows: 'Rows', import_valid: 'Valid', import_invalid: 'Errors',
      import_preview_ok: 'Valid rows (precise PCB preview)', import_preview_err: 'Error list',
      import_row: 'Row', import_col_no: 'No', import_col_name: 'Name', import_col_gross: 'Gross', import_col_net: 'Net',
    },
    ct: { code: 'Code', name: 'Name', name_en: 'English name', grp: 'Group', limit: 'Limit', need_invoice: 'Invoice req.' },
  },

  // ─── 其余 4 语言:回退到 en,保留 key 框架,后续可逐步填充 ───
  ms: {}, th: {}, vi: {}, id: {},
};

// 当前语言(默认中文,localStorage 记忆)
let _lang = localStorage.getItem('claimgpt_lang') || 'zh';
const _langChangeCbs = [];

// 取词:支持点号路径 'nav.dashboard',未命中回退 en → zh → key 本身
function t(key, fallback) {
  const tryGet = (dict) => key.split('.').reduce((o, k) => (o && o[k] != null) ? o[k] : undefined, dict);
  let v = tryGet(I18N[_lang]);
  if (v === undefined && _lang !== 'en') v = tryGet(I18N.en);   // 回退英文
  if (v === undefined) v = tryGet(I18N.zh);                      // 再回退中文
  return v !== undefined ? v : (fallback !== undefined ? fallback : key);
}

function getLang() { return _lang; }

function setLang(code) {
  _lang = I18N[code] ? code : 'en';
  localStorage.setItem('claimgpt_lang', _lang);
  document.documentElement.lang = _lang === 'zh' ? 'zh-CN' : _lang;
  applyI18n();
  _langChangeCbs.forEach(cb => { try { cb(_lang); } catch (e) { console.error(e); } });
}

// 注册语言切换回调(用于重渲染动态内容)
function onLangChange(cb) { _langChangeCbs.push(cb); }

// 扫描 DOM,翻译所有带 data-i18n* 的元素
function applyI18n(root = document) {
  root.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  root.querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
  root.querySelectorAll('[data-i18n-title]').forEach(el => { el.title = t(el.dataset.i18nTitle); });
  root.querySelectorAll('[data-i18n-html]').forEach(el => { el.innerHTML = t(el.dataset.i18nHtml); });
}

// 暴露到全局
window.t = t;
window.setLang = setLang;
window.getLang = getLang;
window.onLangChange = onLangChange;
window.applyI18n = applyI18n;
window.I18N = I18N;
