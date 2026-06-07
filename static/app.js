// ═══════════ Paydaes ClaimGPT 集团版 前端 ═══════════
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const fmt = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');

const S = {           // 全局状态
  groups: [], roles: [], languages: [], nav: [], agents: [],
  group: null, company: null, role: null,
  get lang() { return getLang(); },
  currentNav: 'dashboard', currentAgent: null,
  threadId: 'web-' + Math.random().toString(36).slice(2, 8),
};

// ── 启动 ──
async function boot() {
  const d = await fetch('/api/bootstrap').then(r => r.json());
  Object.assign(S, { groups: d.groups, roles: d.roles, languages: d.languages, nav: d.nav, agents: d.agents });
  S.group = d.groups[0];
  S.company = d.groups[0].companies[0];
  S.role = d.roles.find(r => r.id === 'sys_admin');
  S.currentAgent = d.agents[0];
  // i18n:语言切换时重扫静态 DOM + 重渲染动态区(导航/当前页/智能体条)
  onLangChange(() => {
    renderTopbar(); renderNav(); renderAgentTabs();
    go(S.currentNav);
    if ($('#ai-messages').dataset.init) selectAgent(S.currentAgent);
  });
  applyI18n();                    // 首次翻译静态 DOM
  renderTopbar(); renderNav(); renderAgentTabs();
  go('dashboard');
  bindGlobal();
}

// ════════ 顶部栏渲染 ════════
function renderTopbar() {
  $('#group-logo').textContent = S.group.logo;
  $('#group-logo').style.background = S.group.color;
  $('#group-name').textContent = nameOf(S.group);
  $('#company-flag').textContent = S.company.flag;
  $('#company-name').textContent = nameOf(S.company);
  $('#role-name').textContent = nameOf(S.role);
  $('#role-avatar').innerHTML = `<i class="fas ${S.role.icon}"></i>`;
  $('#role-avatar').style.background = S.role.color;
  $('#lang-flag').textContent = (S.languages.find(l => l.code === S.lang) || {}).flag || '🇨🇳';
}

// 双语取名:对象带 name_en 时按当前语言取,否则回退 name
function nameOf(o) {
  if (!o) return '';
  if (S.lang === 'en' && o.name_en) return o.name_en;
  return o.name || o.name_en || '';
}
function descOf(o) {
  if (!o) return '';
  if (S.lang === 'en' && o.desc_en) return o.desc_en;
  return o.desc || o.desc_en || '';
}

// ════════ 左侧导航树(按角色过滤) ════════
function renderNav() {
  const allow = S.role.menus;
  const html = S.nav.filter(n => allow.includes(n.id)).map(n => {
    if (n.type === 'page') {
      return `<div class="nav-item ${S.currentNav === n.id ? 'active' : ''}" data-nav="${n.id}">
        <i class="fas ${n.icon}"></i><span>${nameOf(n)}</span>
        ${n.badge ? `<span class="b-new ml-auto">${n.badge}</span>` : ''}</div>`;
    }
    const kids = n.children.map(c =>
      `<div class="nav-sub ${S.currentNav === c.id ? 'active' : ''}" data-nav="${c.id}" data-module="${c.module}">${nameOf(c)}</div>`).join('');
    const open = n.children.some(c => c.id === S.currentNav);
    return `<div data-group="${n.id}">
      <div class="nav-group-title" onclick="toggleGroup('${n.id}')">
        <i class="fas ${n.icon}"></i><span>${nameOf(n)}</span>
        <i class="fas fa-chevron-${open ? 'down' : 'right'} text-[10px] text-slate-300 ml-auto group-arrow"></i>
      </div>
      <div class="nav-children ${open ? '' : 'hidden'}" data-children="${n.id}">${kids}</div>
    </div>`;
  }).join('');
  // 注入「AI 配置」固定入口(仅 settings 权限角色可见:hr_admin / sys_admin)
  let extra = '';
  if (S.role.menus.includes('settings')) {
    extra = `<div class="nav-item ${S.currentNav === 'ai_config' ? 'active' : ''}" data-nav="ai_config">
      <i class="fas fa-plug-circle-bolt"></i><span>${t('nav.ai_config')}</span>
      <span class="b-new ml-auto">AI</span></div>`;
  }
  $('#nav-tree').innerHTML = html + extra;
  $$('[data-nav]').forEach(el => el.onclick = () => { go(el.dataset.nav); closeMobileSidebar(); });
}
function toggleGroup(id) {
  const c = $(`[data-children="${id}"]`);
  const arrow = c.previousElementSibling.querySelector('.group-arrow');
  c.classList.toggle('hidden');
  arrow.className = `fas fa-chevron-${c.classList.contains('hidden') ? 'right' : 'down'} text-[10px] text-slate-300 ml-auto group-arrow`;
}

// ════════ 路由 ════════
function go(navId) {
  S.currentNav = navId;
  $$('[data-nav]').forEach(el => el.classList.toggle('active', el.dataset.nav === navId));
  const view = $('#view');
  view.classList.remove('fade-in'); void view.offsetWidth; view.classList.add('fade-in');
  if (navId === 'dashboard') return renderDashboard();
  if (navId === 'global') return renderCompliance();
  if (navId === 'ai_config') return renderAIConfig();
  renderModule(navId);
}

window.toggleGroup = toggleGroup;
window.go = go;
boot();

// ════════ 工作台仪表盘 ════════
async function renderDashboard() {
  const d = await fetch(`/api/dashboard?company=${S.company.id}`).then(r => r.json());
  const kpi = d.kpi.map(k => `
    <div class="kpi-card">
      <div class="flex items-center justify-between">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center text-white" style="background:${k.color}"><i class="fas ${k.icon}"></i></div>
        <span class="badge ${k.trend.includes('+') ? 'b-low' : 'b-info'}">${S.lang === 'en' && k.trend_en ? k.trend_en : k.trend}</span>
      </div>
      <div class="mt-3 text-2xl font-bold text-slate-900">${k.value}<span class="text-sm font-normal text-slate-400 ml-1">${S.lang === 'en' && k.unit_en !== undefined ? k.unit_en : k.unit}</span></div>
      <div class="text-xs text-slate-400 mt-0.5">${S.lang === 'en' && k.label_en ? k.label_en : k.label}</div>
    </div>`).join('');
  const todos = d.todos.map(td => `
    <div class="flex items-center gap-3 py-2.5 border-b border-slate-50 last:border-0">
      <span class="w-1.5 h-1.5 rounded-full" style="background:${td.level === 'high' ? '#ef4444' : '#f59e0b'}"></span>
      <span class="flex-1 text-sm text-slate-700">${S.lang === 'en' && td.title_en ? td.title_en : td.title}</span>
      <span class="badge b-info">${S.lang === 'en' && td.type_en ? td.type_en : td.type}</span>
      <button class="btn btn-ai text-xs py-1" onclick="openAI('${td.agent}','${td.title}')"><i class="fas fa-robot"></i> ${t('ai.give_to_ai')}</button>
    </div>`).join('');
  $('#view').innerHTML = `
    <div class="flex items-center justify-between mb-5 flex-wrap gap-2">
      <div><h1 class="page-title">${t('dashboard.title')}</h1><p class="text-sm text-slate-400 mt-0.5">${S.company.flag} ${nameOf(S.company)} · ${nameOf(S.group)}</p></div>
      <button class="btn btn-ai" onclick="toggleAI(true)"><i class="fas fa-robot"></i> ${t('ai.summon')}</button>
    </div>
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-5">${kpi}</div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="panel p-5 lg:col-span-2">
        <div class="font-semibold text-slate-800 mb-3">${t('dashboard.trend')}</div>
        <div class="chart-box"><canvas id="dash-chart"></canvas></div>
      </div>
      <div class="panel p-5">
        <div class="font-semibold text-slate-800 mb-1">${t('dashboard.todos')} <span class="badge b-high ml-1">${d.todos.length}</span></div>
        <div>${todos}</div>
      </div>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mt-5">
      ${S.agents.map(a => `<div class="panel p-4 cursor-pointer hover:shadow-md transition" onclick="openAI('${a.id}','')">
        <div class="text-2xl mb-1">${a.emoji}</div>
        <div class="font-semibold text-sm text-slate-800">${nameOf(a)}</div>
        <div class="text-[11px] text-slate-400 mt-1 leading-snug">${descOf(a)}</div>
        <div class="text-[10px] text-teal-500 mt-2">${a.modules.length} ${t('dashboard.modules_count')}</div>
      </div>`).join('')}
    </div>`;
  const chLabels = (S.lang === 'en' && d.chart.labels_en) ? d.chart.labels_en : d.chart.labels;
  new Chart($('#dash-chart'), {
    type: 'line',
    data: { labels: chLabels, datasets: d.chart.series.map((s, i) => ({
      label: (S.lang === 'en' && s.name_en) ? s.name_en : s.name, data: s.data, borderColor: i ? '#ec4899' : '#20c997',
      backgroundColor: i ? 'rgba(236,72,153,.1)' : 'rgba(32,201,151,.12)', fill: true, tension: .4 })) },
    options: { plugins: { legend: { labels: { font: { size: 11 } } } }, scales: { y: { beginAtZero: true } }, responsive: true, maintainAspectRatio: false }
  });
}

// ════════ 18 模块工作区 ════════
async function renderModule(navId) {
  const m = await fetch(`/api/module/${navId}?company=${S.company.id}&lang=${S.lang}`).then(r => r.json());
  const actions = (m.actions || []).map((a, i) =>
    `<button class="btn ${a.includes('AI') ? 'btn-ai' : (i === 0 ? 'btn-primary' : 'btn-ghost')}" onclick="moduleAction('${a}','${m.title}')">
      ${a.includes('AI') ? '<i class=\"fas fa-robot\"></i>' : '<i class=\"fas fa-plus\"></i>'} ${a}</button>`).join('');
  let body = '';
  if (m.layout === 'table') body = tableView(m);
  else if (m.layout === 'approval') body = approvalView(m);
  else if (m.layout === 'flow') body = flowView(m);
  else if (m.layout === 'report') body = reportView(m);
  else if (m.layout === 'self_claim') body = selfClaimView(m);
  else if (m.layout === 'balance') body = balanceView(m);
  else if (m.layout === 'family') body = familyView(m);
  // ── Paydaes 7 块积木 ──
  else if (m.layout === 'p_inline') body = pInlineView(m);
  else if (m.layout === 'p_detail') body = pDetailView(m);
  else if (m.layout === 'p_list') body = pListView(m);
  else if (m.layout === 'p_shuttle') body = pShuttleView(m);
  else if (m.layout === 'p_formula') body = pFormulaView(m);
  else if (m.layout === 'p_map') body = pMapView(m);
  else if (m.layout === 'p_tabset') body = pTabsetView(m);
  else body = tableView(m);

  const domainBadge = m.domain ? `<span class="badge b-info ml-2" style="font-size:11px">${m.domain}</span>` : '';
  $('#view').innerHTML = `
    <div class="flex items-start justify-between mb-4 flex-wrap gap-3">
      <div><h1 class="page-title">${m.title}${domainBadge}</h1><p class="text-sm text-slate-400 mt-1">${m.desc || ''}</p></div>
      <div class="flex gap-2 flex-wrap">${actions}</div>
    </div>
    ${m.tabs_top ? topTabsBar(m) : ''}
    ${body}`;
  if (m.layout === 'report') drawReportChart(m);
}

function tableView(m) {
  return `<div class="panel p-1.5"><div class="table-wrap"><table class="dtable">
    <thead><tr>${(m.columns || []).map(c => `<th>${c}</th>`).join('')}</tr></thead>
    <tbody>${(m.rows || []).map(r => `<tr>${r.map(c => `<td>${badgeCell(c)}</td>`).join('')}</tr>`).join('')}</tbody>
  </table></div></div>`;
}
function badgeCell(c) {
  const s = String(c);
  if (s === '高') return `<span class="badge b-high">${t('common.high')}</span>`;
  if (s === '中') return `<span class="badge b-mid">${t('common.mid')}</span>`;
  if (s === '低') return `<span class="badge b-low">${t('common.low')}</span>`;
  if (s.includes('✅') || s.includes('已批') || s.includes('生效') || s.includes('已支付')) return `<span class="badge b-low">${s}</span>`;
  if (s.includes('审批中') || s.includes('进行中') || s.includes('⚠️')) return `<span class="badge b-mid">${s}</span>`;
  return s;
}

function approvalView(m) {
  const sum = m.summary || {};
  return `<div class="panel p-5">
    <div class="flex gap-2 mb-4 flex-wrap">
      <span class="badge b-low">🟢 低风险 ${sum['低'] || 0}</span>
      <span class="badge b-mid">🟡 中风险 ${sum['中'] || 0}</span>
      <span class="badge b-high">🔴 高风险 ${sum['高'] || 0}</span>
    </div>
    <div class="table-wrap"><table class="dtable">
      <thead><tr>${m.columns.map(c => `<th>${c}</th>`).join('')}<th>操作</th></tr></thead>
      <tbody>${m.rows.map(r => `<tr>${r.map(c => `<td>${badgeCell(c)}</td>`).join('')}
        <td><button class="btn btn-ghost text-xs py-1">审批</button></td></tr>`).join('')}</tbody>
    </table></div>
    <div class="flex gap-2 mt-4 flex-wrap">
      <button class="btn btn-primary" style="background:#10b981" onclick="moduleAction('批量通过低风险','${m.title}')"><i class="fas fa-bolt"></i> 一键批量通过低风险</button>
      <button class="btn btn-ai" onclick="openAI('ApprovalCopilot','帮我审批待审单据')"><i class="fas fa-robot"></i> AI 风险分级建议</button>
    </div></div>`;
}

function flowView(m) {
  const steps = m.steps.map(s => {
    const done = s.status === '完成', doing = s.status === '进行中';
    return `<div class="flow-step">
      <div class="flow-ico" style="background:${done ? '#dcfce7' : doing ? '#fef3c7' : '#f1f5f9'};color:${done ? '#16a34a' : doing ? '#d97706' : '#94a3b8'}">
        <i class="fas ${done ? 'fa-check' : doing ? 'fa-spinner fa-spin' : 'fa-clock'}"></i></div>
      <div class="flex-1"><div class="text-sm font-medium text-slate-700">${s.step}</div><div class="text-xs text-slate-400">${s.result}</div></div>
      <span class="badge ${done ? 'b-low' : doing ? 'b-mid' : 'b-info'}">${s.status}</span></div>`;
  }).join('');
  return `<div class="panel p-5">
    <div class="flex items-center gap-2 mb-4 text-sm"><span class="badge b-info">批次 ${m.batch_code}</span>
      ${m.rollback ? '<span class="badge b-mid"><i class="fas fa-rotate-left"></i> 支持回滚</span>' : ''}
      <span class="text-slate-400 text-xs ml-auto"><i class="fas fa-shield-halved text-emerald-400"></i> LangGraph Checkpoint 断点续跑保护</span></div>
    ${steps}
    <div class="flex gap-2 mt-3"><button class="btn btn-ai" onclick="openAI('PayrollNavigator','执行薪资跑批')"><i class="fas fa-robot"></i> AI 自主跑批</button>
      ${m.rollback ? '<button class="btn btn-ghost"><i class="fas fa-rotate-left"></i> 回滚批次</button>' : ''}</div></div>`;
}

function reportView(m) {
  return `<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="panel p-5 lg:col-span-2"><div class="font-semibold text-slate-800 mb-3">${m.title}</div><div class="chart-box"><canvas id="rpt-chart"></canvas></div></div>
    <div class="panel p-5"><div class="font-semibold text-slate-800 mb-2"><i class="fas fa-lightbulb text-amber-400"></i> AI 洞察</div>
      <p class="text-sm text-slate-600 leading-relaxed">${m.insight}</p>
      <button class="btn btn-ai w-full mt-4 justify-center" onclick="openAI('InsightOracle','分析${m.title}')"><i class="fas fa-robot"></i> 对话式深度分析</button></div></div>`;
}
function drawReportChart(m) {
  new Chart($('#rpt-chart'), { type: m.chart.kind || 'bar',
    data: { labels: m.chart.labels, datasets: m.chart.series.map(s => ({ label: s.name, data: s.data, backgroundColor: 'rgba(32,201,151,.75)', borderRadius: 6 })) },
    options: { plugins: { legend: { labels: { font: { size: 11 } } } }, scales: { y: { beginAtZero: true } }, responsive: true, maintainAspectRatio: false } });
}

function selfClaimView(m) {
  const b = m.balance;
  return `<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="panel p-5"><div class="text-sm text-slate-400">我的年度额度</div>
      <div class="text-3xl font-bold text-slate-900 mt-1">${b.remaining}<span class="text-base text-slate-400">/${b.annual}</span></div>
      <div class="mt-3 h-2 bg-slate-100 rounded-full overflow-hidden"><div class="h-full bg-[#20c997]" style="width:${b.used / b.annual * 100}%"></div></div>
      <div class="text-xs text-slate-400 mt-1.5">已用 ${b.used} · ${b.name} · ${b.level}</div>
      <button class="btn btn-ai w-full mt-4 justify-center" onclick="openAI('ClaimMate','我要拍照报销')"><i class="fas fa-camera"></i> 拍照报销(AI)</button></div>
    <div class="panel p-5 lg:col-span-2"><div class="font-semibold text-slate-800 mb-3">最近报销记录</div>
      <div class="table-wrap"><table class="dtable"><thead><tr><th>单号</th><th>类型</th><th>金额</th><th>状态</th><th>日期</th></tr></thead>
        <tbody>${m.recent.map(r => `<tr>${r.map(c => `<td>${badgeCell(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div></div>`;
}

function balanceView(m) {
  const b = m.balance;
  return `<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="panel p-5"><div class="text-sm text-slate-400">当前余额 · ${b.name}</div>
      <div class="text-3xl font-bold text-slate-900 mt-1">${b.remaining}</div>
      <div class="flex gap-2 mt-4"><button class="btn btn-ghost flex-1 justify-center text-emerald-600">增加</button>
        <button class="btn btn-ghost flex-1 justify-center text-amber-600">减少</button><button class="btn btn-ghost flex-1 justify-center">转移</button></div>
      <p class="text-[11px] text-slate-400 mt-3"><i class="fas fa-circle-info"></i> 所有调整必填原因,全程留痕审计</p></div>
    <div class="panel p-5 lg:col-span-2"><div class="font-semibold text-slate-800 mb-3">调整历史(审计留痕)</div>
      <div class="table-wrap"><table class="dtable"><thead><tr><th>日期</th><th>类型</th><th>金额</th><th>原因</th><th>操作人</th></tr></thead>
        <tbody>${m.history.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div></div>`;
}

function familyView(m) {
  return `<div class="panel p-5 max-w-2xl"><div class="font-semibold text-slate-800 mb-3">家属档案</div>
    ${m.members.map(mem => `<div class="flex items-center gap-3 py-3 border-b border-slate-50 last:border-0">
      <div class="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-400"><i class="fas fa-user"></i></div>
      <div class="flex-1"><div class="text-sm font-medium text-slate-700">${mem.name}</div><div class="text-xs text-slate-400">${mem.relation}</div></div>
      <span class="badge b-info">可关联报销</span></div>`).join('')}
    <button class="btn btn-ai mt-4 justify-center" onclick="openAI('ClaimMate','登记我的家属信息')"><i class="fas fa-robot"></i> 对话式登记家属</button></div>`;
}

function moduleAction(action, title) {
  if (action.includes('AI') || action.includes('对话') || action.includes('智能') || action.includes('NL2SQL') || action.includes('批量') || action.includes('跑批'))
    openAI(null, action + ' · ' + title);
  else alert(`「${action}」演示功能 · 实际系统将打开 ${title} 的操作表单`);
}
window.moduleAction = moduleAction;

// ════════ 东南亚多国合规中心 ════════
async function renderCompliance() {
  const d = await fetch('/api/compliance').then(r => r.json());
  const cards = Object.entries(d.countries).map(([code, c]) => `
    <div class="country-card" onclick="showCountry('${code}')">
      <div class="flex items-center gap-2 mb-3"><span class="text-3xl">${c.flag}</span>
        <div><div class="font-semibold text-slate-800">${S.lang === 'en' ? c.name_en : c.name}</div><div class="text-xs text-slate-400">${S.lang === 'en' ? c.name : c.name_en} · ${c.currency}</div></div></div>
      <div class="space-y-1.5 text-sm">
        <div class="flex justify-between"><span class="text-slate-400">${t('compliance.tax_type')}</span><b class="text-slate-700">${c.tax.name}</b></div>
        <div class="flex justify-between"><span class="text-slate-400">${t('compliance.tax_rate')}</span><span class="badge b-info">${c.tax.rate}</span></div>
        <div class="flex justify-between"><span class="text-slate-400">${t('compliance.accounting_std')}</span><span class="text-slate-600 text-xs">${c.accounting.standard.split(' ')[0]}</span></div>
      </div>
      <div class="text-xs text-teal-500 mt-3"><i class="fas fa-arrow-right"></i> ${t('compliance.view_full')}</div>
    </div>`).join('');
  $('#view').innerHTML = `
    <div class="mb-5"><h1 class="page-title"><i class="fas fa-earth-asia text-cyan-500"></i> ${t('compliance.title')}</h1>
      <p class="text-sm text-slate-400 mt-1">${t('compliance.subtitle')}</p></div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">${cards}</div>`;
}
async function showCountry(code) {
  const c = await fetch(`/api/compliance?country=${code}`).then(r => r.json());
  popover(`
    <div class="px-4 py-3 border-b border-slate-100"><div class="flex items-center gap-2"><span class="text-2xl">${c.flag}</span>
      <div><div class="font-bold text-slate-800">${S.lang === 'en' ? c.name_en : c.name} ${t('compliance.system_suffix')}</div><div class="text-xs text-slate-400">${S.lang === 'en' ? c.name : c.name_en}</div></div></div></div>
    <div class="p-4 space-y-3 text-sm">
      <div><div class="text-xs text-slate-400 mb-1"><i class="fas fa-percent text-pink-400"></i> ${t('compliance.tax_system')}</div>
        <div class="bg-slate-50 rounded-lg p-3"><b>${c.tax.name}</b> · 税率 ${c.tax.rate}<br><span class="text-slate-500 text-xs">${c.tax.authority} · ${c.tax.filing}</span></div></div>
      <div><div class="text-xs text-slate-400 mb-1"><i class="fas fa-receipt text-teal-500"></i> ${t('compliance.claim_rules')}</div>
        <ul class="bg-slate-50 rounded-lg p-3 text-xs text-slate-600 space-y-1">${c.claim_rules.map(r => `<li>• ${r}</li>`).join('')}</ul></div>
      <div><div class="text-xs text-slate-400 mb-1"><i class="fas fa-book text-amber-400"></i> ${t('compliance.accounting_system')}</div>
        <div class="bg-slate-50 rounded-lg p-3 text-xs text-slate-600">${t('compliance.standard')}:${c.accounting.standard}<br>${t('compliance.fiscal')}:${c.accounting.fiscal}<br>${t('compliance.elements')}:${c.accounting.elements.join(' / ')}</div></div>
    </div>`, { center: true, wide: true });
}
window.showCountry = showCountry;

// ════════ 切换器(集团/公司/角色/语言) ════════
function bindGlobal() {
  $('#company-switch').onclick = e => showCompanyPop(e);
  $('#role-switch').onclick = e => showRolePop(e);
  $('#lang-switch').onclick = e => showLangPop(e);
  $('#global-btn').onclick = () => go('global');
  $('#ai-toggle').onclick = () => toggleAI(true);
  $('#ai-close').onclick = () => toggleAI(false);
  $('#ai-mask').onclick = () => toggleAI(false);
  $('#menu-toggle').onclick = () => openMobileSidebar();
  $('#sidebar-mask').onclick = () => closeMobileSidebar();
  $('#popover-mask').onclick = closePopover;
  $('#ai-send').onclick = sendAI;
  $('#ai-input').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendAI(); } });
  $('#ai-input').addEventListener('input', e => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px'; });
}

function showCompanyPop(e) {
  let html = '';
  S.groups.forEach(g => {
    html += `<div class="pop-head">${g.name}</div>`;
    g.companies.forEach(c => {
      html += `<div class="pop-item ${c.id === S.company.id ? 'active' : ''}" onclick="switchCompany('${g.id}','${c.id}')">
        <span>${c.flag}</span><span class="flex-1">${c.name}</span><span class="text-xs text-slate-400">${c.currency} · ${c.employees}人</span></div>`;
    });
  });
  popover(html, { anchor: e.currentTarget });
}
function switchCompany(gid, cid) {
  S.group = S.groups.find(g => g.id === gid);
  S.company = S.group.companies.find(c => c.id === cid);
  renderTopbar(); closePopover(); go(S.currentNav);
}
window.switchCompany = switchCompany;

function showRolePop(e) {
  const html = `<div class="pop-head">${t('role.switch_title')}</div>` + S.roles.map(r =>
    `<div class="pop-item ${r.id === S.role.id ? 'active' : ''}" onclick="switchRole('${r.id}')">
      <span class="w-7 h-7 rounded-full text-white text-xs flex items-center justify-center" style="background:${r.color}"><i class="fas ${r.icon}"></i></span>
      <div class="flex-1"><div>${nameOf(r)}</div><div class="text-[11px] text-slate-400">${descOf(r)}</div></div></div>`).join('');
  popover(html, { anchor: e.currentTarget, wide: true });
}
function switchRole(id) {
  S.role = S.roles.find(r => r.id === id);
  renderTopbar(); renderNav(); closePopover();
  if (!S.role.menus.includes(S.currentNav)) go('dashboard'); else go(S.currentNav);
}
window.switchRole = switchRole;

function showLangPop(e) {
  const html = S.languages.map(l => `<div class="pop-item ${l.code === S.lang ? 'active' : ''}" onclick="switchLang('${l.code}')">
    <span>${l.flag}</span><span class="flex-1">${l.name}</span></div>`).join('');
  popover(html, { anchor: e.currentTarget });
}
function switchLang(code) { setLang(code); $('#lang-flag').textContent = (S.languages.find(l => l.code === code) || {}).flag || '🇨🇳'; closePopover(); }
window.switchLang = switchLang;

// ════════ 通用弹层 ════════
function popover(html, opts = {}) {
  const p = $('#popover'), mask = $('#popover-mask');
  p.innerHTML = html; p.classList.remove('hidden'); mask.classList.remove('hidden');
  p.style.width = opts.wide ? '300px' : '';
  if (opts.center) {
    p.style.left = '50%'; p.style.top = '50%'; p.style.transform = 'translate(-50%,-50%)';
    p.style.width = opts.wide ? 'min(420px,92vw)' : '';
  } else if (opts.anchor) {
    const r = opts.anchor.getBoundingClientRect();
    p.style.transform = 'none';
    let left = Math.min(r.left, window.innerWidth - (opts.wide ? 310 : 220));
    p.style.left = Math.max(8, left) + 'px'; p.style.top = (r.bottom + 6) + 'px';
  }
}
function closePopover() { $('#popover').classList.add('hidden'); $('#popover-mask').classList.add('hidden'); }
window.closePopover = closePopover;

// ════════ 移动端侧栏 ════════
function openMobileSidebar() { $('#sidebar').classList.remove('-translate-x-full'); $('#sidebar-mask').classList.remove('hidden'); }
function closeMobileSidebar() { if (window.innerWidth < 768) { $('#sidebar').classList.add('-translate-x-full'); $('#sidebar-mask').classList.add('hidden'); } }

// ════════ AI 抽屉 ════════
function toggleAI(open) {
  $('#ai-drawer').classList.toggle('translate-x-full', !open);
  $('#ai-mask').classList.toggle('hidden', !open);
  if (open && !$('#ai-messages').dataset.init) { selectAgent(S.currentAgent); $('#ai-messages').dataset.init = '1'; }
}
function openAI(agentId, presetMsg) {
  toggleAI(true);
  if (agentId) { const a = S.agents.find(x => x.id === agentId); if (a) selectAgent(a); }
  if (presetMsg) { $('#ai-input').value = presetMsg; setTimeout(sendAI, 300); }
}
window.openAI = openAI; window.toggleAI = toggleAI;

function renderAgentTabs() {
  $('#agent-tabs').innerHTML = S.agents.map(a =>
    `<div class="agent-tab" data-aid="${a.id}" onclick="selectAgentById('${a.id}')"><span class="emoji">${a.emoji}</span><span class="nm">${a.name}</span></div>`).join('');
}
function selectAgentById(id) { selectAgent(S.agents.find(a => a.id === id)); }
window.selectAgentById = selectAgentById;
function selectAgent(a) {
  S.currentAgent = a;
  $$('#agent-tabs .agent-tab').forEach(t => t.classList.toggle('active', t.dataset.aid === a.id));
  const samples = (S.lang === 'en' && a.samples_en) ? a.samples_en : a.samples;
  $('#ai-samples').innerHTML = samples.map(s => `<span class="sample-chip" onclick="quickAI(this.textContent)">${s}</span>`).join('');
  addAIMsg(`${a.emoji} ${t('ai.hello')} **${nameOf(a)}**。${descOf(a)}。`, false);
}
function quickAI(t) { $('#ai-input').value = t; sendAI(); }
window.quickAI = quickAI;

function addUserMsg(t) { $('#ai-messages').insertAdjacentHTML('beforeend', `<div class="msg-user"><div class="bubble">${esc(t)}</div></div>`); aiScroll(); }
function addAIMsg(t, withAvatar = true) {
  const id = 'm' + Date.now();
  $('#ai-messages').insertAdjacentHTML('beforeend',
    `<div class="msg-ai"><span class="text-lg mt-0.5">${S.currentAgent.emoji}</span><div class="flex-1"><div class="bubble" id="${id}">${fmt(t)}</div></div></div>`);
  aiScroll(); return id;
}
let aiBusy = false;
function sendAI() {
  const inp = $('#ai-input'), text = inp.value.trim();
  if (!text || aiBusy) return;
  inp.value = ''; inp.style.height = 'auto'; addUserMsg(text);
  aiBusy = true; $('#ai-send').disabled = true;

  const tid = 'tk' + Date.now();
  $('#ai-messages').insertAdjacentHTML('beforeend',
    `<div class="msg-ai"><span class="text-lg mt-0.5">${S.currentAgent.emoji}</span><div class="flex-1 space-y-2"><div class="think-box" id="${tid}">
      <div class="text-slate-400"><span class="think-dot">●</span> ${t('ai.thinking')}</div></div></div></div>`);
  aiScroll();

  let bubble = null, badge = '';
  const es = new EventSource(`/api/chat/stream?message=${encodeURIComponent(text)}&thread_id=${S.threadId}`);
  es.addEventListener('route', e => {
    const d = JSON.parse(e.data);
    const t = S.agents.find(a => a.id === d.agent); if (t) selectAgentSilent(t);
    badge = `<span class="badge b-info" style="font-size:10px">${d.module}</span>`;
    if (d.needs_human) badge += ` <span class="badge b-high" style="font-size:10px"><i class="fas fa-user-shield"></i> ${d.hil_level}</span>`;
  });
  es.addEventListener('think', e => {
    const d = JSON.parse(e.data);
    $('#' + tid).insertAdjacentHTML('beforeend',
      `<div class="think-step flex items-center gap-2 text-slate-500 py-0.5"><i class="fas fa-check-circle text-emerald-400"></i><b class="text-slate-600">${d.agent}</b>${d.action}${d.detail ? `<span class="text-slate-300 truncate">· ${d.detail}</span>` : ''}</div>`);
    aiScroll();
  });
  es.addEventListener('token', e => {
    if (!bubble) { $('#' + tid).querySelector('.text-slate-400').innerHTML = `<i class="fas fa-check-double text-emerald-400"></i> ${t('ai.think_done')} ${badge}`; bubble = addAIMsg(''); }
    const b = $('#' + bubble); b._raw = (b._raw || '') + JSON.parse(e.data).char; b.innerHTML = fmt(b._raw); b.classList.add('cursor'); aiScroll();
  });
  es.addEventListener('card', e => { renderAICard(JSON.parse(e.data)); aiScroll(); });
  es.addEventListener('done', () => { if (bubble) $('#' + bubble).classList.remove('cursor'); es.close(); aiBusy = false; $('#ai-send').disabled = false; });
  es.onerror = () => { es.close(); aiBusy = false; $('#ai-send').disabled = false; };
}
function selectAgentSilent(a) { S.currentAgent = a; $$('#agent-tabs .agent-tab').forEach(t => t.classList.toggle('active', t.dataset.aid === a.id)); }

function renderAICard(card) {
  const d = card.data; let body = '';
  if (card.type === 'claim' || card.type === 'entitlement')
    body = Object.entries(d).map(([k, v]) => `<div class="flex justify-between py-0.5"><span class="text-slate-400">${k}</span><b>${v}</b></div>`).join('');
  else if (card.type === 'approval') {
    const s = d.summary;
    body = `<div class="flex gap-1.5 mb-2"><span class="badge b-low">低${s['低风险']}</span><span class="badge b-mid">中${s['中风险']}</span><span class="badge b-high">高${s['高风险']}</span></div>` +
      `<table class="dtable" style="font-size:11.5px"><tbody>${d.rows.slice(0, 5).map(r => `<tr><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td>${badgeCell(r[4])}</td></tr>`).join('')}</tbody></table>`;
  } else if (card.type === 'payroll')
    body = d.steps.map(s => `<div class="flex items-center gap-2 py-0.5"><i class="fas fa-check-circle text-emerald-500"></i>${s.step}</div>`).join('') + `<div class="badge b-low mt-2 inline-block">✅ ${d.total} 条全部成功</div>`;
  else if (card.type === 'chart') body = `<div class="chart-box" style="height:160px"><canvas></canvas></div>`;
  else if (card.type === 'table') body = `<table class="dtable" style="font-size:11.5px">${d.headers ? `<thead><tr>${d.headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>` : ''}<tbody>${d.rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  else if (card.type === 'family') body = (d.members || []).map(m => `<div class="py-0.5"><i class="fas fa-user text-slate-300"></i> ${m.relation}: <b>${m.name}</b></div>`).join('');
  else if (card.type === 'report') body = (d.options || []).map(o => `<div class="py-1 text-teal-600"><i class="fas fa-file-export"></i> ${o}</div>`).join('');
  else body = `<pre style="font-size:11px">${esc(JSON.stringify(d))}</pre>`;
  const cid = 'aicard' + Date.now();
  $('#ai-messages').insertAdjacentHTML('beforeend',
    `<div class="msg-ai"><span class="text-lg opacity-0">·</span><div class="ai-card" id="${cid}"><div class="ai-card-head">${card.title}</div><div class="ai-card-body">${body}</div></div></div>`);
  if (card.type === 'chart') new Chart($('#' + cid).querySelector('canvas'), {
    type: 'bar', data: { labels: d.labels, datasets: d.series.map(s => ({ label: s.name, data: s.data, backgroundColor: 'rgba(32,201,151,.75)', borderRadius: 5 })) },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } }, responsive: true, maintainAspectRatio: false }
  });
}
function aiScroll() { const m = $('#ai-messages'); m.scrollTop = m.scrollHeight; }

// ═══════════════════════════════════════════════════════════
//  Paydaes 7 块积木渲染器(Pro 方案 · 数据驱动)
// ═══════════════════════════════════════════════════════════

// 横滚 Tab 群(Tax 家族顶部)
function topTabsBar(m) {
  const act = m.tabs_active ?? 0;
  return `<div class="ptab-bar mb-4">
    ${m.tabs_top.map((t, i) => `<div class="ptab ${i === act ? 'active' : ''}">${t}</div>`).join('')}
  </div>`;
}

// 单个表单字段渲染(支持 ro/dd/date/num/radio/area/map/time/t）
function pField(f) {
  const req = f.req ? '<span class="text-rose-500">*</span>' : '';
  const lbl = `<label class="pf-label">${f.label} ${req}</label>`;
  let ctrl = '';
  const unit = f.unit ? `<span class="pf-unit">${f.unit}</span>` : '';
  if (f.type === 'ro')
    ctrl = `<input class="pf-input pf-ro" value="${esc(f.value)}" disabled>`;
  else if (f.type === 'dd')
    ctrl = `<div class="pf-select">${esc(f.value || (f.opts[0] || ''))}<i class="fas fa-chevron-down text-[10px] text-slate-400"></i></div>`;
  else if (f.type === 'date')
    ctrl = `<div class="pf-input pf-wunit"><span>${esc(f.value)}</span><i class="fas fa-calendar-day text-slate-400"></i></div>`;
  else if (f.type === 'num')
    ctrl = `<div class="pf-input pf-wunit"><span>${esc(f.value)}</span>${unit}</div>`;
  else if (f.type === 'radio')
    ctrl = `<div class="flex gap-2 flex-wrap">${(f.opts || ['Yes', 'No']).map((o, i) =>
      `<label class="pf-radio ${i === 0 ? 'active' : ''}"><span class="pf-dot"></span>${o}</label>`).join('')}</div>`;
  else if (f.type === 'area')
    ctrl = `<div class="pf-area">${esc(f.value) || '<span class="text-slate-300">' + (f.hint || '请输入…') + '</span>'}</div>`;
  else if (f.type === 'time')
    ctrl = `<div class="pf-input pf-wunit"><span>${esc(f.value)}</span><i class="fas fa-clock text-slate-400"></i></div>`;
  else
    ctrl = `<input class="pf-input" value="${esc(f.value)}">`;
  return `<div class="pf-cell">${lbl}${ctrl}${f.hint && f.type !== 'area' ? `<span class="pf-hint">${f.hint}</span>` : ''}</div>`;
}

// 表单字段网格
function pFieldGrid(fields) {
  return `<div class="pf-grid">${fields.map(pField).join('')}</div>`;
}

// 底部 Back / Save Changes 行
function pFooter(saveLabel) {
  return `<div class="flex items-center justify-end gap-3 mt-5 pt-4 border-t border-slate-100">
    <button class="pf-back">${t('common.back')}</button>
    <button class="btn btn-primary">${saveLabel || t('common.save')}</button>
  </div>`;
}

// 分页器 < 1 2 3 >
function pPager(pages = 3, cur = 1) {
  let html = `<div class="ppager"><span><i class="fas fa-angle-left"></i></span>`;
  for (let i = 1; i <= pages; i++) html += `<span class="${i === cur ? 'active' : ''}">${i}</span>`;
  html += `<span><i class="fas fa-angle-right"></i></span></div>`;
  return html;
}

// ① 普通详情页(只读主键 + 表单 + Back/Save）
function pDetailView(m) {
  return `<div class="panel p-5 md:p-6">
    ${pFieldGrid(m.fields || [])}
    ${pFooter()}
  </div>`;
}

// ② Inline Table 行编辑(行尾 ⊕ / 垃圾桶 + 顶部头字段 + 分页）
function pInlineView(m) {
  const head = m.header_fields ? `<div class="mb-5">${pFieldGrid(m.header_fields)}</div>` : '';
  const cols = (m.columns || []).map(c => `<th>${c}</th>`).join('') + `<th class="text-right">${t('common.action')}</th>`;
  const rows = (m.rows || []).map((r, idx) => `<tr>
    ${r.map((c, ci) => `<td>${ci === 0 ? c : `<span class="pf-cellinput">${esc(String(c))}</span>`}</td>`).join('')}
    <td class="text-right whitespace-nowrap">
      <button class="pf-rowbtn add"><i class="fas fa-plus"></i></button>
      <button class="pf-rowbtn del"><i class="fas fa-trash-can"></i></button>
    </td></tr>`).join('');
  return `<div class="panel p-5 md:p-6">
    ${head}
    <div class="table-wrap"><table class="dtable">
      <thead><tr>${cols}</tr></thead><tbody>${rows}</tbody>
    </table></div>
    ${pPager(3, 1)}
    ${pFooter()}
  </div>`;
}

// ③ 列表页(搜索筛选 + Download/+Add 已在 actions + 绿点状态表）
function pListView(m) {
  const filters = (m.filters || []).map(f =>
    `<div class="pf-cell"><label class="pf-label">${f}</label><div class="pf-select text-slate-400">${t('common.all')}<i class="fas fa-chevron-down text-[10px]"></i></div></div>`).join('');
  const cols = (m.columns || []).map(c => `<th>${c}</th>`).join('');
  const rows = (m.rows || []).map(r => `<tr>${r.map((c, ci) =>
    `<td>${ci === 0 ? `<span class="text-teal-600 font-medium cursor-pointer hover:underline">${esc(String(c))}</span>` : badgeCell(c)}</td>`).join('')}</tr>`).join('');
  const filterPanel = filters ? `<div class="panel p-4 mb-4">
    <div class="flex items-end gap-3 flex-wrap">
      <div class="flex-1 grid grid-cols-2 md:grid-cols-3 gap-3">${filters}</div>
      <label class="flex items-center gap-1.5 text-sm text-slate-600 whitespace-nowrap"><span class="pf-check"></span> ${t('common.active_only')}</label>
      <div class="flex gap-2"><button class="pf-back">${t('common.clear')}</button><button class="btn btn-primary"><i class="fas fa-magnifying-glass"></i> ${t('common.search')}</button></div>
    </div></div>` : '';
  return `${filterPanel}
    <div class="panel p-1.5"><div class="table-wrap"><table class="dtable">
      <thead><tr>${cols}</tr></thead><tbody>${rows}</tbody></table></div>
      <div class="px-3 pb-2">${pPager(3, 1)}</div>
    </div>`;
}

// ④ 双栏穿梭框(候选 / 已选 + 箭头）
function pShuttleView(m) {
  const head = m.header_fields ? `<div class="mb-5">${pFieldGrid(m.header_fields)}</div>` : '';
  const list = (items, side) => items.map(it =>
    `<div class="shuttle-item"><span class="pf-check ${side === 'r' ? 'on' : ''}"></span>${esc(it)}</div>`).join('');
  return `<div class="panel p-5 md:p-6">
    ${head}
    <div class="shuttle-wrap">
      <div class="shuttle-col">
        <div class="shuttle-title">${m.shuttle_left_title || '可选项'}</div>
        <div class="shuttle-body">${list(m.left || [], 'l')}</div>
      </div>
      <div class="shuttle-arrows">
        <button class="shuttle-arrow"><i class="fas fa-angle-right"></i></button>
        <button class="shuttle-arrow"><i class="fas fa-angle-left"></i></button>
      </div>
      <div class="shuttle-col">
        <div class="shuttle-title">${m.shuttle_right_title || '已选项'}</div>
        <div class="shuttle-body">${list(m.right || [], 'r')}</div>
      </div>
    </div>
    ${pFooter()}
  </div>`;
}

// ⑤ Formula 公式编辑器
function pFormulaView(m) {
  const head = m.header_fields ? `<div class="mb-5">${pFieldGrid(m.header_fields)}</div>` : '';
  const vars = (m.formula_vars || []).map(v => `<span class="fx-var" onclick="document.getElementById('fx-area')&&0">${v}</span>`).join('');
  return `<div class="panel p-5 md:p-6">
    ${head}
    <div class="flex items-center justify-between mb-2">
      <label class="pf-label mb-0">Eligibility Formula <span class="text-rose-500">*</span></label>
      <button class="btn btn-ai text-xs py-1" onclick="openAI('HRStrategist','把这条假期资格规则翻译成公式')"><i class="fas fa-wand-magic-sparkles"></i> ${S.lang === 'en' ? 'NL→Formula' : '自然语言生成公式'}</button>
    </div>
    <div class="fx-editor" id="fx-area"><pre>${esc(m.formula || "IF(HR.GENDER='M' AND HR.MARITAL='married',\n   ENTITLEMENT.DAYS + 3,\n   ENTITLEMENT.DAYS)")}</pre></div>
    <div class="fx-toolbar">${vars || '<span class="fx-var">HR.GENDER</span><span class="fx-var">HR.MARITAL</span><span class="fx-var">SERVICE.YEARS</span><span class="fx-var">IF()</span><span class="fx-var">AND</span><span class="fx-var">OR</span>'}</div>
    ${pFooter()}
  </div>`;
}

// ⑥ 地图定位框
function pMapView(m) {
  return `<div class="panel p-5 md:p-6">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div>${pFieldGrid(m.fields || [])}</div>
      <div>
        <label class="pf-label">Map <span class="text-rose-500">*</span></label>
        <div class="map-box">
          <div class="map-grid"></div>
          <i class="fas fa-location-dot map-pin"></i>
          <div class="map-radius"></div>
          <div class="map-hint"><i class="fas fa-circle-info"></i> 拖动图钉定位 · 半径 ${m.radius || '500'} 米打卡有效</div>
        </div>
      </div>
    </div>
    ${pFooter()}
  </div>`;
}

// ⑦ Tabset 详情页(内部横向子 Tab）
function pTabsetView(m) {
  const tabs = (m.sub_tabs || []).map((t, i) => `<div class="ptab2 ${i === 0 ? 'active' : ''}">${t}</div>`).join('');
  return `<div class="panel p-5 md:p-6">
    <div class="ptab2-bar">${tabs}</div>
    ${pFieldGrid(m.fields || [])}
    ${pFooter()}
  </div>`;
}

// ═══════════════════════════════════════════════════════════
//  AI 配置后台 —— 基础配置 / 模型管理 / 分发应用
// ═══════════════════════════════════════════════════════════
const AC = { tab: 'basic', providers: [], models: [], bindings: [], presets: {}, agents: [], status: {}, filterProvider: '' };

function tt(k) { return t('aiconf.' + k); }

async function acLoad() {
  const [presetsR, provR, statusR] = await Promise.all([
    fetch('/api/admin/presets').then(r => r.json()),
    fetch('/api/admin/providers').then(r => r.json()),
    fetch('/api/admin/status').then(r => r.json()),
  ]);
  AC.presets = presetsR.presets; AC.agents = presetsR.agents;
  AC.providers = provR.providers; AC.status = statusR;
}

async function renderAIConfig() {
  await acLoad();
  const s = AC.status;
  const ov = [
    [s.providers_total, tt('ov_providers'), 'fa-server', '#3b82f6'],
    [s.providers_active, tt('ov_active'), 'fa-circle-check', '#20c997'],
    [s.models_enabled, tt('ov_models'), 'fa-microchip', '#8b5cf6'],
    [`${s.agents_bound}/${s.agents_total}`, tt('ov_bound'), 'fa-share-nodes', '#f59e0b'],
  ].map(([v, l, ic, c]) => `
    <div class="kpi-card">
      <div class="w-10 h-10 rounded-xl flex items-center justify-center text-white" style="background:${c}"><i class="fas ${ic}"></i></div>
      <div class="mt-2 text-2xl font-bold text-slate-900">${v}</div>
      <div class="text-xs text-slate-400">${l}</div>
    </div>`).join('');
  const tabs = [['basic', tt('tab_basic')], ['model', tt('tab_model')], ['dispatch', tt('tab_dispatch')]]
    .map(([id, lbl]) => `<div class="ptab2 ${AC.tab === id ? 'active' : ''}" onclick="acSwitchTab('${id}')">${lbl}</div>`).join('');
  $('#view').innerHTML = `
    <div class="mb-5">
      <h1 class="page-title"><i class="fas fa-plug-circle-bolt text-teal-500 mr-2"></i>${tt('title')}</h1>
      <p class="text-sm text-slate-400 mt-0.5">${tt('subtitle')}</p>
    </div>
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-5">${ov}</div>
    <div class="panel p-5 md:p-6">
      <div class="ptab2-bar mb-4">${tabs}</div>
      <div id="ac-body"></div>
    </div>`;
  acRenderBody();
}

function acSwitchTab(id) { AC.tab = id; $$('.ptab2').forEach(e => e.classList.toggle('active', e.textContent === ({basic:tt('tab_basic'),model:tt('tab_model'),dispatch:tt('tab_dispatch')})[id])); acRenderBody(); }

async function acRenderBody() {
  const body = $('#ac-body');
  if (AC.tab === 'basic') return acRenderBasic(body);
  if (AC.tab === 'model') return acRenderModels(body);
  if (AC.tab === 'dispatch') return acRenderDispatch(body);
}

// ─────────── ① 基础配置 ───────────
function acStatusBadge(st) {
  const map = { inactive: ['b-info', tt('st_inactive')], verified: ['b-mid', tt('st_verified')],
                active: ['b-low', tt('st_active')], error: ['b-high', tt('st_error')] };
  const [cls, lbl] = map[st] || map.inactive;
  return `<span class="badge ${cls}">${lbl}</span>`;
}

function acRenderBasic(body) {
  const presetOpts = Object.entries(AC.presets).map(([k, v]) =>
    `<option value="${k}">${S.lang === 'en' ? (v.name_en || v.name) : v.name}</option>`).join('');
  const rows = AC.providers.length ? AC.providers.map(p => `
    <div class="panel p-4 mb-3" style="border:1px solid #eef2f7">
      <div class="flex items-center justify-between flex-wrap gap-2">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center"><i class="fas fa-server text-slate-500"></i></div>
          <div>
            <div class="font-semibold text-slate-800">${p.name} ${acStatusBadge(p.status)}</div>
            <div class="text-[11px] text-slate-400">${p.base_url} · ${tt('key_tail')}: ****${p.key_tail || '----'}</div>
            ${p.verify_msg ? `<div class="text-[11px] text-slate-400 mt-0.5"><i class="fas fa-circle-info"></i> ${p.verify_msg}</div>` : ''}
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <button class="btn btn-ghost text-xs py-1.5" onclick="acVerify('${p.id}')"><i class="fas fa-shield-halved"></i> ${tt('verify')}</button>
          ${p.status === 'active'
            ? `<button class="btn btn-ghost text-xs py-1.5" onclick="acActivate('${p.id}',false)"><i class="fas fa-pause"></i> ${tt('deactivate')}</button>`
            : `<button class="btn btn-primary text-xs py-1.5" onclick="acActivate('${p.id}',true)"><i class="fas fa-bolt"></i> ${tt('activate')}</button>`}
          <button class="btn btn-ghost text-xs py-1.5" onclick="acPull('${p.id}')"><i class="fas fa-download"></i> ${tt('pull_models')}</button>
          <button class="btn btn-ghost text-xs py-1.5" style="color:#ef4444" onclick="acDelProvider('${p.id}')"><i class="fas fa-trash"></i></button>
        </div>
      </div>
    </div>`).join('') : `<div class="text-center text-slate-400 py-8 text-sm">${tt('no_provider')}</div>`;
  body.innerHTML = `
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <div class="lg:col-span-2">${rows}</div>
      <div class="panel p-4" style="background:#f8fafc;border:1px solid #eef2f7">
        <div class="font-semibold text-slate-800 mb-3"><i class="fas fa-circle-plus text-teal-500"></i> ${tt('add_provider')}</div>
        <label class="text-xs text-slate-500">${tt('preset')}</label>
        <select id="ac-preset" class="ac-input" onchange="acPresetChange()">
          <option value="">${tt('custom')}</option>${presetOpts}
        </select>
        <label class="text-xs text-slate-500 mt-2 block">${tt('provider_name')}</label>
        <input id="ac-name" class="ac-input" placeholder="DeepSeek / TokenHost ...">
        <label class="text-xs text-slate-500 mt-2 block">${tt('kind')}</label>
        <select id="ac-kind" class="ac-input">
          <option value="openai_compatible">openai_compatible</option>
          <option value="anthropic">anthropic</option>
        </select>
        <label class="text-xs text-slate-500 mt-2 block">${tt('base_url')}</label>
        <input id="ac-base" class="ac-input" placeholder="https://api.xxx.com/v1">
        <label class="text-xs text-slate-500 mt-2 block">${tt('api_key')}</label>
        <input id="ac-key" type="password" class="ac-input" placeholder="${tt('api_key_ph')}">
        <button class="btn btn-primary w-full mt-3" onclick="acSubmitProvider()"><i class="fas fa-floppy-disk"></i> ${tt('submit')}</button>
      </div>
    </div>`;
}

function acPresetChange() {
  const k = $('#ac-preset').value;
  if (k && AC.presets[k]) {
    $('#ac-name').value = S.lang === 'en' ? (AC.presets[k].name_en || AC.presets[k].name) : AC.presets[k].name;
    $('#ac-kind').value = AC.presets[k].kind;
    $('#ac-base').value = AC.presets[k].base_url;
  }
}

async function acSubmitProvider() {
  const preset = $('#ac-preset').value;
  const payload = {
    preset, name: $('#ac-name').value.trim(), kind: $('#ac-kind').value,
    base_url: $('#ac-base').value.trim(), api_key: $('#ac-key').value.trim(),
  };
  if (!preset && !payload.id && !payload.name) { acToast('请填平台名称或选择预设', 'err'); return; }
  if (!preset) payload.id = payload.name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  await fetch('/api/admin/providers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).then(r => r.json());
  acToast(tt('submit') + ' ✅'); renderAIConfig();
}

async function acVerify(pid) {
  acToast(tt('verifying'));
  const r = await fetch(`/api/admin/providers/${pid}/verify`, { method: 'POST' }).then(r => r.json());
  acToast(r.verify.ok ? `${tt('verify_ok')} ${r.verify.models_pulled || 0} models` : r.verify.msg, r.verify.ok ? 'ok' : 'err');
  renderAIConfig();
}
async function acActivate(pid, on) {
  const r = await fetch(`/api/admin/providers/${pid}/activate?on=${on}`, { method: 'POST' }).then(r => r.json());
  if (r.error) acToast(r.error, 'err'); else acToast('✅'); renderAIConfig();
}
async function acPull(pid) {
  acToast(tt('pulling'));
  const r = await fetch(`/api/admin/providers/${pid}/models/pull`, { method: 'POST' }).then(r => r.json());
  acToast(r.error ? r.error : `${r.count} models`, r.error ? 'err' : 'ok');
  AC.tab = 'model'; AC.filterProvider = pid; renderAIConfig();
}
async function acDelProvider(pid) {
  if (!confirm(tt('confirm_del'))) return;
  await fetch(`/api/admin/providers/${pid}`, { method: 'DELETE' });
  acToast('🗑️'); renderAIConfig();
}

// ─────────── ② 模型管理 ───────────
async function acRenderModels(body) {
  const data = await fetch('/api/admin/models').then(r => r.json());
  AC.models = data.models;
  const provFilter = `<select class="ac-input" style="max-width:240px" onchange="acFilterModels(this.value)">
      <option value="">${tt('all_providers')}</option>
      ${AC.providers.map(p => `<option value="${p.id}" ${AC.filterProvider === p.id ? 'selected' : ''}>${p.name}</option>`).join('')}
    </select>`;
  let list = AC.models;
  if (AC.filterProvider) list = list.filter(m => m.provider_id === AC.filterProvider);
  const capLabel = c => (c || '').split(',').map(x => ({ chat: tt('cap_chat'), vision: tt('cap_vision'), reasoning: tt('cap_reasoning') }[x.trim()] || x.trim())).join(' · ');
  const rows = list.length ? list.map(m => `
    <div class="flex items-center gap-3 py-2.5 px-3 border-b border-slate-50 last:border-0">
      <span class="text-xs text-slate-400 w-24 shrink-0">${m.provider_id}</span>
      <span class="flex-1 text-sm font-medium text-slate-700">${m.label || m.model_id}<span class="text-[11px] text-slate-400 ml-2">${m.model_id}</span></span>
      <span class="badge b-info">${capLabel(m.capability)}</span>
      <label class="ac-switch">
        <input type="checkbox" ${m.enabled ? 'checked' : ''} onchange="acToggleModel(${m.id}, this.checked)">
        <span class="ac-slider"></span>
      </label>
      <span class="text-[11px] w-14 text-right ${m.enabled ? 'text-teal-500' : 'text-slate-300'}">${m.enabled ? tt('enabled') : tt('disabled')}</span>
    </div>`).join('') : `<div class="text-center text-slate-400 py-8 text-sm">${tt('no_models')}</div>`;
  body.innerHTML = `
    <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
      <div class="text-sm text-slate-500"><i class="fas fa-microchip text-teal-500"></i> ${tt('recognize')}</div>
      ${provFilter}
    </div>
    <div class="panel" style="border:1px solid #eef2f7">${rows}</div>`;
}
function acFilterModels(pid) { AC.filterProvider = pid; acRenderModels($('#ac-body')); }
async function acToggleModel(pk, on) {
  await fetch('/api/admin/models/toggle', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model_pk: pk, enabled: on }) });
  acToast(on ? tt('enabled') + ' ✅' : tt('disabled')); acRenderModels($('#ac-body'));
  fetch('/api/admin/status').then(r => r.json()).then(s => { AC.status = s; });
}

// ─────────── ③ 分发应用 ───────────
async function acRenderDispatch(body) {
  const [bData, mData] = await Promise.all([
    fetch('/api/admin/bindings').then(r => r.json()),
    fetch('/api/admin/models?enabled_only=true').then(r => r.json()),
  ]);
  AC.bindings = bData.bindings; const enabledModels = mData.models;
  const bmap = {}; AC.bindings.forEach(b => bmap[b.agent_id] = b);
  const agentName = a => S.lang === 'en' ? (a.name_en || a.name) : a.name;
  const agentDesc = a => S.lang === 'en' ? (a.desc_en || a.desc) : a.desc;
  const row = a => {
    const b = bmap[a.id] || {};
    const provOpts = AC.providers.filter(p => p.status === 'active').map(p =>
      `<option value="${p.id}" ${b.provider_id === p.id ? 'selected' : ''}>${p.name}</option>`).join('');
    const modelsFor = (b.provider_id || '');
    const modelOpts = enabledModels.filter(m => !modelsFor || m.provider_id === modelsFor).map(m =>
      `<option value="${m.provider_id}|${m.model_id}" ${(b.provider_id === m.provider_id && b.model_id === m.model_id) ? 'selected' : ''}>${m.label || m.model_id}</option>`).join('');
    const bound = b.provider_id && b.model_id;
    return `
    <div class="flex items-center gap-3 py-3 px-3 border-b border-slate-50 last:border-0 flex-wrap" data-agent="${a.id}">
      <span class="text-xl w-7 text-center">${a.emoji}</span>
      <div class="flex-1 min-w-[140px]">
        <div class="text-sm font-semibold text-slate-700">${agentName(a)} ${bound ? `<span class="badge b-low ml-1">${tt('bound_ok')}</span>` : `<span class="badge b-info ml-1">${tt('unbound')}</span>`}</div>
        <div class="text-[11px] text-slate-400">${agentDesc(a)}</div>
      </div>
      <select class="ac-input" style="max-width:180px" onchange="acBindProvChange('${a.id}', this.value)">
        <option value="">${tt('select_provider')}</option>${provOpts}
      </select>
      <select class="ac-input ac-model-sel" style="max-width:220px" data-agent="${a.id}">
        <option value="">${tt('select_model')}</option>${modelOpts}
      </select>
      <button class="btn btn-primary text-xs py-1.5" onclick="acSaveBinding('${a.id}')"><i class="fas fa-floppy-disk"></i> ${tt('save_binding')}</button>
    </div>`;
  };
  const core = AC.agents.filter(a => a.scope === 'core').map(row).join('');
  const main = AC.agents.filter(a => a.scope === 'main').map(row).join('');
  body.innerHTML = `
    <div class="text-sm text-slate-500 mb-4"><i class="fas fa-circle-info text-teal-500"></i> ${tt('dispatch_hint')}</div>
    <div class="text-xs font-semibold text-slate-400 uppercase mb-1 mt-2">${tt('core_agents')}</div>
    <div class="panel mb-4" style="border:1px solid #eef2f7">${core}</div>
    <div class="text-xs font-semibold text-slate-400 uppercase mb-1">${tt('main_agents')}</div>
    <div class="panel" style="border:1px solid #eef2f7">${main}</div>`;
}
function acBindProvChange(agentId, pid) {
  // 切换平台时重新过滤模型下拉
  fetch('/api/admin/models?enabled_only=true').then(r => r.json()).then(d => {
    const sel = document.querySelector(`.ac-model-sel[data-agent="${agentId}"]`);
    const opts = d.models.filter(m => !pid || m.provider_id === pid).map(m =>
      `<option value="${m.provider_id}|${m.model_id}">${m.label || m.model_id}</option>`).join('');
    sel.innerHTML = `<option value="">${tt('select_model')}</option>${opts}`;
  });
}
async function acSaveBinding(agentId) {
  const sel = document.querySelector(`.ac-model-sel[data-agent="${agentId}"]`);
  const val = sel.value;
  let provider_id = null, model_id = null;
  if (val) { [provider_id, model_id] = val.split('|'); }
  await fetch('/api/admin/bindings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ agent_id: agentId, provider_id, model_id }) });
  acToast(model_id ? tt('bound_ok') : tt('unbound')); acRenderDispatch($('#ac-body'));
  fetch('/api/admin/status').then(r => r.json()).then(s => { AC.status = s; });
}

// 轻量 toast
function acToast(msg, type) {
  let el = $('#ac-toast');
  if (!el) { el = document.createElement('div'); el.id = 'ac-toast'; document.body.appendChild(el); }
  el.className = 'ac-toast ' + (type === 'err' ? 'ac-toast-err' : 'ac-toast-ok');
  el.textContent = msg; el.style.opacity = '1';
  clearTimeout(el._t); el._t = setTimeout(() => { el.style.opacity = '0'; }, 2600);
}

window.acSwitchTab = acSwitchTab; window.acPresetChange = acPresetChange;
window.acSubmitProvider = acSubmitProvider; window.acVerify = acVerify;
window.acActivate = acActivate; window.acPull = acPull; window.acDelProvider = acDelProvider;
window.acFilterModels = acFilterModels; window.acToggleModel = acToggleModel;
window.acBindProvChange = acBindProvChange; window.acSaveBinding = acSaveBinding;
