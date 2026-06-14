// ═══════════ Paydaes ClaimGPT 集团版 前端 ═══════════
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const fmt = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');

// 统一 API 辅助:GET 直接传 url;POST/PUT/DELETE 传 body 对象(自动带 JSON 头并解析)
async function api(url, body, method) {
  const opt = { method: method || (body ? 'POST' : 'GET') };
  if (body) { opt.headers = { 'Content-Type': 'application/json' }; opt.body = JSON.stringify(body); }
  return (await fetch(url, opt)).json();
}
// 触发文件下载(供导出/模板等复用)
function dl(url, name) {
  const a = document.createElement('a');
  a.href = url; a.download = name || '';
  document.body.appendChild(a); a.click(); a.remove();
}

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
  initCorePanel();                // AI 中枢状态面板(科幻活体仪表盘)
}

// ════════ AI 中枢状态面板 —— 13 Agent 灯阵 + 18 模块点阵 + 运维心跳 ════════
const CORE_SUB = ['Intent', 'Policy', 'Risk', 'Extract', 'Workflow', 'Entitle', 'Conv', 'Audit'];
function initCorePanel() {
  const ag = $('#core-agent-grid');
  if (!ag) return;
  // 5 主 Agent(圆形·绿) + 8 子 Agent(方形·青)
  const mains = (S.agents || []).slice(0, 5);
  let html = '';
  mains.forEach((a, i) => {
    html += `<span class="core-led main on" style="--beat:${(2 + i * 0.3).toFixed(1)}s" title="${nameOf(a)} · ${t('core.tip_active')}">${a.emoji ? '' : '<i class="fas fa-robot"></i>'}</span>`;
  });
  CORE_SUB.forEach((s, i) => {
    html += `<span class="core-led on" style="--beat:${(2.2 + i * 0.22).toFixed(1)}s" title="${s}Agent · ${t('core.tip_active')}"></span>`;
  });
  ag.innerHTML = html;
  // 18 模块点阵
  const mg = $('#core-mod-grid');
  if (mg) {
    let md = '';
    for (let i = 0; i < 18; i++) md += `<span class="core-dot run" style="--d:${(2.4 + (i % 6) * 0.3).toFixed(1)}s"></span>`;
    mg.innerHTML = md;
  }
  startCoreHeartbeat();
}
let _coreTimer = null;
// LED 索引 → telemetry canonical Agent id 映射
// 前 5 = 主 Agent(对齐 S.agents 顺序),后 8 = CORE_SUB → SUB_AGENTS
const CORE_SUB_ID = {
  Intent: 'IntentAgent', Policy: 'PolicyAgent', Risk: 'RiskAgent', Extract: 'ExtractionAgent',
  Workflow: 'WorkflowAgent', Entitle: 'EntitlementAgent', Conv: 'ConversationAgent', Audit: 'AuditAgent',
};
function _coreLedAgentIds() {
  // 返回 LED 索引顺序对应的 canonical id 数组(长度 13)
  const mains = (S.agents || []).slice(0, 5).map(a => a.id);
  while (mains.length < 5) mains.push(null);
  const subs = CORE_SUB.map(s => CORE_SUB_ID[s] || null);
  return mains.concat(subs);
}
let _coreLastSince = {};  // 记录上次各 Agent 的 since_ms,用于"新命中"判定(避免重复爆闪)
function startCoreHeartbeat() {
  if (_coreTimer) clearInterval(_coreTimer);
  const leds = $$('#core-agent-grid .core-led');
  const dots = $$('#core-mod-grid .core-dot');
  const ledIds = _coreLedAgentIds();
  let _idleTick = 0;
  _coreTimer = setInterval(async () => {
    let real = null;
    try {
      const r = await fetch('/api/telemetry');
      if (r.ok) real = await r.json();
    } catch (e) { /* 静默失败:零回归,降级到温和兜底 */ }

    if (real && Array.isArray(real.agents)) {
      // ── 真实数据驱动 ──
      const byId = {};
      real.agents.forEach(a => { byId[a.id] = a; });
      let activeCount = 0;
      real.agents.forEach(a => { if (a.recent) activeCount++; });
      const hasTraffic = activeCount > 0;

      ledIds.forEach((id, i) => {
        const led = leds[i];
        if (!led || !id) return;
        const a = byId[id];
        if (a && a.recent) {
          // 真实命中 → 灯爆闪 + 常亮
          const prev = _coreLastSince[id];
          const fresh = (prev == null) || (a.since_ms != null && a.since_ms < (prev - 200)) || (a.since_ms != null && a.since_ms < 1600);
          led.classList.add('on');
          if (fresh) { led.classList.remove('flash'); void led.offsetWidth; led.classList.add('flash'); }
        } else if (hasTraffic) {
          // 有流量时:未命中的灯暗下去,凸显真实调用路径
          led.classList.remove('on');
        } else {
          // 待机态(无任何流量):全部 LED 保持微亮呼吸,营造「系统在线待命」活体感
          led.classList.add('on');
        }
        if (a) _coreLastSince[id] = a.since_ms;
      });

      // 真实指标
      const lat = $('#core-lat');
      if (lat) lat.textContent = (real.avg_latency_ms != null ? real.avg_latency_ms : '–') + 'ms';
      const tps = $('#core-tps');
      if (tps) tps.textContent = (real.tps != null ? real.tps : 0).toFixed(1);
      const act = $('#core-agent-active');
      if (act) act.textContent = hasTraffic ? activeCount : 13;  // 待机显示满编 13

      // 模块点阵:有真实负载时点亮对应数量「忙碌」点;待机时全部常态运行
      if (dots.length) {
        if (hasTraffic) {
          const busyN = Math.min(dots.length, activeCount * 2);
          dots.forEach((d, i) => d.classList.toggle('busy', i < busyN));
        } else {
          dots.forEach(d => d.classList.remove('busy'));
        }
      }

      // 待机态偶尔来一次温和扫描脉冲,避免死气沉沉
      if (!hasTraffic) {
        _idleTick++;
        if (_idleTick % 2 === 0 && leds.length) {
          const led = leds[Math.floor(Math.random() * leds.length)];
          led.classList.remove('flash'); void led.offsetWidth; led.classList.add('flash');
        }
      } else {
        _idleTick = 0;
      }
    } else {
      // ── 兜底:接口不可用时温和模拟(零回归) ──
      if (leds.length) {
        const led = leds[Math.floor(Math.random() * leds.length)];
        led.classList.remove('flash'); void led.offsetWidth; led.classList.add('flash');
      }
      if (dots.length) {
        const d = dots[Math.floor(Math.random() * dots.length)];
        d.classList.add('busy');
        setTimeout(() => d.classList.remove('busy'), 1100);
      }
    }
  }, 1500);
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
  if ($('#mobile-tabbar')) renderTabbar();
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
  S.curModule = m;                       // 暂存当前模块(供 CRUD 模态框读取字段定义)
  window.__crud = m.crud || null;
  const crudAction = m.crud ? m.crud.action : null;
  const actions = (m.actions || []).map((a, i) => {
    const isAI = a.includes('AI');
    // 该 action 是这个模块的"真新增"动作 → 打开真表单模态框
    const onclick = (crudAction && a === crudAction)
      ? `openCrudModal()` : `moduleAction('${a}','${m.title}')`;
    return `<button class="btn ${isAI ? 'btn-ai' : (i === 0 ? 'btn-primary' : 'btn-ghost')}" onclick="${onclick}">
      ${isAI ? '<i class=\"fas fa-robot\"></i>' : '<i class=\"fas fa-plus\"></i>'} ${a}</button>`;
  }).join('');
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
  // 真功能联动:自助申请/审批/数据表 渲染后实时拉真库
  if (m.layout === 'self_claim') { loadClaimTypes(); refreshClaims('mine'); }
  else if (m.layout === 'approval') refreshClaims('approval');
}

function tableView(m) {
  const hasOps = m.has_record_col;       // 末列是删除句柄(__rec:N / __type:CODE / __seed)
  const cols = m.columns || [];
  const head = cols.map(c => `<th>${c}</th>`).join('') + (hasOps ? `<th class="text-right">${t('crud.ops')}</th>` : '');
  const body = (m.rows || []).map(r => {
    let handle = '', cells = r;
    if (hasOps) { handle = r[r.length - 1]; cells = r.slice(0, -1); }
    let opCell = '';
    if (hasOps) {
      if (handle && handle.startsWith('__rec:')) {
        const rid = handle.slice(6);
        opCell = `<td class="text-right"><button class="btn btn-ghost text-xs py-1 text-rose-500" onclick="deleteRow('rec','${rid}')"><i class="fas fa-trash"></i></button></td>`;
      } else if (handle && handle.startsWith('__type:')) {
        const code = handle.slice(7);
        opCell = `<td class="text-right whitespace-nowrap">
          <button class="btn btn-ghost text-xs py-1 text-teal-600" onclick="editClaimType('${code}')"><i class="fas fa-pen"></i></button>
          <button class="btn btn-ghost text-xs py-1 text-rose-500" onclick="deleteRow('type','${code}')"><i class="fas fa-trash"></i></button></td>`;
      } else {
        opCell = `<td class="text-right"><span class="text-xs text-slate-300">${t('crud.seed')}</span></td>`;
      }
    }
    return `<tr>${cells.map(c => `<td>${badgeCell(c)}</td>`).join('')}${opCell}</tr>`;
  }).join('');
  return `<div class="panel p-1.5"><div class="table-wrap"><table class="dtable">
    <thead><tr>${head}</tr></thead><tbody>${body}</tbody>
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
    <div class="table-wrap" id="approval-box"><table class="dtable">
      <thead><tr>${m.columns.map(c => `<th>${c}</th>`).join('')}<th class="text-right">${t('crud.ops')}</th></tr></thead>
      <tbody>${m.rows.map(r => {
        const cid = r[0];
        return `<tr>${r.map(c => `<td>${badgeCell(c)}</td>`).join('')}
        <td class="text-right whitespace-nowrap">
          <button class="btn btn-ghost text-xs py-1 text-emerald-600" onclick="decideClaim('${cid}','approved')"><i class="fas fa-check"></i> ${t('crud.approve')}</button>
          <button class="btn btn-ghost text-xs py-1 text-amber-500" onclick="decideClaim('${cid}','returned')"><i class="fas fa-rotate-left"></i> ${t('wf.return')}</button>
          <button class="btn btn-ghost text-xs py-1 text-rose-500" onclick="decideClaim('${cid}','rejected')"><i class="fas fa-xmark"></i> ${t('crud.reject')}</button>
        </td></tr>`; }).join('')}</tbody>
    </table></div>
    <p class="text-[11px] text-slate-400 mt-2" id="approval-feedback"></p>
    <div class="flex gap-2 mt-4 flex-wrap">
      <button class="btn btn-primary" style="background:#10b981" onclick="batchApprove()"><i class="fas fa-bolt"></i> ${t('crud.batch_low')}</button>
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
  // 导出权限:hr_admin / payroll / finance / sys_admin
  const canExport = S.role && ['hr_admin', 'payroll', 'finance', 'sys_admin'].includes(S.role.id);
  const exportBtns = canExport ? `
      <div class="flex gap-2 mt-3">
        <button class="btn btn-ghost flex-1 justify-center text-emerald-600" onclick="exportReport('excel')"><i class="fas fa-file-excel"></i> ${t('report.export_excel')}</button>
        <button class="btn btn-ghost flex-1 justify-center text-orange-600" onclick="exportReport('ppt')"><i class="fas fa-file-powerpoint"></i> ${t('report.export_ppt')}</button>
      </div>
      <p class="text-[11px] text-slate-400 mt-2" id="rpt-export-fb"></p>` : `
      <p class="text-[11px] text-slate-400 mt-3"><i class="fas fa-lock"></i> ${t('report.no_perm')}</p>`;
  return `<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="panel p-5 lg:col-span-2"><div class="font-semibold text-slate-800 mb-3">${m.title}</div><div class="chart-box"><canvas id="rpt-chart"></canvas></div></div>
    <div class="panel p-5"><div class="font-semibold text-slate-800 mb-2"><i class="fas fa-lightbulb text-amber-400"></i> ${t('report.ai_insight')}</div>
      <p class="text-sm text-slate-600 leading-relaxed">${m.insight}</p>
      <button class="btn btn-ai w-full mt-4 justify-center" onclick="openAI('InsightOracle','分析${m.title}')"><i class="fas fa-robot"></i> ${t('report.deep_analysis')}</button>
      ${exportBtns}</div>
    ${canExport ? statutoryCard() : ''}</div>`;
}

// 🇲🇾 马来西亚法定合规表格卡片
function statutoryCard() {
  const forms = [
    { id: 'payslip', icon: 'fa-file-invoice-dollar', color: 'emerald' },
    { id: 'epf_borang_a', icon: 'fa-piggy-bank', color: 'blue' },
    { id: 'ea_form', icon: 'fa-file-contract', color: 'orange' },
  ];
  const cards = forms.map(f => `
    <button class="stat-form-btn" onclick="exportStatutory('${f.id}')" id="stat-btn-${f.id}">
      <i class="fas ${f.icon} text-${f.color}-500 text-xl"></i>
      <div class="stat-form-name">${t('report.' + f.id)}</div>
      <div class="stat-form-desc">${t('report.' + f.id + '_d')}</div>
      <i class="fas fa-download stat-form-dl"></i>
      ${f.id === 'ea_form' ? `<span class="ea-pdf-badge" onclick="event.stopPropagation(); exportStatutory('ea_form','pdf')" title="${t('report.ea_pdf')}"><i class="fas fa-file-pdf"></i> ${t('report.ea_pdf')}</span>` : ''}
    </button>`).join('');
  return `<div class="panel p-5 lg:col-span-3 mt-1">
    <div class="font-semibold text-slate-800 mb-1 flex items-center gap-2">
      <span data-i18n="report.statutory_title">${t('report.statutory_title')}</span></div>
    <p class="text-xs text-slate-500 mb-3" data-i18n="report.statutory_desc">${t('report.statutory_desc')}</p>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">${cards}</div>
    <p class="text-[11px] text-slate-400 mt-3"><i class="fas fa-circle-info"></i> <span data-i18n="report.statutory_note">${t('report.statutory_note')}</span></p>
    <p class="text-[11px] mt-1" id="stat-export-fb"></p>
    ${importCard()}</div>`;
}

function importCard() {
  return `<div class="import-card mt-4">
    <div class="font-semibold text-slate-800 mb-1 flex items-center gap-2">
      <i class="fas fa-file-import text-indigo-500"></i>
      <span data-i18n="report.import_title">${t('report.import_title')}</span></div>
    <p class="text-xs text-slate-500 mb-3" data-i18n="report.import_desc">${t('report.import_desc')}</p>
    <div class="flex flex-wrap items-center gap-3">
      <button class="import-btn-tpl" onclick="downloadImportTemplate()">
        <i class="fas fa-download"></i> <span data-i18n="report.import_tpl">${t('report.import_tpl')}</span></button>
      <label class="import-btn-up">
        <i class="fas fa-upload"></i> <span data-i18n="report.import_upload">${t('report.import_upload')}</span>
        <input type="file" id="import-file" accept=".xlsx" style="display:none" onchange="uploadRoster(this)">
      </label>
    </div>
    <p class="text-[11px] mt-2" id="import-fb"></p>
    <div id="import-preview"></div></div>`;
}

async function downloadImportTemplate() {
  const fb = document.getElementById('import-fb');
  if (fb) acFlash(fb, t('report.exporting'), false);
  try {
    const r = await api('/api/payroll/import/template?role=' + S.role.id);
    if (r.denied || r.error) { if (fb) acFlash(fb, r.error || t('perm.denied'), true); return; }
    dl(r.download_url, r.filename);
    if (fb) acFlash(fb, `✅ ${r.title} · ${r.filename}`, false);
  } catch (e) { if (fb) acFlash(fb, '下载失败: ' + e.message, true); }
}

async function uploadRoster(input) {
  const fb = document.getElementById('import-fb');
  const pv = document.getElementById('import-preview');
  if (!input.files || !input.files[0]) return;
  const fd = new FormData();
  fd.append('file', input.files[0]);
  fd.append('role', S.role.id);
  if (fb) acFlash(fb, t('report.import_parsing'), false);
  if (pv) pv.innerHTML = '';
  try {
    const r = await fetch('/api/payroll/import/parse', { method: 'POST', body: fd }).then(x => x.json());
    if (r.denied || (r.error && !r.summary)) { if (fb) acFlash(fb, r.error || t('perm.denied'), true); return; }
    const s = r.summary || { data_rows: 0, valid: 0, invalid: 0 };
    const okMsg = r.ok ? `✅ ${t('report.import_ok')}` : `⚠️ ${t('report.import_partial')}`;
    if (fb) acFlash(fb, `${okMsg} — ${t('report.import_rows')}: ${s.data_rows} · ${t('report.import_valid')}: ${s.valid} · ${t('report.import_invalid')}: ${s.invalid}`, !r.ok);
    if (pv) pv.innerHTML = renderImportPreview(r);
  } catch (e) {
    if (fb) acFlash(fb, '解析失败: ' + e.message, true);
  } finally { input.value = ''; }
}

function renderImportPreview(r) {
  let html = '';
  if (r.preview && r.preview.length) {
    const rows = r.preview.map(p => `<tr>
      <td>${p.emp_no}</td><td>${p.name}</td>
      <td class="num">${(p.gross || 0).toLocaleString()}</td>
      <td class="num">${(p.epf_emp || 0).toLocaleString()}</td>
      <td class="num">${(p.pcb || 0).toFixed(2)}</td>
      <td class="num">${(p.zakat || 0).toLocaleString()}</td>
      <td class="num">${(p.net || 0).toLocaleString()}</td></tr>`).join('');
    html += `<div class="import-pv-box"><div class="import-pv-title"><i class="fas fa-circle-check text-emerald-500"></i> ${t('report.import_preview_ok')}</div>
      <table class="import-pv-table"><thead><tr>
        <th>${t('report.import_col_no')}</th><th>${t('report.import_col_name')}</th>
        <th>${t('report.import_col_gross')}</th><th>EPF</th><th>PCB</th><th>Zakat</th><th>${t('report.import_col_net')}</th>
      </tr></thead><tbody>${rows}</tbody></table></div>`;
  }
  if (r.errors && r.errors.length) {
    const errs = r.errors.map(e => `<li><b>${e.emp_no}</b> (${t('report.import_row')} ${e.row}): ${e.errors.join('；')}</li>`).join('');
    html += `<div class="import-pv-box import-pv-err"><div class="import-pv-title"><i class="fas fa-triangle-exclamation text-rose-500"></i> ${t('report.import_preview_err')}</div>
      <ul class="import-err-list">${errs}</ul></div>`;
  }
  return html;
}
window.downloadImportTemplate = downloadImportTemplate;
window.uploadRoster = uploadRoster;

async function exportStatutory(formId, fmt) {
  const fb = document.getElementById('stat-export-fb');
  const btn = document.getElementById('stat-btn-' + formId);
  if (btn) btn.classList.add('loading');
  if (fb) acFlash(fb, t('report.exporting'), false);
  try {
    const body = { form_id: formId, company: 'my', role: S.role.id };
    if (fmt) { body.fmt = fmt; if (fmt === 'pdf') body.period = '2024'; }
    const r = await api('/api/statutory/export', body);
    if (r.denied || r.error) { if (fb) acFlash(fb, r.error || t('perm.denied'), true); return; }
    dl(r.download_url, r.filename);
    if (fb) acFlash(fb, `✅ ${r.title} · ${r.filename} (${(r.size / 1024).toFixed(1)}KB)`, false);
  } catch (e) {
    if (fb) acFlash(fb, '导出失败: ' + e.message, true);
  } finally {
    if (btn) btn.classList.remove('loading');
  }
}
async function exportReport(fmt) {
  const fb = document.getElementById('rpt-export-fb');
  if (fb) acFlash(fb, t('report.exporting'), false);
  try {
    const r = await api('/api/report/export', { company: S.company.id, module_id: S.currentNav, fmt, role: S.role.id });
    if (r.denied || r.error) { if (fb) acFlash(fb, r.error || t('perm.denied'), true); return; }
    dl(r.download_url, r.filename);
    if (fb) acFlash(fb, `✅ ${t('report.export_done')} · ${r.filename} (${(r.size / 1024).toFixed(1)}KB)`, false);
  } catch (e) { if (fb) acFlash(fb, t('claim.load_err'), true); }
}
window.exportReport = exportReport;
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
      <div class="text-xs text-slate-400 mt-1.5">${t('claim.used')} ${b.used} · ${b.name} · ${b.level}</div>
      <button class="btn btn-ai w-full mt-4 justify-center" onclick="openAI('ClaimMate','我要拍照报销')"><i class="fas fa-camera"></i> ${t('claim.photo_ai')}</button></div>

    <!-- 真提交表单 + 发票 OCR 上传 -->
    <div class="panel p-5"><div class="font-semibold text-slate-800 mb-3"><i class="fas fa-file-invoice-dollar text-teal-500"></i> ${t('claim.new_form')}</div>
      <label class="ocr-drop" id="ocr-drop">
        <input type="file" accept="image/*" id="ocr-file" class="hidden" onchange="ocrUpload(event)">
        <i class="fas fa-cloud-arrow-up text-2xl text-slate-300"></i>
        <span class="text-xs text-slate-400 mt-1" id="ocr-hint">${t('claim.upload_invoice')}</span>
      </label>
      <div class="space-y-2 mt-3">
        <select class="ac-input" id="cf-type"><option value="">${t('claim.f_type')}</option></select>
        <input class="ac-input" id="cf-merchant" placeholder="${t('claim.f_merchant')}">
        <div class="flex gap-2">
          <input class="ac-input flex-1" id="cf-amount" type="number" step="0.01" placeholder="${t('claim.f_amount')}">
          <input class="ac-input w-24" id="cf-currency" placeholder="${b.currency || 'SGD'}" value="${b.currency || 'SGD'}">
        </div>
        <div class="flex gap-2">
          <input class="ac-input flex-1" id="cf-receipt" placeholder="${t('claim.f_receipt')}">
          <input class="ac-input w-36" id="cf-date" type="date" title="${t('claim.f_date')}">
        </div>
        <input class="ac-input" id="cf-note" placeholder="${t('claim.f_note')}">
        <button class="btn btn-primary w-full justify-center" onclick="submitClaim()"><i class="fas fa-paper-plane"></i> ${t('claim.submit')}</button>
      </div>
      <p class="text-[11px] text-slate-400 mt-2" id="cf-feedback"></p>
      <div id="cf-predict" class="cf-predict hidden"></div>
    </div>

    <!-- 实时报销记录(读真库) -->
    <div class="panel p-5 lg:col-span-3"><div class="flex items-center justify-between mb-3">
        <div class="font-semibold text-slate-800">${t('claim.recent_real')}</div>
        <button class="btn btn-ghost text-xs py-1" onclick="refreshClaims('mine')"><i class="fas fa-rotate"></i> ${t('claim.refresh')}</button></div>
      <div class="table-wrap" id="claims-box"><div class="text-sm text-slate-400 py-6 text-center"><i class="fas fa-spinner fa-spin"></i> ${t('common.loading')}</div></div></div>
  </div>`;
}

function balanceView(m) {
  const emps = m.employees || [];
  const cur = m.currency || 'SGD';
  const empOpts = emps.map(e => `<option value="${e.id}" data-quota="${e.quota}">${e.name} · ${e.dept} (${e.quota}${cur})</option>`).join('');
  // 权限:仅 finance / sys_admin 可调整;其余角色只读历史
  const canAdjust = S.role && (S.role.id === 'finance' || S.role.id === 'sys_admin');
  const formPanel = canAdjust ? `
    <div class="panel p-5"><div class="font-semibold text-slate-800 mb-3"><i class="fas fa-sliders text-teal-500"></i> ${t('balance.adjust_title')}</div>
      <div class="space-y-2">
        <label class="text-xs text-slate-500">${t('balance.emp')}</label>
        <select class="ac-input" id="bal-emp">${empOpts}</select>
        <label class="text-xs text-slate-500">${t('balance.kind')}</label>
        <select class="ac-input" id="bal-kind" onchange="toggleTransferTarget()">
          <option value="增加">${t('balance.add')}</option>
          <option value="减少">${t('balance.reduce')}</option>
          <option value="转移">${t('balance.transfer')}</option>
        </select>
        <div id="bal-target-wrap" class="hidden">
          <label class="text-xs text-slate-500">${t('balance.to_emp')}</label>
          <select class="ac-input" id="bal-target">${empOpts}</select>
        </div>
        <label class="text-xs text-slate-500">${t('balance.amount')} (${cur})</label>
        <input class="ac-input" id="bal-amount" type="number" step="0.01" placeholder="0.00">
        <label class="text-xs text-slate-500">${t('balance.reason')} <span class="text-rose-400">*</span></label>
        <input class="ac-input" id="bal-reason" placeholder="${t('balance.reason_ph')}">
        <button class="btn btn-primary w-full justify-center mt-1" onclick="submitBalanceAdjust()"><i class="fas fa-check"></i> ${t('balance.submit')}</button>
      </div>
      <p class="text-[11px] text-slate-400 mt-2" id="bal-feedback"></p>
      <p class="text-[11px] text-slate-400 mt-1"><i class="fas fa-shield-halved text-emerald-400"></i> ${t('balance.audit_note')}</p>
    </div>` : `
    <div class="panel p-5"><div class="font-semibold text-slate-800 mb-2"><i class="fas fa-lock text-slate-300"></i> ${t('balance.adjust_title')}</div>
      <p class="text-sm text-slate-500 leading-relaxed">${t('balance.no_perm')}</p>
      <p class="text-[11px] text-slate-400 mt-2"><i class="fas fa-circle-info"></i> ${t('balance.allowed_roles')}</p></div>`;
  return `<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    ${formPanel}
    <div class="panel p-5 lg:col-span-2"><div class="flex items-center justify-between mb-3">
        <div class="font-semibold text-slate-800">${t('balance.history')}</div>
        <button class="btn btn-ghost text-xs py-1" onclick="go(S.currentNav)"><i class="fas fa-rotate"></i> ${t('claim.refresh')}</button></div>
      <div class="table-wrap"><table class="dtable"><thead><tr>
        <th>${t('balance.h_date')}</th><th>${t('balance.h_kind')}</th><th>${t('balance.h_amount')}</th><th>${t('balance.h_emp')}</th><th>${t('balance.h_reason')}</th><th>${t('balance.h_op')}</th></tr></thead>
        <tbody>${(m.history || []).length ? m.history.map(r => `<tr>${r.map(c => `<td>${badgeCell(c)}</td>`).join('')}</tr>`).join('')
          : `<tr><td colspan="6" class="text-center text-slate-400 py-6">${t('balance.empty')}</td></tr>`}</tbody></table></div></div></div>`;
}
function toggleTransferTarget() {
  const kind = (document.getElementById('bal-kind') || {}).value;
  const wrap = document.getElementById('bal-target-wrap');
  if (wrap) wrap.classList.toggle('hidden', kind !== '转移');
}
window.toggleTransferTarget = toggleTransferTarget;
async function submitBalanceAdjust() {
  const fb = document.getElementById('bal-feedback');
  const emp_id = (document.getElementById('bal-emp') || {}).value || '';
  const kind = (document.getElementById('bal-kind') || {}).value || '增加';
  const amount = parseFloat((document.getElementById('bal-amount') || {}).value || '0');
  const reason = ((document.getElementById('bal-reason') || {}).value || '').trim();
  const to_emp_id = (document.getElementById('bal-target') || {}).value || '';
  if (!emp_id) { acFlash(fb, t('balance.need_emp'), true); return; }
  if (!amount || amount <= 0) { acFlash(fb, t('balance.need_amount'), true); return; }
  if (!reason) { acFlash(fb, t('balance.need_reason'), true); return; }
  if (kind === '转移' && (!to_emp_id || to_emp_id === emp_id)) { acFlash(fb, t('balance.need_target'), true); return; }
  acFlash(fb, t('claim.submitting'), false);
  try {
    const r = await api('/api/balance/adjust', { company: S.company.id, emp_id, kind, amount, reason, to_emp_id, role: S.role.id });
    if (r.denied || r.error) { acFlash(fb, r.error || t('perm.denied'), true); return; }
    const bal = r.balance || {};
    acFlash(fb, `✅ ${t('balance.done')} · ${r.emp} ${kind} ${amount} → ${t('balance.remaining')}: ${bal.remaining}`, false);
    setTimeout(() => go(S.currentNav), 700);
  } catch (e) { acFlash(fb, t('claim.load_err'), true); }
}
window.submitBalanceAdjust = submitBalanceAdjust;

function familyView(m) {
  return `<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div class="panel p-5"><div class="font-semibold text-slate-800 mb-3">${t('fam.archive')}</div>
      <div id="family-list">${familyRows(m.members)}</div></div>
    <div class="panel p-5"><div class="font-semibold text-slate-800 mb-3"><i class="fas fa-user-plus text-teal-500"></i> ${t('fam.add')}</div>
      <div class="space-y-2">
        <select class="ac-input" id="fam-relation">
          <option value="配偶">${t('fam.spouse')}</option>
          <option value="子女">${t('fam.child')}</option>
          <option value="父母">${t('fam.parent')}</option>
        </select>
        <input class="ac-input" id="fam-name" placeholder="${t('fam.name')}">
        <button class="btn btn-primary w-full justify-center" onclick="addFamily()"><i class="fas fa-plus"></i> ${t('fam.add')}</button>
      </div>
      <p class="text-[11px] text-slate-400 mt-2" id="fam-feedback"></p>
      <button class="btn btn-ai w-full mt-3 justify-center" onclick="openAI('ClaimMate','登记我的家属信息')"><i class="fas fa-robot"></i> ${t('fam.ai')}</button></div></div>`;
}
function familyRows(members) {
  if (!members || !members.length) return `<div class="text-sm text-slate-400 py-4 text-center">${t('fam.empty')}</div>`;
  return members.map(mem => `<div class="flex items-center gap-3 py-3 border-b border-slate-50 last:border-0">
    <div class="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-400"><i class="fas fa-user"></i></div>
    <div class="flex-1"><div class="text-sm font-medium text-slate-700">${mem.name}</div><div class="text-xs text-slate-400">${mem.relation}</div></div>
    <span class="badge b-info">${t('fam.linkable')}</span></div>`).join('');
}
async function addFamily() {
  const fb = document.getElementById('fam-feedback');
  const name = (document.getElementById('fam-name') || {}).value || '';
  const relation = (document.getElementById('fam-relation') || {}).value || '配偶';
  if (!name.trim()) { acFlash(fb, t('fam.need_name'), true); return; }
  acFlash(fb, t('claim.submitting'), false);
  try {
    const r = await api('/api/family', { company: S.company.id, relation, name, role: S.role.id });
    if (r.denied || r.error) { acFlash(fb, r.error || t('perm.denied'), true); return; }
    acFlash(fb, '✅ ' + t('fam.added') + ' ' + (r.name || name), false);
    document.getElementById('fam-name').value = '';
    // 重新拉模块刷新列表
    const m = await fetch(`/api/module/family?company=${S.company.id}&lang=${S.lang}`).then(x => x.json());
    const box = document.getElementById('family-list');
    if (box) box.innerHTML = familyRows(m.members);
  } catch (e) { acFlash(fb, t('claim.load_err'), true); }
}
window.addFamily = addFamily;

function moduleAction(action, title) {
  // AI/对话/批量类 → 走对话式 Agent
  if (action.includes('AI') || action.includes('对话') || action.includes('智能') ||
      action.includes('NL2SQL') || action.includes('跑批') || action.includes('推荐'))
    return openAI(null, action + ' · ' + title);
  // 当前模块有真新增能力 → 打开真表单
  if (window.__crud) return openCrudModal();
  // 兜底:导出/自动更新 等 → 友好提示(非阻塞 toast)
  toast(`${action} · ${title}`);
}
window.moduleAction = moduleAction;

// ════════ 通用真表单模态框(创建/新增 类型 · 组 · 权益 · 汇率 · 差旅…) ════════
function openCrudModal() {
  const crud = window.__crud;
  if (!crud) return;
  const fields = crud.fields || [];
  const inputs = fields.map(f => {
    const id = `crf-${f.key}`;
    const req = f.required ? '<span class="text-rose-400">*</span>' : '';
    const val = (f.value !== undefined && f.value !== null) ? String(f.value) : '';
    const ro = f.readonly ? 'readonly style="background:#f8fafc;color:#94a3b8"' : '';
    let ctrl;
    if (f.type === 'select') {
      ctrl = `<select class="ac-input" id="${id}">${(f.options || []).map(o => `<option value="${o}" ${o === val ? 'selected' : ''}>${o}</option>`).join('')}</select>`;
    } else if (f.type === 'number') {
      ctrl = `<input class="ac-input" id="${id}" type="number" step="0.01" placeholder="${f.placeholder || ''}" value="${val}" ${ro}>`;
    } else if (f.type === 'date') {
      ctrl = `<input class="ac-input" id="${id}" type="date" value="${val}">`;
    } else {
      ctrl = `<input class="ac-input" id="${id}" placeholder="${f.placeholder || ''}" value="${val}" ${ro}>`;
    }
    return `<div class="mb-2"><label class="text-xs text-slate-500 mb-1 block">${f.label}${req}</label>${ctrl}</div>`;
  }).join('');
  const ov = document.createElement('div');
  ov.id = 'crud-overlay';
  ov.className = 'crud-overlay';
  ov.innerHTML = `<div class="crud-modal">
    <div class="flex items-center justify-between mb-3">
      <div class="font-semibold text-slate-800"><i class="fas ${crud.edit_code ? 'fa-pen-to-square' : 'fa-plus-circle'} text-teal-500"></i> ${crud.action}</div>
      <button class="text-slate-400 hover:text-slate-600" onclick="closeCrudModal()"><i class="fas fa-xmark"></i></button>
    </div>
    <div>${inputs}</div>
    <p class="text-[11px] text-slate-400 my-2" id="crud-feedback"></p>
    <div class="flex gap-2 mt-2">
      <button class="btn btn-ghost flex-1 justify-center" onclick="closeCrudModal()">${t('crud.cancel')}</button>
      <button class="btn btn-primary flex-1 justify-center" onclick="submitCrud()"><i class="fas fa-check"></i> ${t('crud.save')}</button>
    </div></div>`;
  ov.addEventListener('click', e => { if (e.target === ov) closeCrudModal(); });
  document.body.appendChild(ov);
}
function closeCrudModal() { const o = document.getElementById('crud-overlay'); if (o) o.remove(); }

async function submitCrud() {
  const crud = window.__crud;
  if (!crud) return;
  const fb = document.getElementById('crud-feedback');
  const vals = {};
  for (const f of (crud.fields || [])) {
    const el = document.getElementById(`crf-${f.key}`);
    const v = el ? el.value.trim() : '';
    if (f.required && !v) { acFlash(fb, `${f.label} ${t('crud.required')}`, true); return; }
    vals[f.key] = v;
  }
  acFlash(fb, t('claim.submitting'), false);
  try {
    let r;
    if (crud.kind === 'claim_type') {
      // 报销类型 → 走真 claim_types 表
      const ctBody = {
        company: S.company.id, code: vals.code, name: vals.name, name_en: vals.name_en || '',
        grp: vals.grp || '日常', limit_amt: parseFloat(vals.limit_amt || '0'),
        need_invoice: (vals.need_invoice || '是') === '是', role: S.role.id,
      };
      // 编辑模式 → PUT;新建模式 → POST
      if (crud.edit_code) {
        r = await api(`/api/claim_types/${encodeURIComponent(crud.edit_code)}`, ctBody, 'PUT');
      } else {
        r = await api('/api/claim_types', ctBody);
      }
    } else {
      // 其它表格模块 → 通用 module_records
      r = await api('/api/module_records', { module_id: crud.module_id, company: S.company.id, payload: vals, role: S.role.id });
    }
    if (r.error) { acFlash(fb, r.error, true); return; }
    acFlash(fb, '✅ ' + t('crud.saved'), false);
    setTimeout(() => { closeCrudModal(); go(S.currentNav || crud.module_id); }, 500);
  } catch (e) { acFlash(fb, t('claim.load_err'), true); }
}

// ════════ 报销类型编辑(PUT) —— 预填模态框 ════════
async function editClaimType(code) {
  try {
    const types = await fetch(`/api/claim_types?company=${S.company.id}`).then(r => r.json()).then(x => x.types || []);
    const ct = types.find(t_ => t_.code === code);
    if (!ct) { toast(t('crud.not_found') || 'not found', true); return; }
    // 构造编辑用 crud 配置(code 锁定不可改,作为主键)
    window.__crud = {
      module_id: 'claim_type', kind: 'claim_type', edit_code: code,
      action: (S.lang === 'en' ? 'Edit claim type' : '编辑报销类型') + ' · ' + code,
      fields: [
        { key: 'code', label: t('ct.code') || '编码', type: 'text', required: true, readonly: true, value: ct.code },
        { key: 'name', label: t('ct.name') || '名称', type: 'text', required: true, value: ct.name },
        { key: 'name_en', label: t('ct.name_en') || '英文名', type: 'text', value: ct.name_en || '' },
        { key: 'grp', label: t('ct.grp') || '分组', type: 'select', options: ['日常', '差旅', '福利'], value: ct.grp || '日常' },
        { key: 'limit_amt', label: (t('ct.limit') || '限额') + `(${S.company.currency || 'SGD'})`, type: 'number', required: true, value: ct.limit_amt },
        { key: 'need_invoice', label: t('ct.need_invoice') || '需发票', type: 'select', options: ['是', '否'], value: ct.need_invoice ? '是' : '否' },
      ],
    };
    openCrudModal();
  } catch (e) { toast(t('claim.load_err'), true); }
}
window.editClaimType = editClaimType;

async function deleteRow(kind, key) {
  if (!confirm(t('crud.confirm_del'))) return;
  try {
    let r;
    if (kind === 'type') {
      r = await api(`/api/claim_types/${encodeURIComponent(key)}?company=${S.company.id}&role=${S.role.id}`, null, 'DELETE');
    } else {
      r = await api(`/api/module_records/${key}?company=${S.company.id}&role=${S.role.id}`, null, 'DELETE');
    }
    if (r.error) { toast(r.error, true); return; }
    toast(t('crud.deleted'));
    go(S.currentNav);
  } catch (e) { toast(t('claim.load_err'), true); }
}

// ════════ 审批端真操作(接多级审批流 advance API) ════════
async function decideClaim(cid, status) {
  const fb = document.getElementById('approval-feedback');
  if (!cid) return;
  // status: approved/rejected/returned → 审批流状态机 decision
  const decision = status;
  if (fb) acFlash(fb, t('claim.submitting'), false);
  try {
    const r = await api(`/api/claims/${encodeURIComponent(cid)}/advance`,
      { decision, by: nameOf(S.role), comment: '', role: S.role.id });
    if (r.denied) { if (fb) acFlash(fb, r.zh || r.en || t('perm.denied'), true); return; }
    if (r.error) { if (fb) acFlash(fb, r.error, true); return; }
    // 多级审批反馈:显示整体状态 + 链摘要
    const ov = r.overall;
    const wordMap = { approved: t('crud.approved'), rejected: t('crud.rejected'),
                      returned: t('wf.returned'), in_review: t('wf.in_review') };
    const tip = ov === 'in_review'
      ? `↗️ ${cid} ${t('wf.next_level')} L${r.current_level} · ${r.summary}`
      : `✅ ${cid} ${wordMap[ov] || ov} · ${r.summary}`;
    if (fb) acFlash(fb, tip, false);
    go(S.currentNav);
  } catch (e) { if (fb) acFlash(fb, t('claim.load_err'), true); }
}
window.decideClaim = decideClaim;
async function batchApprove() {
  const fb = document.getElementById('approval-feedback');
  if (fb) acFlash(fb, t('claim.submitting'), false);
  try {
    const r = await api('/api/claims/batch_decide', { company: S.company.id, status: 'approved', risk_level: '低', role: S.role.id });
    if (r.denied || r.error) { if (fb) acFlash(fb, r.error || t('perm.denied'), true); return; }
    if (fb) acFlash(fb, `✅ ${t('crud.batch_done')} ${r.affected || 0}`, false);
    go(S.currentNav);
  } catch (e) { if (fb) acFlash(fb, t('claim.load_err'), true); }
}

// 轻提示 toast(替代旧 alert)
function toast(msg, isErr) {
  const el = document.createElement('div');
  el.className = 'ac-toast' + (isErr ? ' ac-toast-err' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.classList.add('show'), 10);
  setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, 2600);
}

window.openCrudModal = openCrudModal;
window.closeCrudModal = closeCrudModal;
window.submitCrud = submitCrud;
window.deleteRow = deleteRow;
window.decideClaim = decideClaim;
window.batchApprove = batchApprove;
window.toast = toast;

// ════════ 真功能联动:报销单实时刷新 + 真提交 + 发票 OCR ════════
const STATUS_BADGE = { pending: 'b-mid', approved: 'b-low', rejected: 'b-high', paid: 'b-info' };
function statusText(st) { return t('claim.st_' + st) || st; }

async function loadClaimTypes() {
  const sel = document.getElementById('cf-type');
  if (!sel) return;
  try {
    const types = await fetch(`/api/claim_types?company=${S.company.id}`).then(r => r.json()).then(x => x.types || []);
    if (types.length) {
      sel.innerHTML = `<option value="">${t('claim.f_type')}</option>` +
        types.map(ct => `<option value="${ct.code}">${(S.lang === 'en' && ct.name_en ? ct.name_en : ct.name)} (≤${ct.limit_amt})</option>`).join('');
    }
  } catch (e) { /* 静默 */ }
}

async function refreshClaims(scope) {
  const box = document.getElementById('claims-box');
  if (!box) return;
  try {
    const d = await fetch(`/api/claims?company=${S.company.id}`).then(r => r.json());
    const claims = d.claims || [];
    if (!claims.length) { box.innerHTML = `<div class="text-sm text-slate-400 py-6 text-center">${t('claim.empty')}</div>`; return; }
    const rows = claims.map(cl => `<tr>
      <td class="font-mono text-xs">${cl.id}</td>
      <td>${cl.type_name || cl.type_code}</td>
      <td>${cl.merchant || '-'}</td>
      <td class="font-medium">${cl.amount} ${cl.currency}</td>
      <td><span class="badge ${cl.risk_level === '高' ? 'b-high' : cl.risk_level === '中' ? 'b-mid' : 'b-low'}">${cl.risk_score}</span></td>
      <td><span class="badge ${STATUS_BADGE[cl.status] || 'b-info'}">${statusText(cl.status)}</span></td>
      <td class="text-xs text-slate-400">${(cl.created_at || '').slice(0, 16)}</td>
    </tr>`).join('');
    const stats = d.stats || {};
    box.innerHTML = `<table class="dtable"><thead><tr>
        <th>${t('claim.c_id')}</th><th>${t('claim.c_type')}</th><th>${t('claim.f_merchant')}</th>
        <th>${t('claim.c_amount')}</th><th>${t('claim.c_risk')}</th><th>${t('claim.c_status')}</th><th>${t('claim.c_date')}</th>
      </tr></thead><tbody>${rows}</tbody></table>
      <div class="text-xs text-slate-400 mt-2 px-1">${t('claim.total')}: ${d.count} · ${t('claim.st_pending')}: ${stats.pending || 0} · ${t('claim.st_approved')}: ${stats.approved || 0}</div>`;
  } catch (e) {
    box.innerHTML = `<div class="text-sm text-rose-400 py-6 text-center">${t('claim.load_err')}</div>`;
  }
}

async function submitClaim() {
  const fb = document.getElementById('cf-feedback');
  const typeCode = (document.getElementById('cf-type') || {}).value || '';
  const amount = parseFloat((document.getElementById('cf-amount') || {}).value || '0');
  if (!typeCode) { acFlash(fb, t('claim.need_type'), true); return; }
  if (!amount || amount <= 0) { acFlash(fb, t('claim.need_amount'), true); return; }
  const payload = {
    company: S.company.id, type_code: typeCode, amount: amount,
    merchant: (document.getElementById('cf-merchant') || {}).value || '',
    currency: (document.getElementById('cf-currency') || {}).value || '',
    note: (document.getElementById('cf-note') || {}).value || '',
    receipt_no: (document.getElementById('cf-receipt') || {}).value || '',
    invoice_date: (document.getElementById('cf-date') || {}).value || '',
  };
  const pv = document.getElementById('cf-predict');
  if (pv) pv.classList.add('hidden');
  acFlash(fb, t('claim.submitting'), false);
  try {
    payload.role = S.role.id;
    const r = await api('/api/claims', payload);
    if (r.error) { acFlash(fb, r.error, true); return; }
    // ── 验证拦截 (7 条规则阻止级错误) ──
    if (r.blocked) {
      acFlash(fb, '⛔ ' + (r.message || t('claim.blocked')), true);
      return;
    }
    const risk = r.risk || {}; const cl = r.claim || {};
    acFlash(fb, `✅ ${t('claim.submitted')} ${cl.id} · ${t('claim.c_risk')} ${risk.score}(${risk.level}) · ${t('claim.tax')} ${r.tax_amount}`, false);
    // ── AI 预判 + 审批链可视化 ──
    if (pv && r.ai_predict) {
      const p = r.ai_predict;
      pv.classList.remove('hidden');
      pv.innerHTML = `<div class="cf-predict-chain"><i class="fas fa-route text-teal-500"></i> ${r.chain_summary || ''}</div>
        <div class="cf-predict-ai"><i class="fas fa-robot text-indigo-400"></i> ${p.summary}</div>`;
    }
    ['cf-merchant', 'cf-amount', 'cf-note', 'cf-receipt', 'cf-date'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    refreshClaims('mine');
  } catch (e) { acFlash(fb, t('claim.load_err'), true); }
}

async function ocrUpload(ev) {
  const file = ev.target.files && ev.target.files[0];
  if (!file) return;
  const hint = document.getElementById('ocr-hint');
  if (hint) hint.textContent = t('claim.ocr_reading');
  const reader = new FileReader();
  reader.onload = async () => {
    const b64 = String(reader.result);
    try {
      const r = await api('/api/ocr', { company: S.company.id, image_b64: b64, mime: file.type || 'image/jpeg' });
      const ext = r.extracted || {};
      if (ext.type_code) { const s = document.getElementById('cf-type'); if (s) s.value = ext.type_code; }
      if (ext.merchant) { const e = document.getElementById('cf-merchant'); if (e) e.value = ext.merchant; }
      if (ext.amount) { const e = document.getElementById('cf-amount'); if (e) e.value = ext.amount; }
      if (ext.currency) { const e = document.getElementById('cf-currency'); if (e) e.value = ext.currency; }
      if (ext.date) { const e = document.getElementById('cf-date'); if (e) e.value = ext.date; }
      if (ext.tax_no) { const e = document.getElementById('cf-receipt'); if (e && !e.value) e.value = ext.tax_no; }
      const note = (r.engine_note && (S.lang === 'en' ? r.engine_note.en : r.engine_note.zh)) || '';
      if (hint) hint.textContent = (r.engine === 'vision' ? '✅ ' : 'ℹ️ ') + note;
    } catch (e) { if (hint) hint.textContent = t('claim.ocr_err'); }
  };
  reader.readAsDataURL(file);
}

// 通用反馈(复用 ac-toast 风格的轻提示)
function acFlash(el, msg, isErr) {
  if (!el) return;
  el.textContent = msg;
  el.style.color = isErr ? '#ef4444' : '#10b981';
}

window.loadClaimTypes = loadClaimTypes;
window.refreshClaims = refreshClaims;
window.submitClaim = submitClaim;
window.ocrUpload = ocrUpload;

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
  applyMode();                       // 用户模式 → 移动端外壳;管理角色 → 桌面工作台
  renderTopbar(); renderNav(); closePopover();
  if (!S.role.menus.includes(S.currentNav)) go('dashboard'); else go(S.currentNav);
}
window.switchRole = switchRole;

// ════════ 移动端用户模式 ════════
// 普通员工(employee)= 移动端 App 体验;其余为桌面管理工作台
const MOBILE_ROLES = ['employee'];
function isMobileMode() { return S.role && MOBILE_ROLES.includes(S.role.id); }
function applyMode() {
  const on = isMobileMode();
  document.body.classList.toggle('mode-mobile', on);
  let bar = $('#mobile-tabbar');
  if (on) { if (!bar) buildTabbar(); renderTabbar(); }
  else if (bar) bar.remove();
}
// 底部 Tab(员工自助:首页/报销/我的)
const MOBILE_TABS = [
  { nav: 'dashboard', icon: 'fa-house', key: 'm.tab_home' },
  { nav: 'my', icon: 'fa-receipt', key: 'm.tab_claim' },
  { nav: '__me', icon: 'fa-user', key: 'm.tab_me' },
];
function buildTabbar() {
  const bar = document.createElement('nav');
  bar.id = 'mobile-tabbar';
  document.body.appendChild(bar);
}
function renderTabbar() {
  const bar = $('#mobile-tabbar'); if (!bar) return;
  bar.innerHTML = MOBILE_TABS.map(tb => {
    const active = (tb.nav === '__me') ? (S.currentNav === '__me') : (S.currentNav === tb.nav);
    return `<button class="mtab ${active ? 'active' : ''}" onclick="mobileGo('${tb.nav}')">
      <i class="fas ${tb.icon}"></i><span>${t(tb.key)}</span></button>`;
  }).join('') +
    `<button class="mtab mtab-ai" onclick="openAI('ClaimMate')"><i class="fas fa-robot"></i><span>${t('m.tab_ai')}</span></button>`;
}
function mobileGo(nav) {
  if (nav === '__me') { S.currentNav = '__me'; renderMeView(); renderTabbar(); return; }
  go(nav); renderTabbar();
}
window.mobileGo = mobileGo;
// 「我的」页(移动端个人中心)
function renderMeView() {
  const r = S.role, c = S.company;
  $('#view').innerHTML = `<div class="me-page">
    <div class="me-hero">
      <div class="me-avatar" style="background:${r.color}"><i class="fas ${r.icon}"></i></div>
      <div class="me-name">${nameOf(r)}</div>
      <div class="me-sub">${c.flag} ${nameOf(c)}</div>
    </div>
    <div class="me-list">
      <div class="me-item" onclick="openAI('ClaimMate','我还能报多少额度?')"><i class="fas fa-wallet text-emerald-500"></i><span>${t('m.me_balance')}</span><i class="fas fa-chevron-right me-arr"></i></div>
      <div class="me-item" onclick="mobileGo('my')"><i class="fas fa-receipt text-teal-500"></i><span>${t('m.me_claims')}</span><i class="fas fa-chevron-right me-arr"></i></div>
      <div class="me-item" onclick="openAI('ClaimMate','帮我登记家属信息')"><i class="fas fa-users text-indigo-500"></i><span>${t('m.me_family')}</span><i class="fas fa-chevron-right me-arr"></i></div>
      <div class="me-item" onclick="$('#help-btn').click()"><i class="fas fa-circle-question text-slate-400"></i><span>${t('help.open')}</span><i class="fas fa-chevron-right me-arr"></i></div>
      <div class="me-item" onclick="$('#role-switch').click()"><i class="fas fa-right-left text-slate-400"></i><span>${t('m.me_switch')}</span><i class="fas fa-chevron-right me-arr"></i></div>
    </div></div>`;
}

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
  const es = new EventSource(`/api/chat/stream?message=${encodeURIComponent(text)}&thread_id=${S.threadId}&company=${S.company.id}&role=${S.role.id}`);
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
        <input id="ac-name" class="ac-input" placeholder="DeepSeek / TokenHot ...">
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
  await api('/api/admin/providers', payload);
  acToast(tt('submit') + ' ✅'); renderAIConfig();
}

async function acVerify(pid) {
  acToast(tt('verifying'));
  const r = await api(`/api/admin/providers/${pid}/verify`, {});
  acToast(r.verify.ok ? `${tt('verify_ok')} ${r.verify.models_pulled || 0} models` : r.verify.msg, r.verify.ok ? 'ok' : 'err');
  renderAIConfig();
}
async function acActivate(pid, on) {
  const r = await api(`/api/admin/providers/${pid}/activate?on=${on}`, {});
  if (r.error) acToast(r.error, 'err'); else acToast('✅'); renderAIConfig();
}
async function acPull(pid) {
  acToast(tt('pulling'));
  const r = await api(`/api/admin/providers/${pid}/models/pull`, {});
  acToast(r.error ? r.error : `${r.count} models`, r.error ? 'err' : 'ok');
  AC.tab = 'model'; AC.filterProvider = pid; renderAIConfig();
}
async function acDelProvider(pid) {
  if (!confirm(tt('confirm_del'))) return;
  await api(`/api/admin/providers/${pid}`, null, 'DELETE');
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
  await api('/api/admin/models/toggle', { model_pk: pk, enabled: on });
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
  await api('/api/admin/bindings', { agent_id: agentId, provider_id, model_id });
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

