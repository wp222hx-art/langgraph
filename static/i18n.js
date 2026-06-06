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
