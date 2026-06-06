// ═══════════ Paydaes ClaimGPT 集团版 前端 ═══════════
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const fmt = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');

const S = {           // 全局状态
  groups: [], roles: [], languages: [], nav: [], agents: [],
  group: null, company: null, role: null, lang: 'zh',
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
  renderTopbar(); renderNav(); renderAgentTabs();
  go('dashboard');
  bindGlobal();
}

// ════════ 顶部栏渲染 ════════
function renderTopbar() {
  $('#group-logo').textContent = S.group.logo;
  $('#group-logo').style.background = S.group.color;
  $('#group-name').textContent = S.group.name;
  $('#company-flag').textContent = S.company.flag;
  $('#company-name').textContent = S.company.name;
  $('#role-name').textContent = S.role.name;
  $('#role-avatar').innerHTML = `<i class="fas ${S.role.icon}"></i>`;
  $('#role-avatar').style.background = S.role.color;
  $('#lang-flag').textContent = (S.languages.find(l => l.code === S.lang) || {}).flag || '🇨🇳';
}

// ════════ 左侧导航树(按角色过滤) ════════
function renderNav() {
  const allow = S.role.menus;
  const html = S.nav.filter(n => allow.includes(n.id)).map(n => {
    if (n.type === 'page') {
      return `<div class="nav-item ${S.currentNav === n.id ? 'active' : ''}" data-nav="${n.id}">
        <i class="fas ${n.icon}"></i><span>${n.name}</span>
        ${n.badge ? `<span class="b-new ml-auto">${n.badge}</span>` : ''}</div>`;
    }
    const kids = n.children.map(c =>
      `<div class="nav-sub ${S.currentNav === c.id ? 'active' : ''}" data-nav="${c.id}" data-module="${c.module}">${c.name}</div>`).join('');
    const open = n.children.some(c => c.id === S.currentNav);
    return `<div data-group="${n.id}">
      <div class="nav-group-title" onclick="toggleGroup('${n.id}')">
        <i class="fas ${n.icon}"></i><span>${n.name}</span>
        <i class="fas fa-chevron-${open ? 'down' : 'right'} text-[10px] text-slate-300 ml-auto group-arrow"></i>
      </div>
      <div class="nav-children ${open ? '' : 'hidden'}" data-children="${n.id}">${kids}</div>
    </div>`;
  }).join('');
  $('#nav-tree').innerHTML = html;
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
        <span class="badge ${k.trend.includes('+') ? 'b-low' : 'b-info'}">${k.trend}</span>
      </div>
      <div class="mt-3 text-2xl font-bold text-slate-900">${k.value}<span class="text-sm font-normal text-slate-400 ml-1">${k.unit}</span></div>
      <div class="text-xs text-slate-400 mt-0.5">${k.label}</div>
    </div>`).join('');
  const todos = d.todos.map(t => `
    <div class="flex items-center gap-3 py-2.5 border-b border-slate-50 last:border-0">
      <span class="w-1.5 h-1.5 rounded-full" style="background:${t.level === 'high' ? '#ef4444' : '#f59e0b'}"></span>
      <span class="flex-1 text-sm text-slate-700">${t.title}</span>
      <span class="badge b-info">${t.type}</span>
      <button class="btn btn-ai text-xs py-1" onclick="openAI('${t.agent}','${t.title}')"><i class="fas fa-robot"></i> 交给AI</button>
    </div>`).join('');
  $('#view').innerHTML = `
    <div class="flex items-center justify-between mb-5 flex-wrap gap-2">
      <div><h1 class="page-title">工作台</h1><p class="text-sm text-slate-400 mt-0.5">${S.company.flag} ${S.company.name} · ${S.group.name}</p></div>
      <button class="btn btn-ai" onclick="toggleAI(true)"><i class="fas fa-robot"></i> 唤起 AI 智能体</button>
    </div>
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-5">${kpi}</div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="panel p-5 lg:col-span-2">
        <div class="font-semibold text-slate-800 mb-3">报销趋势分析</div>
        <div class="chart-box"><canvas id="dash-chart"></canvas></div>
      </div>
      <div class="panel p-5">
        <div class="font-semibold text-slate-800 mb-1">待办事项 <span class="badge b-high ml-1">${d.todos.length}</span></div>
        <div>${todos}</div>
      </div>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mt-5">
      ${S.agents.map(a => `<div class="panel p-4 cursor-pointer hover:shadow-md transition" onclick="openAI('${a.id}','')">
        <div class="text-2xl mb-1">${a.emoji}</div>
        <div class="font-semibold text-sm text-slate-800">${a.name}</div>
        <div class="text-[11px] text-slate-400 mt-1 leading-snug">${a.desc}</div>
        <div class="text-[10px] text-teal-500 mt-2">${a.modules.length} 个模块</div>
      </div>`).join('')}
    </div>`;
  new Chart($('#dash-chart'), {
    type: 'line',
    data: { labels: d.chart.labels, datasets: d.chart.series.map((s, i) => ({
      label: s.name, data: s.data, borderColor: i ? '#ec4899' : '#20c997',
      backgroundColor: i ? 'rgba(236,72,153,.1)' : 'rgba(32,201,151,.12)', fill: true, tension: .4 })) },
    options: { plugins: { legend: { labels: { font: { size: 11 } } } }, scales: { y: { beginAtZero: true } }, responsive: true, maintainAspectRatio: false }
  });
}

// ════════ 18 模块工作区 ════════
async function renderModule(navId) {
  const m = await fetch(`/api/module/${navId}?company=${S.company.id}`).then(r => r.json());
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
  else body = tableView(m);

  $('#view').innerHTML = `
    <div class="flex items-start justify-between mb-4 flex-wrap gap-3">
      <div><h1 class="page-title">${m.title}</h1><p class="text-sm text-slate-400 mt-1">${m.desc || ''}</p></div>
      <div class="flex gap-2 flex-wrap">${actions}</div>
    </div>${body}`;
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
  if (s === '高') return `<span class="badge b-high">高</span>`;
  if (s === '中') return `<span class="badge b-mid">中</span>`;
  if (s === '低') return `<span class="badge b-low">低</span>`;
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
        <div><div class="font-semibold text-slate-800">${c.name}</div><div class="text-xs text-slate-400">${c.name_en} · ${c.currency}</div></div></div>
      <div class="space-y-1.5 text-sm">
        <div class="flex justify-between"><span class="text-slate-400">税种</span><b class="text-slate-700">${c.tax.name}</b></div>
        <div class="flex justify-between"><span class="text-slate-400">税率</span><span class="badge b-info">${c.tax.rate}</span></div>
        <div class="flex justify-between"><span class="text-slate-400">会计准则</span><span class="text-slate-600 text-xs">${c.accounting.standard.split(' ')[0]}</span></div>
      </div>
      <div class="text-xs text-teal-500 mt-3"><i class="fas fa-arrow-right"></i> 查看完整合规体系</div>
    </div>`).join('');
  $('#view').innerHTML = `
    <div class="mb-5"><h1 class="page-title"><i class="fas fa-earth-asia text-cyan-500"></i> 全球合规中心</h1>
      <p class="text-sm text-slate-400 mt-1">调用全球各国税收、报销、做账体系 · 切换公司自动适配本地合规</p></div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">${cards}</div>`;
}
async function showCountry(code) {
  const c = await fetch(`/api/compliance?country=${code}`).then(r => r.json());
  popover(`
    <div class="px-4 py-3 border-b border-slate-100"><div class="flex items-center gap-2"><span class="text-2xl">${c.flag}</span>
      <div><div class="font-bold text-slate-800">${c.name} 合规体系</div><div class="text-xs text-slate-400">${c.name_en}</div></div></div></div>
    <div class="p-4 space-y-3 text-sm">
      <div><div class="text-xs text-slate-400 mb-1"><i class="fas fa-percent text-pink-400"></i> 税收体系</div>
        <div class="bg-slate-50 rounded-lg p-3"><b>${c.tax.name}</b> · 税率 ${c.tax.rate}<br><span class="text-slate-500 text-xs">${c.tax.authority} · ${c.tax.filing}</span></div></div>
      <div><div class="text-xs text-slate-400 mb-1"><i class="fas fa-receipt text-teal-500"></i> 报销规则</div>
        <ul class="bg-slate-50 rounded-lg p-3 text-xs text-slate-600 space-y-1">${c.claim_rules.map(r => `<li>• ${r}</li>`).join('')}</ul></div>
      <div><div class="text-xs text-slate-400 mb-1"><i class="fas fa-book text-amber-400"></i> 做账体系</div>
        <div class="bg-slate-50 rounded-lg p-3 text-xs text-slate-600">准则:${c.accounting.standard}<br>财年:${c.accounting.fiscal}<br>科目:${c.accounting.elements.join(' / ')}</div></div>
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
  const html = `<div class="pop-head">切换角色(体验不同权限)</div>` + S.roles.map(r =>
    `<div class="pop-item ${r.id === S.role.id ? 'active' : ''}" onclick="switchRole('${r.id}')">
      <span class="w-7 h-7 rounded-full text-white text-xs flex items-center justify-center" style="background:${r.color}"><i class="fas ${r.icon}"></i></span>
      <div class="flex-1"><div>${r.name}</div><div class="text-[11px] text-slate-400">${r.desc}</div></div></div>`).join('');
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
function switchLang(code) { S.lang = code; renderTopbar(); closePopover(); }
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
  $('#ai-samples').innerHTML = a.samples.map(s => `<span class="sample-chip" onclick="quickAI('${s}')">${s}</span>`).join('');
  addAIMsg(`${a.emoji} 你好,我是**${a.name}**。${a.desc}。`, false);
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
      <div class="text-slate-400"><span class="think-dot">●</span> 智能体团队协作思考中…</div></div></div></div>`);
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
    if (!bubble) { $('#' + tid).querySelector('.text-slate-400').innerHTML = `<i class="fas fa-check-double text-emerald-400"></i> 思考完成 ${badge}`; bubble = addAIMsg(''); }
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
