// ═══════════ Paydaes ClaimGPT 集团版 前端 ═══════════
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const fmt = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');

// 对外信息脱敏开关:false=对外展示(隐藏「技术栈」板块 + 「商业化路线图」入口/页面),
// true=内部完整视图。内部需查看时改为 true 并重新混淆即可恢复。
const SHOW_INTERNAL = false;

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
  // 默认 sys_admin;支持 ?role=employee 等 URL 参数(便于直达指定身份/演示)
  const _qpRole = new URLSearchParams(location.search).get('role');
  S.role = (_qpRole && d.roles.find(r => r.id === _qpRole)) || d.roles.find(r => r.id === 'sys_admin');
  // 员工(手机端)演示员工 MY001 隶属马来西亚公司,默认锁定 my 公司,保证额度/报销/薪资全链路 RM 一致
  if (S.role && S.role.id === 'employee') {
    const myCo = S.group.companies.find(c => c.id === 'my');
    if (myCo) S.company = myCo;
  }
  S.currentAgent = d.agents[0];
  // i18n:语言切换时重扫静态 DOM + 重渲染动态区(导航/当前页/智能体条)
  onLangChange(() => {
    renderTopbar(); renderNav(); renderAgentTabs();
    go(S.currentNav);
    if ($('#ai-messages').dataset.init) selectAgent(S.currentAgent);
  });
  applyI18n();                    // 首次翻译静态 DOM
  applyMode();                    // 按初始角色决定手机/桌面外壳(支持 ?role= 直达)
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
  // 点击集团 Logo / 名称 → 进入系统架构图谱+说明书页
  $('#group-logo').style.cursor = 'pointer';
  $('#group-logo').title = t('arch.enter');
  $('#group-logo').onclick = () => go('__arch');
  $('#group-name').style.cursor = 'pointer';
  $('#group-name').onclick = () => go('__arch');
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
  if (navId === '__arch') return renderArchitecture();  // 系统架构图谱+说明书(点 Logo 进入)
  if (navId === '__roadmap') return SHOW_INTERNAL ? renderRoadmap() : renderArchitecture();  // 商业化路线图(仅内部,脱敏模式回退架构页)
  if (navId === '__me') return renderMeView();          // 移动端·我的(个人中心)
  if (navId === '__payslip') return renderMyPayslip();  // 移动端·我的薪资单
  // 员工(手机模式)用专属轻量首页,而非管理者的桌面大屏
  if (navId === 'dashboard' && isMobileMode()) return renderMobileHome();
  if (navId === 'dashboard') return renderDashboard();
  if (navId === 'global') return renderCompliance();
  if (navId === 'cockpit') return renderCockpit();
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
// 取该模块在当前公司已保存的表单,回填到字段定义(实现"保存→重载回显"闭环)
async function mergeSavedForm(m, navId) {
  const res = await api(`/api/module_form/${navId}?company=${effCompany()}`);
  const form = res && res.form;
  if (!form || !Object.keys(form).length) return;
  const apply = (fields) => (fields || []).forEach(f => {
    const key = f.label_key || f.label_en || f.label;
    if (key in form && form[key] != null) f.value = form[key];
  });
  apply(m.fields); apply(m.header_fields);
  if (form._formula) m.formula = form._formula;
  if (form._selected) m.right = form._selected;
  if (form._available) m.left = form._available;
  if (form['GPS Coordinate']) m.coord = form['GPS Coordinate'];
  m._restored = true;     // 标记已回显(可用于角标提示)
}
async function renderModule(navId) {
  const m = await fetch(`/api/module/${navId}?company=${effCompany()}&lang=${S.lang}`).then(r => r.json());
  // 加载回显:把该公司已保存的表单值合并回字段(按 label_en/label_key 匹配)
  if (['p_detail', 'p_tabset', 'p_shuttle', 'p_formula', 'p_map'].includes(m.layout)) {
    try { await mergeSavedForm(m, navId); } catch (e) { /* 无已存数据则跳过 */ }
  }
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
    <div class="flex gap-2 mt-3 flex-wrap"><button class="btn btn-ai" onclick="openAI('PayrollNavigator','执行薪资跑批')"><i class="fas fa-robot"></i> ${S.lang === 'en' ? 'AI Auto Run' : 'AI 自主跑批'}</button>
      <button class="btn btn-primary" style="background:#0f766e" onclick="runFormulaPayroll(this)"><i class="fas fa-calculator"></i> ${S.lang === 'en' ? 'Formula-Driven Payroll' : '公式驱动批量发薪'}</button>
      ${m.rollback ? `<button class="btn btn-ghost"><i class="fas fa-rotate-left"></i> ${S.lang === 'en' ? 'Rollback' : '回滚批次'}</button>` : ''}</div>
    <div id="fp-result" class="mt-4"></div></div>`;
}

// 公式驱动批量发薪 —— 调真实批算管线, 展示工资单 + 公式溯源
async function runFormulaPayroll(btn) {
  const box = document.getElementById('fp-result');
  if (!box) return;
  const en = S.lang === 'en';
  const old = btn.innerHTML; btn.disabled = true;
  btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${en ? 'Running…' : '跑批中…'}`;
  try {
    let company = (typeof effCompany === 'function' ? effCompany() : (S.company && S.company.id)) || 'my';
    if (company === 'group' || !company) company = 'my';  // 集团视图回退到演示主体
    const r = await api(`/api/payroll/run?company=${company}&role=${S.role ? S.role.id : 'payroll'}`, null, 'GET');
    if (r.error || r.denied) { box.innerHTML = `<div class="fp-err"><i class="fas fa-lock"></i> ${esc(r.error || (en ? 'No permission' : '权限不足'))}</div>`; return; }
    const tot = r.totals || {};
    const cpf = r.currency_prefix || 'RM';   // 币种前缀(随公司所在国)
    const fxNote = `<div class="fp-fxbar">
      <span class="fp-fxchip ${r.formulas.leave_active ? 'on' : 'off'}"><i class="fas fa-umbrella-beach"></i> ${en ? 'Leave formula' : '假期公式'}: ${r.formulas.leave_active ? (en ? 'ACTIVE' : '已驱动') : (en ? 'default' : '默认')}</span>
      <span class="fp-fxchip ${r.formulas.ot_active ? 'on' : 'off'}"><i class="fas fa-business-time"></i> ${en ? 'OT formula' : '加班公式'}: ${r.formulas.ot_active ? (en ? 'ACTIVE' : '已驱动') : (en ? 'default' : '默认')}</span>
    </div>`;
    const rows = (r.rows || []).map(p => {
      const traceOk = (p.formula_trace || []).filter(t => t.ok).length;
      const traceBtn = (p.formula_trace && p.formula_trace.length)
        ? `<button class="fp-trace-btn" onclick='fpShowTrace(${JSON.stringify(JSON.stringify(p.formula_trace))})' title="${en ? 'Formula trace' : '公式溯源'}"><i class="fas fa-diagram-project"></i> ${traceOk}</button>` : '—';
      return `<tr>
        <td>${esc(p.emp_no)}</td><td>${esc(p.name)}</td><td>${esc(p.grade || '')}</td>
        <td class="num">${fmtMoney(p.basic_pay, cpf)}</td>
        <td class="num">${fmtMoney(p.ot_amount, cpf)}</td>
        <td class="num"><b>${p.entitlement_days}</b></td>
        <td class="num">${fmtMoney(p.gross_total, cpf)}</td>
        <td class="num fp-ded">-${fmtMoney(p.total_deduction, cpf)}</td>
        <td class="num fp-net">${fmtMoney(p.net_pay, cpf)}</td>
        <td class="center">${traceBtn}</td></tr>`;
    }).join('');
    box.innerHTML = `${fxNote}
      <div class="fp-tablewrap"><table class="fp-table">
        <thead><tr>
          <th>${en ? 'No.' : '工号'}</th><th>${en ? 'Name' : '姓名'}</th><th>${en ? 'Grade' : '职级'}</th>
          <th class="num">${en ? 'Basic' : '基本'}</th><th class="num">${en ? 'OT' : '加班'}</th>
          <th class="num">${en ? 'Leave Days' : '应享天数'}</th><th class="num">${en ? 'Gross' : '应发'}</th>
          <th class="num">${en ? 'Deduction' : '扣除'}</th><th class="num">${en ? 'Net Pay' : '实发'}</th>
          <th class="center">${en ? 'Trace' : '溯源'}</th>
        </tr></thead><tbody>${rows}</tbody>
        <tfoot><tr><td colspan="6">${en ? 'TOTAL' : '合计'} · ${r.count} ${en ? 'employees' : '人'} · <span class="fp-cur">${esc(r.currency || cpf)}</span></td>
          <td class="num">${fmtMoney(tot.gross_total, cpf)}</td><td class="num fp-ded">-${fmtMoney(tot.total_deduction || (tot.gross_total - tot.net_pay), cpf)}</td>
          <td class="num fp-net">${fmtMoney(tot.net_pay, cpf)}</td><td></td></tr></tfoot>
      </table></div>
      <p class="fp-hint"><i class="fas fa-circle-info"></i> ${en ? 'Leave days & OT driven by formulas saved in Leave Entitlement / Overtime modules. Click trace to see variables.' : '应享天数 / 加班费由「假期权益 / 加班设置」模块里保存的公式实时驱动。点溯源图标看变量来源。'}</p>`;
  } catch (e) {
    box.innerHTML = `<div class="fp-err"><i class="fas fa-triangle-exclamation"></i> ${esc(String(e))}</div>`;
  } finally { btn.disabled = false; btn.innerHTML = old; }
}
window.runFormulaPayroll = runFormulaPayroll;

// 注:fmtMoney(v, cur) 统一定义于后文(币种前缀 + 数字),全站共用,此处不再重复定义
//     (此前这里有一份重复定义会被后定义者覆盖 —— 同「重复路由」类隐患,已合并)

// 公式溯源弹层
function fpShowTrace(traceJson) {
  let trace = [];
  try { trace = JSON.parse(traceJson); } catch (e) { return; }
  const en = S.lang === 'en';
  const items = trace.map(t => {
    const vars = Object.entries(t.used_vars || {}).map(([k, v]) => `<span class="fp-var"><code>${esc(k)}</code>=${esc(String(v))}</span>`).join('');
    return `<div class="fp-trace-card ${t.ok ? '' : 'bad'}">
      <div class="fp-trace-h"><span class="fp-trace-badge">${esc(t.label || t.driver)}</span>
        ${t.ok ? `<span class="fp-trace-res">→ ${esc(String(t.result))}</span>` : `<span class="fp-trace-err">${esc(t.error || 'error')}</span>`}</div>
      <pre class="fp-trace-code">${esc(t.formula)}</pre>
      <div class="fp-trace-vars">${vars || (en ? '(no variables)' : '(无变量)')}</div></div>`;
  }).join('');
  const html = `<div id="fp-trace-mask" class="fxhelp-mask" onclick="if(event.target===this)fpTraceClose()">
    <div class="fxhelp-panel" style="width:min(560px,94vw)">
      <div class="fxhelp-head"><div class="fxhelp-title"><i class="fas fa-diagram-project"></i> ${en ? 'Formula Trace' : '公式溯源'}</div>
        <button class="fxhelp-x" onclick="fpTraceClose()"><i class="fas fa-times"></i></button></div>
      <div class="fxhelp-body">${items}</div></div></div>`;
  document.body.insertAdjacentHTML('beforeend', html);
}
function fpTraceClose() { const m = document.getElementById('fp-trace-mask'); if (m) m.remove(); }
window.fpShowTrace = fpShowTrace; window.fpTraceClose = fpTraceClose;

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
// 表单图标映射(按 form_id;未列出的用默认图标)
const STAT_FORM_ICON = {
  payslip: ['fa-file-invoice-dollar', 'emerald'],
  epf_borang_a: ['fa-piggy-bank', 'blue'], ea_form: ['fa-file-contract', 'orange'],
  e_form: ['fa-file-lines', 'teal'], ec_form: ['fa-file-circle-check', 'green'],
  cp39: ['fa-receipt', 'rose'], socso_8a: ['fa-shield-heart', 'cyan'],
  bank_ibg: ['fa-building-columns', 'indigo'], payroll_gl: ['fa-scale-balanced', 'amber'],
  lhdn_audit: ['fa-file-shield', 'slate'],
  ir8a: ['fa-file-contract', 'orange'], ir8a_appendix: ['fa-paperclip', 'blue'],
  ir21: ['fa-plane-departure', 'rose'], cpf_submission: ['fa-piggy-bank', 'blue'],
  ais_file: ['fa-file-export', 'teal'],
  pnd1: ['fa-receipt', 'rose'], pnd1_kor: ['fa-file-contract', 'orange'],
  sso_kor_tor20: ['fa-shield-heart', 'cyan'], fiftytawi: ['fa-file-circle-check', 'green'],
  pit_monthly: ['fa-receipt', 'rose'], pit_annual: ['fa-file-contract', 'orange'], si_d02: ['fa-shield-heart', 'cyan'],
  spt1721: ['fa-file-contract', 'orange'], form_1721a1: ['fa-file-circle-check', 'green'], bpjs: ['fa-shield-heart', 'cyan'],
  ir56b: ['fa-file-contract', 'orange'], ir56e: ['fa-user-plus', 'green'], ir56f: ['fa-user-minus', 'rose'],
  ir56g: ['fa-plane-departure', 'indigo'], mpf_remittance: ['fa-piggy-bank', 'blue'],
  iit_withholding: ['fa-receipt', 'rose'], iit_annual: ['fa-file-contract', 'orange'], social_insurance: ['fa-shield-heart', 'cyan'],
};

function statutoryCard() {
  // 容器先占位,实际表单按当前公司所属国家异步加载
  setTimeout(() => loadStatutoryForms(), 0);
  return `<div class="panel p-5 lg:col-span-3 mt-1">
    <div class="font-semibold text-slate-800 mb-1 flex items-center gap-2">
      <span data-i18n="report.statutory_title">${t('report.statutory_title')}</span>
      <span id="stat-country-tag" class="text-[11px] font-normal px-2 py-0.5 rounded-full bg-teal-50 text-teal-600"></span></div>
    <p class="text-xs text-slate-500 mb-3" data-i18n="report.statutory_desc">${t('report.statutory_desc')}</p>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3" id="stat-forms-grid">
      <div class="text-sm text-slate-400 col-span-3"><i class="fas fa-spinner fa-spin"></i> ...</div>
    </div>
    <p class="text-[11px] text-slate-400 mt-3"><i class="fas fa-circle-info"></i> <span data-i18n="report.statutory_note">${t('report.statutory_note')}</span></p>
    <p class="text-[11px] mt-1" id="stat-export-fb"></p>
    ${importCard()}</div>`;
}

// 按当前公司所属国家加载法定报表清单(切换公司时调用)
async function loadStatutoryForms() {
  const grid = $('#stat-forms-grid');
  if (!grid) return;
  const data = await api(`/api/statutory/forms?company=${effCompany()}`);
  const tag = $('#stat-country-tag');
  if (tag && data.country) tag.textContent = data.country;
  const forms = data.forms || [];
  grid.innerHTML = forms.map(f => {
    const [icon, color] = STAT_FORM_ICON[f.id] || ['fa-file-lines', 'slate'];
    const nm = S.lang === 'en' ? f.name_en : f.name_zh;
    const desc = f.name_en;
    return `
    <button class="stat-form-btn" onclick="exportStatutory('${f.id}')" id="stat-btn-${f.id}">
      <i class="fas ${icon} text-${color}-500 text-xl"></i>
      <div class="stat-form-name">${nm}</div>
      <div class="stat-form-desc">${desc}</div>
      <i class="fas fa-download stat-form-dl"></i>
      ${f.id === 'ea_form' ? `<span class="ea-pdf-badge" onclick="event.stopPropagation(); exportStatutory('ea_form','pdf')" title="${t('report.ea_pdf')}"><i class="fas fa-file-pdf"></i> ${t('report.ea_pdf')}</span>` : ''}
    </button>`;
  }).join('');
}
window.loadStatutoryForms = loadStatutoryForms;

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

// ════════ AI 老板驾驶舱 ① + AI 异常稽查 ④ ════════
let _cockpitCharts = [];
async function renderCockpit() {
  const view = $('#view');
  const roleId = (S.role && S.role.id) || 'finance';
  const lang = S.lang;
  view.innerHTML = `<div class="cockpit-head">
    <div><h1 class="page-title flex items-center gap-2"><i class="fas fa-gauge-high text-teal-500"></i> ${t('cockpit.title')}</h1>
      <p class="text-sm text-slate-400 mt-0.5">${S.company.flag} ${nameOf(S.company)} · <span data-i18n="cockpit.sub">${t('cockpit.sub')}</span></p></div>
    <div class="cockpit-health" id="ck-health"><div class="ck-health-ring" id="ck-ring"><span id="ck-health-num">··</span></div>
      <div class="text-xs text-slate-400 mt-1" data-i18n="cockpit.health">${t('cockpit.health')}</div></div>
  </div>
  <div id="ck-ai" class="cockpit-ai"><div class="ck-ai-icon"><i class="fas fa-robot"></i></div>
    <div class="ck-ai-body"><div class="ck-ai-title"><span data-i18n="cockpit.ai_title">${t('cockpit.ai_title')}</span></div>
      <div class="ck-ai-text" id="ck-ai-text">${t('cockpit.loading')}</div>
      <div class="ck-ai-factors" id="ck-ai-factors"></div></div></div>
  <div class="cockpit-kpis" id="ck-kpis"></div>
  <div class="cockpit-grid">
    <div class="panel p-5"><div class="ck-card-title"><i class="fas fa-chart-line text-teal-500"></i> <span data-i18n="cockpit.trend">${t('cockpit.trend')}</span></div>
      <div class="ck-chart-wrap"><canvas id="ck-trend"></canvas></div></div>
    <div class="panel p-5"><div class="ck-card-title"><i class="fas fa-chart-pie text-indigo-500"></i> <span data-i18n="cockpit.dept">${t('cockpit.dept')}</span></div>
      <div class="ck-chart-wrap"><canvas id="ck-dept"></canvas></div></div>
  </div>
  <div class="panel p-5 mt-4"><div class="ck-card-title"><i class="fas fa-triangle-exclamation text-amber-500"></i> <span data-i18n="cockpit.anomaly">${t('cockpit.anomaly')}</span>
    <span class="ck-anom-counts" id="ck-anom-counts"></span></div>
    <div id="ck-anom-list" class="ck-anom-list">${t('cockpit.loading')}</div></div>`;

  const c = S.company.id, m = '2026-05';
  const [ov, an, ex] = await Promise.all([
    api(`/api/cockpit/overview?company=${c}&month=${m}&lang=${lang}&role=${roleId}`),
    api(`/api/cockpit/anomalies?company=${c}&month=${m}&role=${roleId}`),
    api(`/api/cockpit/explain?company=${c}&month=${m}&lang=${lang}&role=${roleId}`),
  ]);
  if (ov.denied || !ov.ok) { $('#ck-ai-text').textContent = (ov.message || t('cockpit.denied')); return; }
  // 法定体系徽章: 让"全球合规护城河"可见(CPF / 五险一金 / MPF / SSF…)
  if (ov.scheme) {
    const badge = document.createElement('span');
    badge.className = 'ck-scheme-badge';
    badge.innerHTML = `<i class="fas fa-shield-halved"></i> ${ov.currency} · ${ov.scheme}`;
    const sub = view.querySelector('.cockpit-head p');
    if (sub) sub.appendChild(badge);
  }
  drawCockpitKpis(ov);
  drawCockpitAI(ex);
  drawCockpitHealth(an.health_score);
  drawCockpitAnomalies(an);
  drawCockpitCharts(ov);
}

// 驾驶舱货币前缀:跟随后端返回的公司币种(RM/¥/HK$/S$/฿/₫/Rp),不再统一 RM
function ckPrefix(ov) { return (ov && ov.currency_prefix) || 'RM'; }
function fmtCur(v, prefix) { return (prefix || 'RM') + Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 }); }
function momBadge(mom) {
  if (!mom) return `<span class="ck-mom flat">0%</span>`;
  const up = mom > 0;
  return `<span class="ck-mom ${up ? 'up' : 'down'}"><i class="fas fa-arrow-${up ? 'up' : 'down'}"></i> ${Math.abs(mom)}%</span>`;
}
function drawCockpitKpis(ov) {
  const order = ['total_cost', 'gross', 'net', 'employer_contrib', 'hrdf', 'pcb', 'ot', 'headcount'];
  const icons = { total_cost: 'fa-sack-dollar', gross: 'fa-money-bill-wave', net: 'fa-hand-holding-dollar', employer_contrib: 'fa-building', hrdf: 'fa-graduation-cap', pcb: 'fa-landmark', ot: 'fa-clock', headcount: 'fa-users' };
  const hero = ['total_cost'];
  const lang = S.lang;
  const pfx = ckPrefix(ov);
  $('#ck-kpis').innerHTML = order.map(k => {
    const kp = ov.kpis[k]; if (!kp) return '';
    const val = k === 'headcount' ? kp.value : fmtCur(kp.value, pfx);
    const lbl = lang === 'en' ? kp.label_en : kp.label_zh;
    return `<div class="ck-kpi ${hero.includes(k) ? 'hero' : ''}">
      <div class="ck-kpi-top"><i class="fas ${icons[k]}"></i>${k === 'headcount' ? '' : momBadge(kp.mom)}</div>
      <div class="ck-kpi-val">${val}</div><div class="ck-kpi-lbl">${lbl}</div></div>`;
  }).join('') + `<div class="ck-kpi soft"><div class="ck-kpi-top"><i class="fas fa-user-tag"></i></div>
      <div class="ck-kpi-val">${fmtCur(ov.cost_per_head, pfx)}</div><div class="ck-kpi-lbl">${t('cockpit.per_head')}</div></div>`;
}
function drawCockpitAI(ex) {
  $('#ck-ai-text').textContent = ex.summary || '';
  const pfx = (ex && ex.currency_prefix) || 'RM';
  const top = (ex.factors || []).slice(0, 4);
  $('#ck-ai-factors').innerHTML = top.map(f => {
    const lbl = S.lang === 'en' ? f.label_en : f.label_zh;
    const up = f.delta > 0;
    return `<span class="ck-factor ${up ? 'up' : 'down'}">${lbl} ${up ? '+' : ''}${fmtCur(f.delta, pfx)} <em>${f.share}%</em></span>`;
  }).join('');
}
function drawCockpitHealth(score) {
  const ring = $('#ck-ring'); $('#ck-health-num').textContent = score;
  const col = score >= 85 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
  ring.style.background = `conic-gradient(${col} ${score * 3.6}deg, #e2e8f0 0deg)`;
}
function drawCockpitAnomalies(an) {
  const cc = an.counts || {};
  $('#ck-anom-counts').innerHTML =
    `<span class="ck-cnt crit">${cc.critical || 0} ${t('cockpit.sev_crit')}</span>
     <span class="ck-cnt warn">${cc.warning || 0} ${t('cockpit.sev_warn')}</span>
     <span class="ck-cnt info">${cc.info || 0} ${t('cockpit.sev_info')}</span>`;
  const list = an.anomalies || [];
  if (!list.length) { $('#ck-anom-list').innerHTML = `<div class="ck-anom-empty"><i class="fas fa-circle-check text-emerald-500"></i> ${t('cockpit.no_anomaly')}</div>`; return; }
  $('#ck-anom-list').innerHTML = list.map(a => `
    <div class="ck-anom ${a.severity}">
      <div class="ck-anom-dot"></div>
      <div class="ck-anom-main"><div class="ck-anom-title">${a.title} <span class="ck-anom-who">${a.subject}</span></div>
        <div class="ck-anom-detail">${a.detail}</div></div>
      <span class="ck-anom-tag ${a.severity}">${t('cockpit.sev_' + (a.severity === 'critical' ? 'crit' : a.severity === 'warning' ? 'warn' : 'info'))}</span>
    </div>`).join('');
}
function drawCockpitCharts(ov) {
  _cockpitCharts.forEach(ch => { try { ch.destroy(); } catch (e) {} });
  _cockpitCharts = [];
  const lang = S.lang;
  const pfx = ckPrefix(ov);
  // 趋势: 总成本(柱) + 加班(线)
  const tr = ov.trend;
  _cockpitCharts.push(new Chart($('#ck-trend'), {
    data: {
      labels: tr.map(r => r.month),
      datasets: [
        { type: 'bar', label: lang === 'en' ? 'Total Cost' : '企业总成本', data: tr.map(r => r.total_cost), backgroundColor: 'rgba(15,118,110,.85)', borderRadius: 6, order: 2 },
        { type: 'line', label: lang === 'en' ? 'Overtime' : '加班成本', data: tr.map(r => r.ot), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,.15)', tension: .35, fill: true, yAxisID: 'y1', order: 1 },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { font: { size: 11 } } } },
      scales: { y: { beginAtZero: true, ticks: { callback: v => pfx + (v / 1000) + 'k' } }, y1: { position: 'right', grid: { drawOnChartArea: false }, beginAtZero: true } } },
  }));
  // 部门分布(环图)
  const dp = ov.departments;
  const palette = ['#0f766e', '#20c997', '#3b82f6', '#8b5cf6', '#f59e0b', '#ec4899'];
  _cockpitCharts.push(new Chart($('#ck-dept'), {
    type: 'doughnut',
    data: { labels: dp.map(d => d.dept), datasets: [{ data: dp.map(d => d.total_cost), backgroundColor: palette, borderWidth: 2, borderColor: '#fff' }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '58%',
      plugins: { legend: { position: 'bottom', labels: { font: { size: 10 }, boxWidth: 12 } },
        tooltip: { callbacks: { label: ctx => `${ctx.label}: ${fmtCur(ctx.raw, pfx)}` } } } },
  }));
}
window.renderCockpit = renderCockpit;

function selfClaimView(m) {
  const b = m.balance;
  // 手机端(员工)货币统一锁定为 RM,与额度卡/薪资单/个人中心保持一致
  if (isMobileMode()) b.currency = 'RM';
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
          <input class="ac-input w-24" id="cf-currency" placeholder="${b.currency || 'RM'}" value="${b.currency || 'RM'}">
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
    const m = await fetch(`/api/module/family?company=${effCompany()}&lang=${S.lang}`).then(x => x.json());
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
    const types = await fetch(`/api/claim_types?company=${effCompany()}`).then(r => r.json()).then(x => x.types || []);
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
    const d = await fetch(`/api/claims?company=${effCompany()}`).then(r => r.json());
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
    company: effCompany(), type_code: typeCode, amount: amount,
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
      const r = await api('/api/ocr', { company: effCompany(), image_b64: b64, mime: file.type || 'image/jpeg' });
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

// ════════ AI 助手·对话式拍照识别 ════════
// 暂存最近一次 AI 识别结果,供"一键填入报销单"复用
let _aiLastOcr = null;
async function aiOcrUpload(ev) {
  const file = ev.target.files && ev.target.files[0];
  ev.target.value = '';                 // 允许重复选同一文件
  if (!file) return;
  // 确保对话已初始化(若用户直接点相机而未发过消息)
  if (!$('#ai-messages').dataset.init) { selectAgent(S.currentAgent); $('#ai-messages').dataset.init = '1'; }
  const reader = new FileReader();
  reader.onload = async () => {
    const b64 = String(reader.result);
    // 1) 用户气泡:显示上传的票据缩略图
    $('#ai-messages').insertAdjacentHTML('beforeend',
      `<div class="msg-user"><div class="bubble" style="padding:6px"><img src="${b64}" alt="票据" style="max-width:160px;border-radius:9px;display:block"><div class="text-xs opacity-80 mt-1">${t('ai.cam_uploaded')}</div></div></div>`);
    aiScroll();
    // 2) AI 识别中动效
    const tid = 'ocr' + Date.now();
    $('#ai-messages').insertAdjacentHTML('beforeend',
      `<div class="msg-ai"><span class="text-lg mt-0.5">${(S.currentAgent && S.currentAgent.emoji) || '🤖'}</span><div class="flex-1"><div class="think-box" id="${tid}"><div class="text-slate-400"><span class="think-dot">●</span> ${t('ai.cam_reading')}</div></div></div></div>`);
    aiScroll();
    try {
      const r = await api('/api/ocr', { company: effCompany(), image_b64: b64, mime: file.type || 'image/jpeg' });
      const ext = r.extracted || {};
      _aiLastOcr = ext;
      const note = (r.engine_note && (S.lang === 'en' ? r.engine_note.en : r.engine_note.zh)) || '';
      const tn = typeNameByCode(ext.type_code) || ext.category || '-';
      // 3) 识别结果卡片 + 一键填入按钮
      const rows = [
        [t('claim.f_type'), tn],
        [t('claim.f_merchant'), ext.merchant || '-'],
        [t('claim.f_amount'), (ext.amount != null ? ext.amount : '-') + ' ' + (isMobileMode() ? 'RM' : (ext.currency || 'RM'))],
        [t('claim.f_date'), ext.date || '-'],
      ].map(([k, v]) => `<div class="flex justify-between py-0.5"><span class="text-slate-400">${k}</span><b>${v}</b></div>`).join('');
      const cid = 'aiocr' + Date.now();
      $('#' + tid).closest('.msg-ai').remove();
      $('#ai-messages').insertAdjacentHTML('beforeend',
        `<div class="msg-ai"><span class="text-lg mt-0.5">${(S.currentAgent && S.currentAgent.emoji) || '🤖'}</span><div class="flex-1 space-y-2">
          <div class="bubble">${(r.engine === 'vision' ? '✅ ' : 'ℹ️ ')}${esc(note)} —— ${t('ai.cam_done')}</div>
          <div class="ai-card" id="${cid}"><div class="ai-card-head"><i class="fas fa-receipt text-teal-500"></i> ${t('ai.cam_card_title')}</div>
            <div class="ai-card-body">${rows}
              <button class="btn btn-primary w-full justify-center mt-3" onclick="aiFillClaim()"><i class="fas fa-wand-magic-sparkles"></i> ${t('ai.cam_fill')}</button>
            </div></div></div></div>`);
      aiScroll();
    } catch (e) {
      const box = $('#' + tid);
      if (box) box.innerHTML = `<div class="text-rose-400"><i class="fas fa-triangle-exclamation"></i> ${t('claim.ocr_err')}</div>`;
    }
  };
  reader.readAsDataURL(file);
}
// 一键:跳到自助报销页并把 AI 识别结果回填进表单
function aiFillClaim() {
  if (!_aiLastOcr) return;
  const ext = _aiLastOcr;
  toggleAI(false);
  // 进入自助报销模块(员工→my_claim)
  if (isMobileMode()) { mobileGo('my_claim'); } else { go('my_claim'); }
  // 等模块渲染完成再回填(loadClaimTypes 异步拉下拉项)
  setTimeout(() => {
    const set = (id, v) => { const e = document.getElementById(id); if (e && v != null && v !== '') e.value = v; };
    set('cf-type', ext.type_code);
    set('cf-merchant', ext.merchant);
    set('cf-amount', ext.amount);
    if (!isMobileMode()) set('cf-currency', ext.currency);
    set('cf-date', ext.date);
    if (ext.tax_no) set('cf-receipt', ext.tax_no);
    const fb = document.getElementById('cf-feedback');
    if (fb) acFlash(fb, t('ai.cam_filled'), false);
    const drop = document.getElementById('ocr-drop');
    if (drop) drop.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 700);
}
// 按 type_code 找类型名(回填卡片展示用)
function typeNameByCode(code) {
  if (!code) return '';
  const sel = document.getElementById('cf-type');
  if (sel) { const o = [...sel.options].find(x => x.value === code); if (o) return o.textContent.replace(/\s*\(.*\)$/, ''); }
  return code;
}

window.loadClaimTypes = loadClaimTypes;
window.refreshClaims = refreshClaims;
window.submitClaim = submitClaim;
window.ocrUpload = ocrUpload;
window.aiOcrUpload = aiOcrUpload;
window.aiFillClaim = aiFillClaim;

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
// 有效公司ID:员工(手机端)演示员工隶属马来西亚公司,所有数据源强制锁 my,
// 保证额度/报销记录/类型/薪资/AI 对话全链路同一套真实数据(RM)。
function effCompany() { return isMobileMode() ? 'my' : (S.company ? S.company.id : 'group'); }
window.effCompany = effCompany;
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
  { nav: 'my_claim', icon: 'fa-receipt', key: 'm.tab_claim' },
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
    // '我的' tab 在个人中心或薪资单详情页都保持高亮
    const active = (tb.nav === '__me')
      ? (S.currentNav === '__me' || S.currentNav === '__payslip')
      : (S.currentNav === tb.nav);
    return `<button class="mtab ${active ? 'active' : ''}" onclick="mobileGo('${tb.nav}')">
      <i class="fas ${tb.icon}"></i><span>${t(tb.key)}</span></button>`;
  }).join('') +
    `<button class="mtab mtab-ai" onclick="openAI('ClaimMate')"><i class="fas fa-robot"></i><span>${t('m.tab_ai')}</span></button>`;
}
function mobileGo(nav) {
  if (nav === '__me') { S.currentNav = '__me'; renderMeView(); renderTabbar(); return; }
  if (nav === '__payslip') { S.currentNav = '__payslip'; renderMyPayslip(); renderTabbar(); return; }
  go(nav); renderTabbar();
}
window.mobileGo = mobileGo;
// 金额格式(带 2 位小数,本地货币符号)
function fmtMoney(v, cur) { return (cur || 'RM') + ' ' + Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

// ════════ 员工手机首页(轻量·非管理者大屏) ════════
async function renderMobileHome() {
  const c = S.company;
  const hour = new Date().getHours();
  const greet = hour < 12 ? t('mh.morning') : (hour < 18 ? t('mh.afternoon') : t('mh.evening'));
  // 骨架
  $('#view').innerHTML = `<div class="mh-page">
    <div class="mh-greet">
      <div class="mh-greet-hi" id="mh-hi">${greet}</div>
      <div class="mh-greet-sub" id="mh-sub">${c.flag} ${nameOf(c)}</div>
    </div>
    <div id="mh-body"><div class="me-loading"><i class="fas fa-spinner fa-spin"></i> ${t('common.loading')}</div></div>
  </div>`;
  try {
    const s = await api(`/api/me/summary?role=${S.role.id}&company=${S.company.id}`);
    if (!s || !s.ok) { $('#mh-body').innerHTML = mhActions(); return; }
    $('#mh-hi').textContent = `${greet},${s.emp.name.split(' ')[0]}`;
    $('#mh-sub').textContent = `${s.emp.designation} · ${s.emp.dept}`;
    drawMobileHome(s);
  } catch (e) { const b = $('#mh-body'); if (b) b.innerHTML = mhActions(); }
}
window.renderMobileHome = renderMobileHome;
function drawMobileHome(s) {
  const body = $('#mh-body'); if (!body) return;
  const cur = s.balance.currency || 'RM';
  const cs = s.claims.by_status || {};
  body.innerHTML = `
    <!-- 薪资速览(可点进薪资单) -->
    <div class="mh-pay" onclick="mobileGo('__payslip')">
      <div class="mh-pay-l">
        <div class="mh-pay-label">${t('me.net_this_month')} · ${s.payslip.month}</div>
        <div class="mh-pay-val">${fmtMoney(s.payslip.net_pay, cur)}</div>
      </div>
      <i class="fas fa-chevron-right mh-pay-arr"></i>
    </div>

    ${s.todos > 0 ? `<div class="me-todo" onclick="mobileGo('my_claim')">
      <i class="fas fa-bell"></i><span>${t('me.todo_prefix')} <b>${s.todos}</b> ${t('me.todo_suffix')}</span>
      <i class="fas fa-chevron-right me-arr"></i></div>` : ''}

    <!-- 快捷操作四宫格 -->
    <div class="mh-actions">
      <div class="mh-act" onclick="openAI('ClaimMate','我要拍照报销')">
        <div class="mh-act-ico" style="background:#ecfdf5;color:#059669"><i class="fas fa-camera"></i></div>
        <span>${t('mh.act_photo')}</span></div>
      <div class="mh-act" onclick="mobileGo('my_claim')">
        <div class="mh-act-ico" style="background:#eff6ff;color:#2563eb"><i class="fas fa-receipt"></i></div>
        <span>${t('mh.act_claim')}</span></div>
      <div class="mh-act" onclick="mobileGo('__payslip')">
        <div class="mh-act-ico" style="background:#fffbeb;color:#d97706"><i class="fas fa-file-invoice-dollar"></i></div>
        <span>${t('me.my_payslip')}</span></div>
      <div class="mh-act" onclick="openAI('ClaimMate','帮我登记家属信息')">
        <div class="mh-act-ico" style="background:#eef2ff;color:#6366f1"><i class="fas fa-users"></i></div>
        <span>${t('m.me_family')}</span></div>
    </div>

    <!-- 我的报销近况 -->
    <div class="mh-card">
      <div class="mh-card-title"><i class="fas fa-chart-simple text-teal-500"></i> ${t('mh.claim_status')}</div>
      <div class="me-stats" style="margin:0">
        <div class="me-stat" onclick="mobileGo('my_claim')"><div class="me-stat-n">${cs.pending || 0}</div><div class="me-stat-l">${t('me.st_pending')}</div></div>
        <div class="me-stat" onclick="mobileGo('my_claim')"><div class="me-stat-n text-emerald-500">${cs.approved || 0}</div><div class="me-stat-l">${t('me.st_approved')}</div></div>
        <div class="me-stat" onclick="mobileGo('my_claim')"><div class="me-stat-n text-sky-500">${cs.paid || 0}</div><div class="me-stat-l">${t('me.st_paid')}</div></div>
        <div class="me-stat" onclick="mobileGo('my_claim')"><div class="me-stat-n text-rose-400">${cs.rejected || 0}</div><div class="me-stat-l">${t('me.st_rejected')}</div></div>
      </div>
    </div>

    <!-- 年度额度 -->
    <div class="me-quota" style="margin-bottom:0">
      <div class="me-quota-head"><span><i class="fas fa-wallet text-emerald-500"></i> ${t('me.annual_quota')}</span>
        <span class="me-quota-rem">${fmtMoney(s.balance.remaining, cur)}</span></div>
      <div class="me-quota-bar"><div class="me-quota-fill" style="width:${s.balance.annual ? Math.min(100, s.balance.used / s.balance.annual * 100) : 0}%"></div></div>
      <div class="me-quota-foot">${t('claim.used')} ${fmtMoney(s.balance.used, cur)} / ${fmtMoney(s.balance.annual, cur)}</div>
    </div>`;
}
function mhActions() {
  return `<div class="mh-actions">
      <div class="mh-act" onclick="openAI('ClaimMate','我要拍照报销')"><div class="mh-act-ico" style="background:#ecfdf5;color:#059669"><i class="fas fa-camera"></i></div><span>${t('mh.act_photo')}</span></div>
      <div class="mh-act" onclick="mobileGo('my_claim')"><div class="mh-act-ico" style="background:#eff6ff;color:#2563eb"><i class="fas fa-receipt"></i></div><span>${t('mh.act_claim')}</span></div>
      <div class="mh-act" onclick="mobileGo('__payslip')"><div class="mh-act-ico" style="background:#fffbeb;color:#d97706"><i class="fas fa-file-invoice-dollar"></i></div><span>${t('me.my_payslip')}</span></div>
      <div class="mh-act" onclick="$('#role-switch').click()"><div class="mh-act-ico" style="background:#f1f5f9;color:#64748b"><i class="fas fa-right-left"></i></div><span>${t('m.me_switch')}</span></div>
    </div>`;
}

// 「我的」页(移动端个人中心)—— 真数据驱动:薪资卡 + 报销进度 + 待办 + 快捷入口
async function renderMeView() {
  const r = S.role, c = S.company;
  // 先渲染骨架(头像 + 加载态),再异步填真数据
  $('#view').innerHTML = `<div class="me-page">
    <div class="me-hero">
      <div class="me-avatar" style="background:${r.color}"><i class="fas ${r.icon}"></i></div>
      <div class="me-name" id="me-name">${nameOf(r)}</div>
      <div class="me-sub" id="me-sub">${c.flag} ${nameOf(c)}</div>
    </div>
    <div id="me-body">
      <div class="me-loading"><i class="fas fa-spinner fa-spin"></i> ${t('common.loading')}</div>
    </div>
  </div>`;
  try {
    const s = await api(`/api/me/summary?role=${S.role.id}&company=${S.company.id}`);
    if (!s || !s.ok) { drawMeFallback(); return; }
    // 真实姓名/职位
    $('#me-name').textContent = s.emp.name;
    $('#me-sub').textContent = `${c.flag} ${s.emp.designation} · ${s.emp.dept}`;
    drawMeBody(s);
  } catch (e) { drawMeFallback(); }
}
function drawMeFallback() {
  const body = $('#me-body'); if (!body) return;
  body.innerHTML = meQuickLinks();
}
function drawMeBody(s) {
  const body = $('#me-body'); if (!body) return;
  const cur = s.balance.currency || 'RM';
  const usedPct = s.balance.annual ? Math.min(100, s.balance.used / s.balance.annual * 100) : 0;
  const cs = s.claims.by_status || {};
  body.innerHTML = `
    <!-- 本月薪资卡(可点进详情) -->
    <div class="me-paycard" onclick="mobileGo('__payslip')">
      <div class="me-pc-top">
        <span class="me-pc-label">${t('me.net_this_month')}</span>
        <span class="me-pc-month">${s.payslip.month}</span>
      </div>
      <div class="me-pc-net">${fmtMoney(s.payslip.net_pay, cur)}</div>
      <div class="me-pc-sub">
        <span>${t('me.gross')} ${fmtMoney(s.payslip.gross_total, cur)}</span>
        <span>${t('me.deduction')} ${fmtMoney(s.payslip.total_deduction, cur)}</span>
      </div>
      <div class="me-pc-cta"><i class="fas fa-file-invoice-dollar"></i> ${t('me.view_payslip')} <i class="fas fa-chevron-right"></i></div>
    </div>

    <!-- 年度报销额度 -->
    <div class="me-quota">
      <div class="me-quota-head">
        <span><i class="fas fa-wallet text-emerald-500"></i> ${t('me.annual_quota')}</span>
        <span class="me-quota-rem">${fmtMoney(s.balance.remaining, cur)}</span>
      </div>
      <div class="me-quota-bar"><div class="me-quota-fill" style="width:${usedPct}%"></div></div>
      <div class="me-quota-foot">${t('claim.used')} ${fmtMoney(s.balance.used, cur)} / ${fmtMoney(s.balance.annual, cur)}</div>
    </div>

    <!-- 报销进度统计(真库) -->
    <div class="me-stats">
      <div class="me-stat" onclick="mobileGo('my_claim')">
        <div class="me-stat-n">${cs.pending || 0}</div><div class="me-stat-l">${t('me.st_pending')}</div></div>
      <div class="me-stat" onclick="mobileGo('my_claim')">
        <div class="me-stat-n text-emerald-500">${cs.approved || 0}</div><div class="me-stat-l">${t('me.st_approved')}</div></div>
      <div class="me-stat" onclick="mobileGo('my_claim')">
        <div class="me-stat-n text-sky-500">${cs.paid || 0}</div><div class="me-stat-l">${t('me.st_paid')}</div></div>
      <div class="me-stat" onclick="mobileGo('my_claim')">
        <div class="me-stat-n text-rose-400">${cs.rejected || 0}</div><div class="me-stat-l">${t('me.st_rejected')}</div></div>
    </div>

    ${s.todos > 0 ? `<div class="me-todo" onclick="mobileGo('my_claim')">
      <i class="fas fa-bell"></i> <span>${t('me.todo_prefix')} <b>${s.todos}</b> ${t('me.todo_suffix')}</span>
      <i class="fas fa-chevron-right me-arr"></i></div>` : ''}

    ${meQuickLinks(s)}`;
}
function meQuickLinks(s) {
  const fam = s && s.family_count ? `<span class="me-badge">${s.family_count}</span>` : '';
  return `<div class="me-list">
      <div class="me-item" onclick="mobileGo('__payslip')"><i class="fas fa-file-invoice-dollar text-amber-500"></i><span>${t('me.my_payslip')}</span><i class="fas fa-chevron-right me-arr"></i></div>
      <div class="me-item" onclick="mobileGo('my_claim')"><i class="fas fa-receipt text-teal-500"></i><span>${t('m.me_claims')}</span><i class="fas fa-chevron-right me-arr"></i></div>
      <div class="me-item" onclick="openAI('ClaimMate','我还能报多少额度?')"><i class="fas fa-robot text-emerald-500"></i><span>${t('me.ask_ai_quota')}</span><i class="fas fa-chevron-right me-arr"></i></div>
      <div class="me-item" onclick="openAI('ClaimMate','帮我登记家属信息')"><i class="fas fa-users text-indigo-500"></i><span>${t('m.me_family')}</span>${fam}<i class="fas fa-chevron-right me-arr"></i></div>
      <div class="me-item" onclick="$('#help-btn').click()"><i class="fas fa-circle-question text-slate-400"></i><span>${t('help.open')}</span><i class="fas fa-chevron-right me-arr"></i></div>
      <div class="me-item" onclick="$('#role-switch').click()"><i class="fas fa-right-left text-slate-400"></i><span>${t('m.me_switch')}</span><i class="fas fa-chevron-right me-arr"></i></div>
    </div>`;
}

// 「我的薪资单」详情页(手机友好:收入/扣除明细 + 实发)
async function renderMyPayslip() {
  $('#view').innerHTML = `<div class="me-page"><div class="me-loading"><i class="fas fa-spinner fa-spin"></i> ${t('common.loading')}</div></div>`;
  try {
    const p = await api(`/api/me/payslip?role=${S.role.id}`);
    if (!p || !p.ok) { $('#view').innerHTML = `<div class="me-page"><div class="me-loading">${t('cockpit.denied')}</div></div>`; return; }
    const cur = 'RM';
    const earn = p.earnings.map(e => `<div class="ps-row"><span>${S.lang === 'en' ? e.label_en : e.label_zh}</span><span class="ps-amt">${fmtMoney(e.amount, cur)}</span></div>`).join('');
    const ded = p.deductions.map(d => `<div class="ps-row"><span>${S.lang === 'en' ? d.label_en : d.label_zh}</span><span class="ps-amt ps-neg">- ${fmtMoney(d.amount, cur)}</span></div>`).join('');
    $('#view').innerHTML = `<div class="me-page ps-page">
      <div class="ps-back" onclick="mobileGo('__me')"><i class="fas fa-chevron-left"></i> ${t('me.back')}</div>
      <div class="ps-head">
        <div class="ps-title">${t('me.payslip_title')}</div>
        <div class="ps-month">${p.month}</div>
        <div class="ps-emp">${p.emp.name} · ${p.emp.designation}</div>
        <div class="ps-emp-sub">${p.emp.emp_no} · ${p.emp.dept}</div>
      </div>
      <div class="ps-net-card">
        <div class="ps-net-label">${t('me.net_pay')}</div>
        <div class="ps-net-val">${fmtMoney(p.net_pay, cur)}</div>
        <div class="ps-net-bank"><i class="fas fa-building-columns"></i> ${p.emp.bank_code || '—'} · ****${(p.emp.bank_acct || '').slice(-4)}</div>
      </div>
      <div class="ps-section">
        <div class="ps-sec-title"><i class="fas fa-plus-circle text-emerald-500"></i> ${t('me.earnings')}</div>
        ${earn}
        <div class="ps-row ps-total"><span>${t('me.gross_total')}</span><span class="ps-amt">${fmtMoney(p.gross_total, cur)}</span></div>
      </div>
      <div class="ps-section">
        <div class="ps-sec-title"><i class="fas fa-minus-circle text-rose-400"></i> ${t('me.deductions')}</div>
        ${ded}
        <div class="ps-row ps-total"><span>${t('me.total_deduction')}</span><span class="ps-amt ps-neg">- ${fmtMoney(p.total_deduction, cur)}</span></div>
      </div>
      <div class="ps-note"><i class="fas fa-shield-halved text-emerald-400"></i> ${t('me.payslip_note')}</div>
    </div>`;
  } catch (e) { $('#view').innerHTML = `<div class="me-page"><div class="me-loading">${t('claim.load_err')}</div></div>`; }
}
window.renderMyPayslip = renderMyPayslip;

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
  const es = new EventSource(`/api/chat/stream?message=${encodeURIComponent(text)}&thread_id=${S.threadId}&company=${effCompany()}&role=${S.role.id}`);
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
  else if (card.type === 'upload_action') {
    const hint = S.lang === 'en' ? (d.hint_en || d.hint) : d.hint;
    const btn = S.lang === 'en' ? (d.btn_en || d.btn) : d.btn;
    body = `<div class="text-sm text-slate-500 mb-3 leading-relaxed">${esc(hint || '')}</div>
      <button class="btn btn-primary w-full justify-center" onclick="document.getElementById('ai-cam-file').click()"><i class="fas fa-camera"></i> ${esc(btn || t('ai.cam_btn'))}</button>`;
  }
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

// Tax 家族横滚 Tab → 对应模块 navId(无模块者为 null = 建设中)
const TAX_TAB_NAV = {
  'EPF Rate': null, 'SOCSO Rate': null, 'EIS Rate': null,
  'Tax Rate Table': 'tax_rate', 'Tax Parameters': 'tax_param',
  'Tax Exemption (TP1)': 'tax_tp1', 'Tax Receipt': 'tax_receipt',
  'EA Setting': 'ea_setting', 'EC Setting': 'ec_setting',
};
// 横滚 Tab 群(Tax 家族顶部)—— 可点击切换子模块
function topTabsBar(m) {
  const act = m.tabs_active ?? 0;
  return `<div class="ptab-bar mb-4">
    ${m.tabs_top.map((tab, i) => {
      const nav = TAX_TAB_NAV[tab];
      const clickable = !!nav;
      const onclick = clickable ? `onclick="go('${nav}')"` : `onclick="toast('${tab} ' + (t('tax.tab_wip')||'功能建设中'))"`;
      return `<div class="ptab ${i === act ? 'active' : ''} ${clickable ? 'ptab-clk' : 'ptab-wip'}" ${onclick}>${tab}</div>`;
    }).join('')}
  </div>`;
}

// 单个表单字段渲染(全部真可编辑:ro 禁用,其余 input/select/radio 真控件)
function pField(f, idx) {
  const req = f.req ? '<span class="text-rose-500">*</span>' : '';
  const dispLabel = (typeof fieldLabel === 'function') ? fieldLabel(f.label_en || f.label) : (f.label_en || f.label);
  const lbl = `<label class="pf-label">${dispLabel} ${req}</label>`;
  let ctrl = '';
  const unit = f.unit ? `<span class="pf-unit">${f.unit}</span>` : '';
  // data-label 用原始(英文)label 作为落库 key,保证多语言下 key 一致
  const keyLabel = f.label_key || f.label_en || f.label || '';
  const fid = (idx != null ? `data-pf="${idx}" ` : '') + `data-label="${esc(keyLabel)}"`;
  if (f.type === 'ro')
    ctrl = `<input class="pf-input pf-ro" value="${esc(f.value)}" ${fid} readonly>`;
  else if (f.type === 'dd')
    ctrl = `<select class="pf-input pf-realselect" ${fid}>${(f.opts || []).map(o =>
      `<option ${o === f.value ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
  else if (f.type === 'date')
    ctrl = `<div class="pf-wunit"><input type="date" class="pf-input" value="${esc(f.value)}" ${fid}></div>`;
  else if (f.type === 'num')
    ctrl = `<div class="pf-wunit"><input type="text" inputmode="decimal" class="pf-input pf-num" value="${esc(f.value)}" ${fid}>${unit}</div>`;
  else if (f.type === 'radio')
    ctrl = `<div class="flex gap-2 flex-wrap pf-radiogrp" ${fid}>${(f.opts || ['Yes', 'No']).map((o, i) =>
      `<label class="pf-radio ${(f.value ? o === f.value : i === 0) ? 'active' : ''}" onclick="pfRadioPick(this)"><span class="pf-dot"></span>${o}</label>`).join('')}</div>`;
  else if (f.type === 'area')
    ctrl = `<textarea class="pf-area" placeholder="${esc(f.hint || '请输入…')}" ${fid}>${esc(f.value || '')}</textarea>`;
  else if (f.type === 'time')
    ctrl = `<div class="pf-wunit"><input type="time" class="pf-input" value="${esc(f.value)}" ${fid}></div>`;
  else
    ctrl = `<input class="pf-input" value="${esc(f.value)}" ${fid}>`;
  return `<div class="pf-cell">${lbl}${ctrl}${f.hint && f.type !== 'area' ? `<span class="pf-hint">${f.hint}</span>` : ''}</div>`;
}

// radio 单选切换
function pfRadioPick(el) {
  const grp = el.parentElement;
  grp.querySelectorAll('.pf-radio').forEach(r => r.classList.remove('active'));
  el.classList.add('active');
}
window.pfRadioPick = pfRadioPick;

// 表单字段网格
function pFieldGrid(fields) {
  return `<div class="pf-grid">${(fields || []).map((f, i) => pField(f, i)).join('')}</div>`;
}

// 底部 Back / Save Changes 行(真保存反馈)
function pFooter(saveLabel, onSave) {
  const cb = onSave || 'pfSaveDefault(this)';
  return `<div class="flex items-center justify-end gap-3 mt-5 pt-4 border-t border-slate-100">
    <button class="pf-back" onclick="pfBack()">${t('common.back')}</button>
    <button class="btn btn-primary" onclick="${cb}">${saveLabel || t('common.save')}</button>
  </div>`;
}
function pfBack() { go('dashboard'); }
window.pfBack = pfBack;
function pfSaveDefault(btn) {
  const old = btn.innerHTML;
  btn.disabled = true; btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${t('common.saving') || '保存中'}`;
  setTimeout(() => {
    btn.innerHTML = `<i class="fas fa-check"></i> ${t('common.saved') || '已保存'}`;
    toast(t('common.save_ok') || '配置已保存(演示)');
    setTimeout(() => { btn.disabled = false; btn.innerHTML = old; }, 1400);
  }, 500);
}
window.pfSaveDefault = pfSaveDefault;

// 从页面收集所有带 data-label 的控件值 → form{label: value}
function collectHeaderInto(form, root) {
  const scope = root || document;
  scope.querySelectorAll('[data-label]').forEach(el => {
    const key = el.getAttribute('data-label');
    if (!key) return;
    let val;
    if (el.classList.contains('pf-radiogrp')) {
      const a = el.querySelector('.pf-radio.active');
      val = a ? a.textContent.trim() : '';
    } else if (el.tagName === 'SELECT' || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      val = el.value;
    } else { return; }
    form[key] = val;
  });
  return form;
}
function collectForm(root) { return collectHeaderInto({}, root); }
window.collectForm = collectForm;

// 真实保存表单到后端(按 module+company upsert 落库) + 反馈
async function pfSaveForm(btn, moduleId, form) {
  const old = btn.innerHTML;
  btn.disabled = true; btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${t('common.saving') || '保存中'}`;
  try {
    const r = await api('/api/module_form', {
      module_id: moduleId, company: effCompany(), form: form, role: (S.role && S.role.id) || 'hr_admin'
    });
    if (r && r.ok) {
      btn.innerHTML = `<i class="fas fa-check"></i> ${t('common.saved') || '已保存'}`;
      toast((t('common.save_ok2') || '已保存到') + ' ' + (S.company ? nameOf(S.company) : effCompany()));
    } else {
      btn.innerHTML = old; btn.disabled = false;
      toast((r && r.message) || (t('common.save_fail') || '保存失败(权限不足?)'), true);
      return;
    }
  } catch (e) {
    btn.innerHTML = old; btn.disabled = false;
    toast(t('common.save_fail') || '保存失败', true); return;
  }
  setTimeout(() => { btn.disabled = false; btn.innerHTML = old; }, 1400);
}
window.pfSaveForm = pfSaveForm;

// 通用:p_detail/p_tabset 的保存(收集整页 data-label)
function pfSaveCollect(btn) {
  const mid = (S.curModule && S.curModule.id) || S.currentNav;
  pfSaveForm(btn, mid, collectForm());
}
window.pfSaveCollect = pfSaveCollect;

// 分页器 < 1 2 3 >(可点击)
function pPager(pages = 3, cur = 1, onPage) {
  const cb = onPage || 'pfPagerToast';
  let html = `<div class="ppager"><span onclick="${cb}(${Math.max(1, cur - 1)})"><i class="fas fa-angle-left"></i></span>`;
  for (let i = 1; i <= pages; i++) html += `<span class="${i === cur ? 'active' : ''}" onclick="${cb}(${i})">${i}</span>`;
  html += `<span onclick="${cb}(${Math.min(pages, cur + 1)})"><i class="fas fa-angle-right"></i></span></div>`;
  return html;
}
function pfPagerToast(p) { toast((t('common.page') || '第') + ' ' + p + ' ' + (t('common.page_unit') || '页') + '(演示数据仅 1 页)'); }
window.pfPagerToast = pfPagerToast;

// ① 普通详情页(只读主键 + 表单 + Back/Save）
function pDetailView(m) {
  return `<div class="panel p-5 md:p-6">
    ${pFieldGrid(m.fields || [])}
    ${pFooter(t('common.save'), 'pfSaveCollect(this)')}
  </div>`;
}

// 当前 Inline 表运行态(支持切税种 / 行编辑)
let _inlineState = null;

// 渲染 Inline 表的 tbody(可点开行编辑)
function pInlineRows(rows) {
  return rows.map((r, idx) => `<tr data-ri="${idx}">
    ${r.map((c, ci) => ci === 0
      ? `<td class="text-slate-400">${esc(String(c))}</td>`
      : `<td><span class="pf-cellinput" onclick="inlineEditCell(${idx},${ci},this)">${esc(String(c))}</span></td>`).join('')}
    <td class="text-right whitespace-nowrap">
      <button class="pf-rowbtn add" title="${t('common.add')||'新增'}" onclick="inlineAddRow(${idx})"><i class="fas fa-plus"></i></button>
      <button class="pf-rowbtn del" title="${t('common.delete')||'删除'}" onclick="inlineDelRow(${idx})"><i class="fas fa-trash-can"></i></button>
    </td></tr>`).join('');
}

// 单元格点开 → 变 input，失焦/回车回写
function inlineEditCell(ri, ci, span) {
  if (!_inlineState) return;
  const cur = _inlineState.rows[ri][ci];
  const inp = document.createElement('input');
  inp.className = 'pf-cell-edit';
  inp.value = cur;
  const commit = () => {
    _inlineState.rows[ri][ci] = inp.value;
    const s = document.createElement('span');
    s.className = 'pf-cellinput';
    s.textContent = inp.value;
    s.onclick = () => inlineEditCell(ri, ci, s);
    inp.replaceWith(s);
  };
  inp.onblur = commit;
  inp.onkeydown = (e) => { if (e.key === 'Enter') inp.blur(); };
  span.replaceWith(inp);
  inp.focus(); inp.select();
}
window.inlineEditCell = inlineEditCell;

function inlineAddRow(after) {
  if (!_inlineState) return;
  const ncol = _inlineState.rows[0] ? _inlineState.rows[0].length : 5;
  const blank = Array(ncol).fill(''); blank[0] = String(after + 2);
  _inlineState.rows.splice(after + 1, 0, blank);
  _inlineState.rows.forEach((r, i) => r[0] = String(i + 1));
  refreshInlineBody();
}
window.inlineAddRow = inlineAddRow;

function inlineDelRow(ri) {
  if (!_inlineState || _inlineState.rows.length <= 1) { toast(t('tax.min_one_row') || '至少保留一行'); return; }
  _inlineState.rows.splice(ri, 1);
  _inlineState.rows.forEach((r, i) => r[0] = String(i + 1));
  refreshInlineBody();
}
window.inlineDelRow = inlineDelRow;

function refreshInlineBody() {
  const tb = document.querySelector('#inline-tbody');
  if (tb) tb.innerHTML = pInlineRows(_inlineState.rows);
}

// 切换税种(Tax Category）→ 表格换成该税种的累进档
function inlineSwitchCategory(sel) {
  if (!_inlineState || !_inlineState.brackets) return;
  const rows = _inlineState.brackets[sel.value];
  if (rows) { _inlineState.rows = rows.map(r => r.slice()); refreshInlineBody(); }
}
window.inlineSwitchCategory = inlineSwitchCategory;

// ② Inline Table 行编辑(可点开编辑 + 切税种联动 + 增删行 + 分页）
function pInlineView(m) {
  _inlineState = { rows: (m.rows || []).map(r => r.slice()), brackets: m.brackets_all || null };
  // 头字段:Tax Category 用真 <select> 触发切税种
  const head = m.header_fields ? `<div class="mb-5"><div class="pf-grid">${m.header_fields.map(f => {
    if (f.label === 'Tax Category' && m.brackets_all) {
      const opts = (f.opts || []).map(o => `<option ${o === f.value ? 'selected' : ''}>${esc(o)}</option>`).join('');
      return `<div class="pf-cell"><label class="pf-label">${fieldLabel(f.label)} <span class="text-rose-500">*</span></label>
        <select class="pf-input pf-realselect" onchange="inlineSwitchCategory(this)">${opts}</select></div>`;
    }
    return pField(f);
  }).join('')}</div></div>` : '';
  const cols = (m.columns || []).map(c => `<th>${fieldLabel(c)}</th>`).join('') + `<th class="text-right">${t('common.action')}</th>`;
  return `<div class="panel p-5 md:p-6">
    ${head}
    <div class="table-wrap"><table class="dtable">
      <thead><tr>${cols}</tr></thead><tbody id="inline-tbody">${pInlineRows(_inlineState.rows)}</tbody>
    </table></div>
    ${pPager(3, 1)}
    ${pFooter()}
  </div>`;
}

// ③ 列表页(可搜索过滤 + 清除 + 行点击 + 分页)
let _listState = null;
function pListView(m) {
  _listState = { all: (m.rows || []).map(r => r.slice()), cols: m.columns || [] };
  const filters = (m.filters || []).map((f, i) =>
    `<div class="pf-cell"><label class="pf-label">${fieldLabel(f)}</label>
      <input class="pf-input" id="lst-f${i}" placeholder="${t('common.all') || '全部'}" oninput="pListSearch()"></div>`).join('');
  const cols = (m.columns || []).map(c => `<th>${fieldLabel(c)}</th>`).join('');
  const filterPanel = filters ? `<div class="panel p-4 mb-4">
    <div class="flex items-end gap-3 flex-wrap">
      <div class="flex-1 grid grid-cols-2 md:grid-cols-3 gap-3">${filters}</div>
      <label class="flex items-center gap-1.5 text-sm text-slate-600 whitespace-nowrap cursor-pointer" onclick="pfChkToggle(this)"><span class="pf-check"></span> ${t('common.active_only')}</label>
      <div class="flex gap-2"><button class="pf-back" onclick="pListClear()">${t('common.clear')}</button>
        <button class="btn btn-primary" onclick="pListSearch()"><i class="fas fa-magnifying-glass"></i> ${t('common.search')}</button></div>
    </div></div>` : '';
  return `${filterPanel}
    <div class="panel p-1.5"><div class="table-wrap"><table class="dtable">
      <thead><tr>${cols}</tr></thead><tbody id="lst-tbody">${pListRows(_listState.all)}</tbody></table></div>
      <div class="px-3 pb-2" id="lst-pager">${pPager(1, 1)}</div>
    </div>`;
}
function pListRows(rows) {
  if (!rows.length) return `<tr><td colspan="9" class="text-center text-slate-400 py-6"><i class="fas fa-inbox"></i> ${t('common.no_data') || '无匹配数据'}</td></tr>`;
  return rows.map(r => `<tr>${r.map((c, ci) =>
    `<td>${ci === 0 ? `<span class="text-teal-600 font-medium cursor-pointer hover:underline" data-row="${esc(String(r[0]))}" onclick="pListRowOpen(this)">${esc(String(c))}</span>` : badgeCell(c)}</td>`).join('')}</tr>`).join('');
}
function pListRowOpen(el) { toast((t('common.open') || '打开') + ' ' + (el.getAttribute('data-row') || el.textContent || '')); }
window.pListRowOpen = pListRowOpen;
function pListSearch() {
  if (!_listState) return;
  const inputs = [...document.querySelectorAll('[id^="lst-f"]')].map(i => i.value.trim().toLowerCase());
  const filtered = _listState.all.filter(r =>
    inputs.every(q => !q || r.some(cell => String(cell).toLowerCase().includes(q))));
  const tb = document.querySelector('#lst-tbody');
  if (tb) tb.innerHTML = pListRows(filtered);
}
window.pListSearch = pListSearch;
function pListClear() {
  document.querySelectorAll('[id^="lst-f"]').forEach(i => i.value = '');
  pListSearch();
}
window.pListClear = pListClear;
function pfChkToggle(el) { el.querySelector('.pf-check').classList.toggle('on'); }
window.pfChkToggle = pfChkToggle;

// ④ 双栏穿梭框(可双击/点箭头移动项)
let _shuttleState = null;
function pShuttleView(m) {
  _shuttleState = { left: (m.left || []).slice(), right: (m.right || []).slice(), sel: { l: null, r: null } };
  const head = m.header_fields ? `<div class="mb-5">${pFieldGrid(m.header_fields)}</div>` : '';
  return `<div class="panel p-5 md:p-6">
    ${head}
    <div class="shuttle-wrap">
      <div class="shuttle-col">
        <div class="shuttle-title">${fieldLabel(m.shuttle_left_title || '可选项')}</div>
        <div class="shuttle-body" id="shuttle-left">${shuttleList('l')}</div>
      </div>
      <div class="shuttle-arrows">
        <button class="shuttle-arrow" onclick="shuttleMove('r')" title="${t('common.add') || '添加'}"><i class="fas fa-angle-right"></i></button>
        <button class="shuttle-arrow" onclick="shuttleMove('l')" title="${t('common.remove') || '移除'}"><i class="fas fa-angle-left"></i></button>
      </div>
      <div class="shuttle-col">
        <div class="shuttle-title">${fieldLabel(m.shuttle_right_title || '已选项')}</div>
        <div class="shuttle-body" id="shuttle-right">${shuttleList('r')}</div>
      </div>
    </div>
    ${pFooter(t('common.save'), 'pfSaveShuttle(this)')}
  </div>`;
}
// p_shuttle 保存:把"已选"列表 + header 字段一起落库
function pfSaveShuttle(btn) {
  const form = {};
  collectHeaderInto(form);
  if (_shuttleState) { form._selected = _shuttleState.right.slice(); form._available = _shuttleState.left.slice(); }
  const mid = (S.curModule && S.curModule.id) || S.currentNav;
  pfSaveForm(btn, mid, form);
}
window.pfSaveShuttle = pfSaveShuttle;
function shuttleList(side) {
  const items = side === 'l' ? _shuttleState.left : _shuttleState.right;
  const sel = _shuttleState.sel[side];
  return items.map((it, i) =>
    `<div class="shuttle-item ${sel === i ? 'sel' : ''}" onclick="shuttleSel('${side}',${i})" ondblclick="shuttleMoveItem('${side}',${i})">
      <span class="pf-check ${side === 'r' ? 'on' : ''}"></span>${esc(it)}</div>`).join('')
    || `<div class="text-xs text-slate-300 p-3">${t('common.empty') || '(空)'}</div>`;
}
function shuttleSel(side, i) {
  _shuttleState.sel[side] = (_shuttleState.sel[side] === i ? null : i);
  document.querySelector('#shuttle-left').innerHTML = shuttleList('l');
  document.querySelector('#shuttle-right').innerHTML = shuttleList('r');
}
window.shuttleSel = shuttleSel;
// to='r' 把左选中移到右;to='l' 把右选中移到左
function shuttleMove(to) {
  const from = to === 'r' ? 'l' : 'r';
  const idx = _shuttleState.sel[from];
  if (idx == null) { toast(t('common.pick_first') || '请先选中一项'); return; }
  const srcArr = from === 'l' ? _shuttleState.left : _shuttleState.right;
  const dstArr = to === 'r' ? _shuttleState.right : _shuttleState.left;
  dstArr.push(srcArr.splice(idx, 1)[0]);
  _shuttleState.sel = { l: null, r: null };
  document.querySelector('#shuttle-left').innerHTML = shuttleList('l');
  document.querySelector('#shuttle-right').innerHTML = shuttleList('r');
}
window.shuttleMove = shuttleMove;
// 双击直接移动该项(无需预选)
function shuttleMoveItem(side, i) {
  _shuttleState.sel[side] = i;
  shuttleMove(side === 'l' ? 'r' : 'l');
}
window.shuttleMoveItem = shuttleMoveItem;

// ⑤ Formula 公式编辑器(可编辑 + 点变量插入 + 后端真实试算 + 真落库)
let _fxModule = null;
function pFormulaView(m) {
  _fxModule = m;
  const head = m.header_fields ? `<div class="mb-5">${pFieldGrid(m.header_fields)}</div>` : '';
  const defaultVars = ['HR.GENDER', 'HR.MARITAL', 'SERVICE.YEARS', 'ENTITLEMENT.DAYS', 'IF()', 'AND', 'OR'];
  const vars = (m.formula_vars && m.formula_vars.length ? m.formula_vars : defaultVars)
    .map(v => `<span class="fx-var" data-tok="${esc(v)}" onclick="fxInsertEl(this)">${esc(v)}</span>`).join('');
  const defaultFormula = "IF(HR.GENDER='M' AND HR.MARITAL='married',\n   ENTITLEMENT.DAYS + 3,\n   ENTITLEMENT.DAYS)";
  // 示例变量上下文(可编辑) —— 来自后端 sample_context 或模块自带
  const sample = m.formula_sample || { 'HR.GENDER': 'M', 'HR.MARITAL': 'married', 'SERVICE.YEARS': 6, 'ENTITLEMENT.DAYS': 14 };
  const varRows = Object.keys(sample).map(k =>
    `<div class="fx-var-row"><span class="fx-var-k">${esc(k)}</span>
      <input class="fx-var-v" data-vk="${esc(k)}" value="${esc(String(sample[k]))}"></div>`).join('');
  const flabel = S.lang === 'en' ? 'Eligibility Formula' : '资格公式';
  return `<div class="panel p-5 md:p-6">
    ${head}
    <div class="flex items-center justify-between mb-2">
      <label class="pf-label mb-0">${flabel} <span class="text-rose-500">*</span></label>
      <button class="btn btn-ai text-xs py-1" onclick="fxHelpOpen()"><i class="fas fa-wand-magic-sparkles"></i> ${S.lang === 'en' ? 'Formula Helper' : '公式查询助手'}</button>
    </div>
    <textarea class="fx-editor fx-editable" id="fx-area" spellcheck="false">${esc(m.formula || defaultFormula)}</textarea>
    <div class="fx-toolbar">${vars}</div>
    <div class="fx-testpanel">
      <div class="fx-test-head"><i class="fas fa-flask"></i> ${S.lang === 'en' ? 'Test Variables' : '试算变量'}</div>
      <div class="fx-var-grid">${varRows}</div>
      <div class="flex items-center gap-3 mt-3">
        <button class="btn btn-secondary text-sm" onclick="fxEval(this)"><i class="fas fa-play"></i> ${S.lang === 'en' ? 'Run Test' : '运行试算'}</button>
        <div id="fx-result" class="fx-result"></div>
      </div>
    </div>
    ${pFooter(t('common.save'), 'fxSave(this)')}
  </div>`;
}
function fxInsert(token) {
  const ta = document.getElementById('fx-area');
  if (!ta) return;
  const s = ta.selectionStart, e = ta.selectionEnd;
  ta.value = ta.value.slice(0, s) + token + ta.value.slice(e);
  ta.focus(); ta.selectionStart = ta.selectionEnd = s + token.length;
}
function fxInsertEl(el) { fxInsert(el.getAttribute('data-tok') || el.textContent || ''); }
window.fxInsert = fxInsert;
window.fxInsertEl = fxInsertEl;

// ── 公式查询助手 (Formula Helper) —— 真正的查询体系: 函数手册/变量字典/场景模板 ──
let _fxHelpCache = null;
const _isEn = () => S.lang === 'en';
async function fxHelpOpen() {
  if (document.getElementById('fxhelp-mask')) return;
  const T = _isEn();
  const html = `<div id="fxhelp-mask" class="fxhelp-mask" onclick="if(event.target===this)fxHelpClose()">
    <div class="fxhelp-panel" role="dialog">
      <div class="fxhelp-head">
        <div class="fxhelp-title"><i class="fas fa-wand-magic-sparkles"></i> ${T ? 'Formula Helper' : '公式查询助手'}</div>
        <button class="fxhelp-x" onclick="fxHelpClose()"><i class="fas fa-times"></i></button>
      </div>
      <div class="fxhelp-search">
        <i class="fas fa-search"></i>
        <input id="fxhelp-q" placeholder="${T ? 'Describe what you want, e.g. overtime, service tier...' : '描述你想算什么,如:加班、司龄阶梯、按比例折算…'}"
          oninput="fxHelpSearch(this.value)">
      </div>
      <div class="fxhelp-tabs">
        <span class="fxhelp-tab active" data-tab="tpl" onclick="fxHelpTab('tpl')">${T ? 'Templates' : '场景模板'}</span>
        <span class="fxhelp-tab" data-tab="fn" onclick="fxHelpTab('fn')">${T ? 'Functions' : '函数手册'}</span>
        <span class="fxhelp-tab" data-tab="var" onclick="fxHelpTab('var')">${T ? 'Variables' : '变量字典'}</span>
      </div>
      <div id="fxhelp-body" class="fxhelp-body"><div class="fxhelp-empty"><i class="fas fa-spinner fa-spin"></i></div></div>
    </div></div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  if (!_fxHelpCache) {
    try { _fxHelpCache = await api('/api/formula/help', null, 'GET'); }
    catch (e) { _fxHelpCache = { templates: [], functions: [], variables: [] }; }
  }
  _fxHelpTab = 'tpl';
  fxHelpRender(_fxHelpCache);
  setTimeout(() => { const i = document.getElementById('fxhelp-q'); if (i) i.focus(); }, 60);
}
function fxHelpClose() { const m = document.getElementById('fxhelp-mask'); if (m) m.remove(); }
let _fxHelpTab = 'tpl';
function fxHelpTab(tab) {
  _fxHelpTab = tab;
  document.querySelectorAll('.fxhelp-tab').forEach(el =>
    el.classList.toggle('active', el.getAttribute('data-tab') === tab));
  fxHelpRender(_fxHelpCache);
}
let _fxHelpTimer = null;
function fxHelpSearch(q) {
  clearTimeout(_fxHelpTimer);
  _fxHelpTimer = setTimeout(async () => {
    const query = (q || '').trim();
    if (!query) { _fxHelpTab = 'tpl'; fxHelpTab('tpl'); return; }
    let data;
    try { data = await api('/api/formula/help?q=' + encodeURIComponent(query), null, 'GET'); }
    catch (e) { return; }
    fxHelpRenderSearch(data);
  }, 220);
}
function _tplCard(tpl) {
  const T = _isEn();
  const title = esc(T && tpl.title_en ? tpl.title_en : tpl.title);
  const f = esc(tpl.formula);
  return `<div class="fxhelp-card">
    <div class="fxhelp-card-h"><span class="fxhelp-badge">${esc(tpl.domain)}</span><b>${title}</b></div>
    <pre class="fxhelp-code">${f}</pre>
    <div class="fxhelp-card-act">
      <button class="btn btn-secondary text-xs py-1" onclick='fxHelpUse(${JSON.stringify(tpl.formula)})'><i class="fas fa-arrow-down"></i> ${T ? 'Insert' : '插入编辑器'}</button>
    </div></div>`;
}
function _fnRow(f) {
  const T = _isEn();
  return `<div class="fxhelp-fn">
    <div class="fxhelp-fn-h"><code>${esc(T && f.sig_en ? f.sig_en : f.sig)}</code><span class="fxhelp-cat">${esc(f.cat)}</span></div>
    <div class="fxhelp-fn-d">${esc(T && f.desc_en ? f.desc_en : f.desc)}</div>
    <div class="fxhelp-fn-ex" onclick='fxHelpUse(${JSON.stringify(f.example)})' title="${T ? 'Click to insert' : '点击插入'}"><i class="fas fa-code"></i> ${esc(f.example)}</div>
  </div>`;
}
function _varRow(v) {
  const T = _isEn();
  return `<div class="fxhelp-var" onclick='fxHelpUse(${JSON.stringify(v.name)})' title="${T ? 'Click to insert' : '点击插入'}">
    <code>${esc(v.name)}</code><span>${esc(T && v.desc_en ? v.desc_en : v.desc)}</span><em>${esc(v.domain)}</em></div>`;
}
function fxHelpRender(data) {
  const body = document.getElementById('fxhelp-body'); if (!body || !data) return;
  const T = _isEn();
  if (_fxHelpTab === 'tpl') {
    body.innerHTML = (data.templates || []).map(_tplCard).join('') ||
      `<div class="fxhelp-empty">${T ? 'No templates' : '暂无模板'}</div>`;
  } else if (_fxHelpTab === 'fn') {
    body.innerHTML = (data.functions || []).map(_fnRow).join('');
  } else {
    body.innerHTML = (data.variables || []).map(_varRow).join('');
  }
}
function fxHelpRenderSearch(data) {
  const body = document.getElementById('fxhelp-body'); if (!body) return;
  const T = _isEn();
  let html = '';
  if (data.templates && data.templates.length)
    html += `<div class="fxhelp-sec">${T ? 'Matched Templates' : '匹配模板'}</div>` + data.templates.map(_tplCard).join('');
  if (data.functions && data.functions.length)
    html += `<div class="fxhelp-sec">${T ? 'Matched Functions' : '匹配函数'}</div>` + data.functions.map(_fnRow).join('');
  body.innerHTML = html || `<div class="fxhelp-empty"><i class="fas fa-circle-info"></i> ${T ? 'No match. Try keywords like overtime / service / pro-rata.' : '没有匹配。试试关键词:加班 / 司龄 / 折算 / 结转。'}</div>`;
}
function fxHelpUse(formula) {
  const ta = document.getElementById('fx-area');
  if (ta) { ta.value = formula; ta.focus(); }
  fxHelpClose();
  toast(_isEn() ? 'Formula inserted — adjust variables then Run Test' : '已插入公式 — 可改试算变量后点「运行试算」');
}
window.fxHelpOpen = fxHelpOpen; window.fxHelpClose = fxHelpClose;
window.fxHelpTab = fxHelpTab; window.fxHelpSearch = fxHelpSearch; window.fxHelpUse = fxHelpUse;
// 收集试算变量(自动把数字字符串转 number,true/false 转布尔)
function fxCollectVars() {
  const vars = {};
  document.querySelectorAll('.fx-var-v').forEach(inp => {
    const k = inp.getAttribute('data-vk'); let v = inp.value.trim();
    if (/^-?\d+(\.\d+)?$/.test(v)) v = parseFloat(v);
    else if (v.toLowerCase() === 'true') v = true;
    else if (v.toLowerCase() === 'false') v = false;
    vars[k] = v;
  });
  return vars;
}
// 真实后端试算
async function fxEval(btn) {
  const ta = document.getElementById('fx-area');
  const box = document.getElementById('fx-result');
  if (!ta || !box) return;
  const old = btn.innerHTML;
  btn.disabled = true; btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i>`;
  try {
    const r = await api('/api/formula/eval', { formula: ta.value, variables: fxCollectVars() });
    if (r.ok) {
      box.className = 'fx-result fx-ok';
      box.innerHTML = `<i class="fas fa-check-circle"></i> ${S.lang === 'en' ? 'Result' : '结果'}: <b>${esc(String(r.result))}</b> <span class="fx-type">(${r.type})</span>`;
    } else {
      box.className = 'fx-result fx-err';
      box.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${esc(r.error || (S.lang === 'en' ? 'Error' : '错误'))}`;
    }
  } catch (e) {
    box.className = 'fx-result fx-err';
    box.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${S.lang === 'en' ? 'Request failed' : '请求失败'}`;
  }
  btn.disabled = false; btn.innerHTML = old;
}
window.fxEval = fxEval;
// 保存公式(先后端校验语法,通过才真落库)
async function fxSave(btn) {
  const ta = document.getElementById('fx-area');
  if (!ta) return;
  // 先用一次 eval 验证语法(变量缺失不算致命,只拦语法/括号错误)
  const chk = await api('/api/formula/eval', { formula: ta.value, variables: fxCollectVars() });
  if (!chk.ok && /括号|语法|bracket|syntax/i.test(chk.error || '')) {
    toast(chk.error, true); return;
  }
  const form = {};
  document.querySelectorAll('[data-pf]').forEach(el => { /* header 字段 */ });
  form._formula = ta.value;
  if (_fxModule) collectHeaderInto(form);
  pfSaveForm(btn, (_fxModule && _fxModule.id) || S.currentNav, form);
}
window.fxSave = fxSave;

// ⑥ 地图定位框 —— 真实地图(Leaflet + OpenStreetMap, 图钉可拖 + 半径圆 + 地址搜索)
let _leafMap = null;     // Leaflet 地图实例(单例,切模块时销毁重建)
function pMapView(m) {
  const radius = m.radius || '500';
  const geo = m.geo || { lat: 3.157640, lng: 101.711950, zoom: 14 };
  const coord = m.coord || `${geo.lat}, ${geo.lng}`;
  // 把初始化参数挂到 window,供 initRealMap 读取(避免闭包/混淆问题)
  window._mapInit = { lat: geo.lat, lng: geo.lng, zoom: geo.zoom || 14,
                      radius: Number(radius) || 500, country: m.country_code || '' };
  setTimeout(() => initRealMap(), 60);   // 等容器进 DOM 再初始化地图
  return `<div class="panel p-5 md:p-6">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div>${pFieldGrid(m.fields || [])}
        <div class="pf-cell mt-1"><label class="pf-label">${t('map.coord') || '坐标 (拖图钉自动更新)'}</label>
          <input class="pf-input pf-ro" id="map-coord" data-label="GPS Coordinate" value="${esc(coord)}" readonly></div>
      </div>
      <div>
        <label class="pf-label">Map <span class="text-rose-500">*</span></label>
        <div class="map-search-bar">
          <i class="fas fa-magnifying-glass map-search-ico"></i>
          <input id="map-search" class="map-search-input" placeholder="${t('map.search') || '搜索地址/地点定位…'}"
                 onkeydown="if(event.key==='Enter'){event.preventDefault();mapSearch();}">
          <button type="button" class="map-search-btn" onclick="mapSearch()">${t('map.go') || '定位'}</button>
        </div>
        <div class="map-box" id="map-box"></div>
        <div class="map-foot"><i class="fas fa-circle-info"></i>
          ${t('map.hint') || '拖动图钉或点击地图定位'} ·
          ${t('map.radius') || '半径'} <b id="map-radius-txt">${radius}</b> ${t('map.meter') || '米打卡有效'}</div>
      </div>
    </div>
    ${pFooter(t('common.save'), 'pfSaveCollect(this)')}
  </div>`;
}

// 初始化真实 Leaflet 地图:可拖动 marker + 打卡半径圆 + 实时回填坐标
function initRealMap() {
  const box = document.getElementById('map-box');
  if (!box || typeof L === 'undefined') return;   // Leaflet 未就绪则跳过
  const cfg = window._mapInit || { lat: 3.157640, lng: 101.711950, zoom: 14, radius: 500 };
  // 销毁旧实例(切换公司/模块复用同一容器)
  if (_leafMap) { try { _leafMap.remove(); } catch (e) {} _leafMap = null; }
  box.innerHTML = '';

  const map = L.map(box, { zoomControl: true, attributionControl: true })
               .setView([cfg.lat, cfg.lng], cfg.zoom || 14);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '© OpenStreetMap'
  }).addTo(map);

  // 打卡有效半径圆(单位:米)
  const circle = L.circle([cfg.lat, cfg.lng], {
    radius: cfg.radius || 500, color: '#0f766e', weight: 1.5,
    fillColor: '#14b8a6', fillOpacity: 0.15
  }).addTo(map);

  // 可拖动图钉
  const marker = L.marker([cfg.lat, cfg.lng], { draggable: true }).addTo(map);

  const sync = (latlng) => {
    circle.setLatLng(latlng);
    const c = document.getElementById('map-coord');
    if (c) c.value = `${latlng.lat.toFixed(6)}, ${latlng.lng.toFixed(6)}`;
  };
  marker.on('drag', e => sync(e.target.getLatLng()));
  marker.on('dragend', e => { sync(e.target.getLatLng()); });
  // 点击地图 → 图钉跳过去
  map.on('click', e => { marker.setLatLng(e.latlng); sync(e.latlng); });
  // 半径输入框联动圆大小
  const radInput = document.querySelector('[data-label="Maximum Radius"]');
  if (radInput) radInput.addEventListener('input', () => {
    const r = Number(radInput.value) || 0;
    circle.setRadius(r);
    const txt = document.getElementById('map-radius-txt'); if (txt) txt.textContent = r;
  });

  _leafMap = map; _leafMapMarker = marker; _leafMapCircle = circle;
  // 容器可能在隐藏/动画后才定尺寸,强制重算一次
  setTimeout(() => { try { map.invalidateSize(); } catch (e) {} }, 200);
}
let _leafMapMarker = null, _leafMapCircle = null;

// 地址搜索(OSM Nominatim 免费地理编码,无需 Key)
async function mapSearch() {
  const inp = document.getElementById('map-search');
  if (!inp || !inp.value.trim() || !_leafMap) return;
  const q = inp.value.trim();
  const btn = document.querySelector('.map-search-btn');
  const old = btn ? btn.textContent : '';
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  try {
    const country = (window._mapInit && window._mapInit.country) || '';
    let url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(q)}`;
    if (country) url += `&countrycodes=${country.toLowerCase()}`;
    const res = await fetch(url, { headers: { 'Accept-Language': S.lang === 'en' ? 'en' : 'zh' } });
    const arr = await res.json();
    if (arr && arr.length) {
      const lat = parseFloat(arr[0].lat), lng = parseFloat(arr[0].lon);
      const ll = L.latLng(lat, lng);
      _leafMap.setView(ll, 16);
      if (_leafMapMarker) _leafMapMarker.setLatLng(ll);
      if (_leafMapCircle) _leafMapCircle.setLatLng(ll);
      const c = document.getElementById('map-coord');
      if (c) c.value = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
    } else {
      acFlash && acFlash(document.querySelector('.map-foot'), t('map.notfound') || '未找到该地址', true);
    }
  } catch (e) {
    console.warn('map search failed', e);
  } finally { if (btn) { btn.disabled = false; btn.textContent = old; } }
}
window.mapSearch = mapSearch;
window.initRealMap = initRealMap;

// ⑦ Tabset 详情页(内部横向子 Tab 可点切换 + 字段分段)
let _tabsetState = null;
function pTabsetView(m) {
  const subs = m.sub_tabs || ['General'];
  const fields = m.fields || [];
  // 字段按 tab 数量均分到各子 Tab
  const per = Math.ceil(fields.length / subs.length) || 1;
  _tabsetState = { subs, groups: subs.map((s, i) => fields.slice(i * per, (i + 1) * per)), active: 0, form: {} };
  const tabs = subs.map((tb, i) => `<div class="ptab2 ${i === 0 ? 'active' : ''}" onclick="tabsetSwitch(${i})">${fieldLabel(tb)}</div>`).join('');
  return `<div class="panel p-5 md:p-6">
    <div class="ptab2-bar">${tabs}</div>
    <div id="tabset-body">${pFieldGrid(_tabsetState.groups[0])}</div>
    ${pFooter(t('common.save'), 'pfSaveTabset(this)')}
  </div>`;
}
function tabsetSwitch(i) {
  if (!_tabsetState) return;
  // 切走前先把当前 tab 的输入累积到内存 form,避免切 tab 丢数据
  const body0 = document.getElementById('tabset-body');
  if (body0) collectHeaderInto(_tabsetState.form, body0);
  _tabsetState.active = i;
  document.querySelectorAll('.ptab2-bar .ptab2').forEach((e, k) => e.classList.toggle('active', k === i));
  const body = document.getElementById('tabset-body');
  const g = _tabsetState.groups[i];
  if (body) body.innerHTML = g && g.length ? pFieldGrid(g) : `<div class="text-sm text-slate-400 py-6 text-center"><i class="fas fa-sliders"></i> ${t('common.tab_empty') || '该分组暂无更多配置项'}</div>`;
}
window.tabsetSwitch = tabsetSwitch;
// p_tabset 保存:合并内存 form + 当前可见 tab
function pfSaveTabset(btn) {
  if (!_tabsetState) { pfSaveCollect(btn); return; }
  const body = document.getElementById('tabset-body');
  if (body) collectHeaderInto(_tabsetState.form, body);
  const mid = (S.curModule && S.curModule.id) || S.currentNav;
  pfSaveForm(btn, mid, Object.assign({}, _tabsetState.form));
}
window.pfSaveTabset = pfSaveTabset;

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

// ════════════════════════════════════════════════════════════
//  系统架构图谱 + 完整说明书(点击左上角集团 Logo 进入)
//  —— 中英双语并排 · 功能精确详解 ——
// ════════════════════════════════════════════════════════════

// 双语并排行:中文在上、英文在下(始终同屏对照)
function biRow(zh, en) {
  return `<div class="bi-row"><div class="bi-zh">${zh}</div><div class="bi-en">${en}</div></div>`;
}
// 双语标题(用于区块 h2)
function biH2(icon, zh, en) {
  return `<h2 class="arch-h2"><i class="fas ${icon}"></i><span class="bi-h2-zh">${zh}</span><span class="bi-h2-en">${en}</span></h2>`;
}
// 双语小标签(中 / English 同行)
function biH2cap(zh, en) {
  return `<span class="bi-cap"><i class="fas fa-bolt"></i> ${zh} <em>/ ${en}</em></span>`;
}

function renderArchitecture() {
  const G = S.group ? S.group : { logo: 'P', color: '#20c997' };

  // ════ 1. 五层架构(双语并排) ════
  const layers = [
    { icon: 'fa-display', color: '#0ea5e9',
      zh: '① 体验层', en: 'Experience Layer',
      subzh: '多端自适应 · 角色化界面 · 对话式交互', suben: 'Adaptive multi-device · Role-based UI · Conversational UX',
      items: [
        ['管理者桌面驾驶舱:KPI 大屏、趋势图表、待办派发,一屏掌握经营全局', 'Manager desktop cockpit: KPI wall, trend charts, todo dispatch — run the whole business at a glance'],
        ['员工手机端自助门户:本月薪资、年度报销额度、报销进度、个人中心', 'Employee mobile self-portal: monthly payslip, annual claim quota, claim status, profile center'],
        ['AI 助手抽屉:自然语言对话 + 拍照识别 + 结构化结果卡片', 'AI assistant drawer: natural-language chat + photo OCR + structured result cards'],
        ['全站中英双语 i18n,手机/平板/桌面三视口零溢出自适应', 'Full bilingual i18n (zh/en), zero-overflow across mobile / tablet / desktop'],
      ] },
    { icon: 'fa-diagram-project', color: '#14b8a6',
      zh: '② 编排层', en: 'Orchestration Layer',
      subzh: 'LangGraph 状态机 · 意图路由 · 人机协同 (HITL)', suben: 'LangGraph state machine · Intent routing · Human-in-the-loop',
      items: [
        ['LangGraph 状态图 build_graph():感知 → 规划 → 调工具 → 执行,可追溯每一步', 'LangGraph state graph build_graph(): perceive → plan → call-tool → act, every step traceable'],
        ['统一入口 run_turn(输入, 会话, 公司, 角色),按身份决定数据与权限边界', 'Single entry run_turn(input, thread, company, role) — identity decides data & permission scope'],
        ['意图检测主动递工具:用户问「怎么报销」即推送拍照识别卡片', 'Intent detection proactively offers tools: asking "how to claim" pushes a photo-OCR card'],
        ['风险分级触发 needs_human / hil_level,高风险自动转人工兜底', 'Risk grading triggers needs_human / hil_level — high risk auto-escalates to a human'],
      ] },
    { icon: 'fa-robot', color: '#8b5cf6',
      zh: '③ 智能体层 (5 主 + 8 子 = 13)', en: 'Agent Layer (5 main + 8 sub = 13)',
      subzh: '专家分工 · 多体协作 · 工具调用', suben: 'Expert division · Multi-agent collaboration · Tool use',
      items: [
        ['5 个面向用户的主智能体,各管一条业务线(报销/审批/HR/薪资/分析)', '5 user-facing main agents, each owning a business line (claim / approval / HR / payroll / analytics)'],
        ['8 个后台子智能体协同:意图、政策、风险、抽取、流程、权益、对话、稽查', '8 backstage sub-agents collaborate: intent, policy, risk, extraction, workflow, entitlement, conversation, audit'],
      ] },
    { icon: 'fa-microchip', color: '#f59e0b',
      zh: '④ 引擎层', en: 'Engine Layer',
      subzh: '合规精度内核 · 可插拔大模型网关', suben: 'Statutory precision core · Pluggable LLM gateway',
      items: [
        ['薪资精度引擎:加班分级、按比例计薪、HRDF 征费、企业总成本核算', 'Payroll precision engine: OT tiers, pro-rata pay, HRDF levy, employer total-cost'],
        ['法定文件引擎:CP39、SOCSO 8A、银行 IBG、LHDN 审计追踪、EA 表', 'Statutory docs engine: CP39, SOCSO 8A, bank IBG, LHDN audit trail, EA form'],
        ['PCB 税务引擎 + 视觉 OCR 抽取 + 共享分析稽查引擎', 'PCB tax engine + Vision OCR extraction + shared analytics & audit engine'],
        ['LLM 网关:多供应商接入、模型按 Agent 绑定、失败降级兜底', 'LLM gateway: multi-provider, per-agent model binding, graceful fallback'],
      ] },
    { icon: 'fa-database', color: '#64748b',
      zh: '⑤ 数据层', en: 'Data Layer',
      subzh: '集团多公司隔离 · 角色级权限 · 全链路一致', suben: 'Group multi-company isolation · RBAC · end-to-end consistency',
      items: [
        ['集团 / 公司 / 部门 / 员工四级主数据,多公司物理隔离', 'Four-tier master data (group / company / dept / employee), multi-company isolation'],
        ['报销单、差旅、薪资批次、权益额度等业务数据按公司归集', 'Business data (claims, travel, payroll batches, entitlements) scoped per company'],
        ['6 角色权限矩阵 + effCompany() 统一所有数据源的公司口径', '6-role RBAC matrix + effCompany() unifies company scope across all data sources'],
      ] },
  ];
  const layerCards = layers.map((l, i) => `
    <div class="arch-layer" style="--lc:${l.color}">
      <div class="arch-layer-head">
        <span class="arch-layer-ic"><i class="fas ${l.icon}"></i></span>
        <div>
          <div class="arch-layer-title">${l.zh} <span class="arch-layer-en">${l.en}</span></div>
          <div class="arch-layer-sub">${l.subzh}<br><i>${l.suben}</i></div>
        </div>
      </div>
      <ul class="arch-layer-list">${l.items.map(x => `<li><i class="fas fa-angle-right"></i>${biRow(x[0], x[1])}</li>`).join('')}</ul>
    </div>
    ${i < layers.length - 1 ? '<div class="arch-flow"><i class="fas fa-arrow-down-long"></i></div>' : ''}
  `).join('');

  // ════ 2. 一次请求的旅程(双语泳道) ════
  const flow = [
    ['fa-comment-dots', '用户提问/拍照', 'User asks / snaps'],
    ['fa-route', '意图路由', 'Intent routing'],
    ['fa-robot', 'Agent 协作', 'Agent collaboration'],
    ['fa-microchip', '引擎计算', 'Engine compute'],
    ['fa-shield-halved', '合规校验', 'Compliance check'],
    ['fa-square-poll-vertical', '卡片/报表返回', 'Cards / report back'],
  ];
  const flowHtml = flow.map((f, i) => `
    <div class="arch-fl"><span class="arch-fl-ic"><i class="fas ${f[0]}"></i></span>
      <span class="arch-fl-tx"><b>${f[1]}</b><i>${f[2]}</i></span></div>
    ${i < flow.length - 1 ? '<i class="fas fa-chevron-right arch-fl-arrow"></i>' : ''}`).join('');

  // ════ 3. 5 主智能体 · 功能手册(精确详解) ════
  // 字段:emoji 名称 / 一句话定位 / 使用者 / 能做什么(精确清单)/ 典型对话 / 产出
  const agentManual = [
    { emoji: '🙋', color: '#10b981',
      zh: '报销伙伴', en: 'ClaimMate',
      rolezh: '面向全体员工的报销助手', roleen: 'Claim assistant for every employee',
      userzh: '普通员工', useren: 'Employee',
      can: [
        ['拍照/对话提交报销:上传票据自动识别商户、金额、类别、日期并填单', 'Submit by photo/chat: OCR auto-extracts merchant, amount, category, date and fills the form'],
        ['实时查询可报余额与年度额度,告知还能报多少、哪类已超限', 'Check claimable balance & annual quota — how much is left, which category is over limit'],
        ['商务差旅预审批申请 + 行后差旅报销提交', 'Business-travel pre-approval requests + post-trip travel claims'],
        ['登记/维护家属信息(用于家庭相关权益)', 'Register / maintain family info (for family-related entitlements)'],
      ],
      sayzh: '「我打车花了 88 块要报销」「我还能报多少钱」', sayen: '"I spent RM88 on a taxi to claim" · "How much can I still claim"',
      outzh: '已入库报销单 + 余额卡 + 拍照识别结果卡', outen: 'Posted claim + balance card + OCR result card' },
    { emoji: '✅', color: '#3b82f6',
      zh: '审批副驾', en: 'ApprovalCopilot',
      rolezh: '面向审批人的智能审批助手', roleen: 'Smart approval copilot for approvers',
      userzh: '审批人 / 部门主管', useren: 'Approver / Line manager',
      can: [
        ['自动风险分级:对待审单据标注高/中/低风险并给出理由', 'Auto risk grading: tags pending items as high/mid/low with reasons'],
        ['一键批量通过低风险报销,聚焦人工处理高风险', 'One-click batch-approve low-risk claims, focus humans on high-risk'],
        ['异常检测:重复票据、超额、过期发票、节假日疑点', 'Anomaly detection: duplicate receipts, over-limit, expired invoices, holiday flags'],
        ['人机协同:高风险自动转人工确认 (HITL)', 'Human-in-the-loop: high risk auto-routes to human confirmation'],
      ],
      sayzh: '「帮我审批待审单据」「批量通过低风险报销」', sayen: '"Approve my pending claims" · "Batch-approve low-risk claims"',
      outzh: '风险分级清单 + 批量审批结果 + 异常告警', outen: 'Risk-graded list + batch result + anomaly alerts' },
    { emoji: '🧠', color: '#8b5cf6',
      zh: 'HR 战略顾问', en: 'HR Strategist',
      rolezh: '面向 HR 的对话式政策配置专家', roleen: 'Conversational policy-config expert for HR',
      userzh: 'HR 管理员', useren: 'HR Admin',
      can: [
        ['对话式配置报销类型、报销组、报销权益规则', 'Chat-config claim types, claim groups, entitlement rules'],
        ['权益预算优化建议与年度权益批量生成', 'Entitlement budget optimization + bulk annual entitlement generation'],
        ['政策推理:依据规则解释「为什么这笔不能报」', 'Policy reasoning: explains "why this claim is not allowed" by rules'],
        ['余额调整(带审批留痕)', 'Balance adjustment (with audit trail)'],
      ],
      sayzh: '「帮我配置报销类型」「推荐权益预算方案」', sayen: '"Help me configure claim types" · "Recommend an entitlement budget"',
      outzh: '配置变更单 + 权益方案 + 政策解释', outen: 'Config change + entitlement plan + policy explanation' },
    { emoji: '⚙️', color: '#f59e0b',
      zh: '薪资领航员', en: 'Payroll Navigator',
      rolezh: '面向薪资专员的跑批与对账引擎', roleen: 'Batch & reconciliation engine for payroll officers',
      userzh: '薪资专员', useren: 'Payroll Officer',
      can: [
        ['自主薪资跑批,自动核算 EPF/SOCSO/EIS/PCB 法定扣缴', 'Autonomous payroll run, auto-computes EPF/SOCSO/EIS/PCB statutory deductions'],
        ['接口数据审核:报销→薪资接口流程校验与异常预警', 'Interface data review: claim→payroll flow validation & anomaly alerts'],
        ['多币种汇率查询与折算', 'Multi-currency FX lookup & conversion'],
        ['对账:发薪明细与银行 IBG 文件一致性核对', 'Reconciliation: payslip vs bank IBG file consistency'],
      ],
      sayzh: '「执行薪资跑批」「查一下美元汇率」', sayen: '"Run payroll batch" · "Check the USD exchange rate"',
      outzh: '薪资批次结果 + 异常预警 + 汇率折算', outen: 'Payroll batch result + anomaly alerts + FX conversion' },
    { emoji: '📊', color: '#ec4899',
      zh: '洞察先知', en: 'Insight Oracle',
      rolezh: '面向财务/管理层的分析与报表大师', roleen: 'Analytics & reporting master for finance/management',
      userzh: '财务 / 审计 / 管理者', useren: 'Finance / Audit / Manager',
      can: [
        ['自然语言转 SQL (NL2SQL),用大白话查任意经营数据', 'Natural-language-to-SQL: query any business data in plain words'],
        ['预测分析:费用趋势、超支预警、预算缺口预测', 'Forecasting: spend trends, over-budget warnings, gap prediction'],
        ['自动生成福利使用、差旅、报销三大报表', 'Auto-generates benefit-usage, travel, and claim reports'],
        ['一键生成月度总结 PPT', 'One-click monthly summary PPT'],
      ],
      sayzh: '「看一下福利使用报表」「生成报销月度总结 PPT」', sayen: '"Show the benefits report" · "Generate a monthly expense PPT"',
      outzh: '可视化报表 + 预测图 + PPT 文件', outen: 'Visual reports + forecast charts + PPT file' },
  ];
  const agentManualHtml = agentManual.map(a => `
    <div class="arch-amx" style="--ac:${a.color}">
      <div class="arch-amx-head">
        <span class="arch-amx-emoji">${a.emoji}</span>
        <div class="arch-amx-title">
          <div class="arch-amx-name">${a.zh} <span>${a.en}</span></div>
          <div class="arch-amx-role">${a.rolezh}<br><i>${a.roleen}</i></div>
        </div>
        <span class="arch-amx-user"><i class="fas fa-user-tag"></i> ${a.userzh} / ${a.useren}</span>
      </div>
      <div class="arch-amx-cando">${biH2cap('能做什么', 'What it can do')}</div>
      <ul class="arch-amx-list">${a.can.map(c => `<li><i class="fas fa-check"></i>${biRow(c[0], c[1])}</li>`).join('')}</ul>
      <div class="arch-amx-foot">
        <div><span class="arch-amx-lbl"><i class="fas fa-quote-left"></i> 典型对话 / Typical</span>${biRow(a.sayzh, a.sayen)}</div>
        <div><span class="arch-amx-lbl"><i class="fas fa-box-open"></i> 产出 / Output</span>${biRow(a.outzh, a.outen)}</div>
      </div>
    </div>`).join('');

  // 8 子智能体(双语 chip)
  const subAgents = [
    ['意图', 'Intent', '识别用户想干什么', 'Detect user intent'],
    ['政策', 'Policy', '匹配报销/薪资规则', 'Match claim/payroll rules'],
    ['风险', 'Risk', '评估单据风险等级', 'Grade item risk level'],
    ['抽取', 'Extraction', '票据 OCR 字段抽取', 'OCR field extraction'],
    ['流程', 'Workflow', '驱动审批工作流', 'Drive approval workflow'],
    ['权益', 'Entitlement', '核算额度与权益', 'Compute quota & benefits'],
    ['对话', 'Conversation', '维护多轮上下文', 'Keep multi-turn context'],
    ['稽查', 'Audit', '异常与合规稽查', 'Anomaly & compliance audit'],
  ];
  const subChips = subAgents.map(s => `
    <div class="arch-subcard">
      <div class="arch-subcard-t">${s[0]} <span>${s[1]}</span></div>
      ${biRow(s[2], s[3])}
    </div>`).join('');

  // ════ 4. 18 业务模块 · 功能手册(逐条精确说明) ════
  // 分组 → [中文名, 英文名, 精确功能说明(中), 精确功能说明(英)]
  const moduleManual = [
    { gzh: '报销与权益', gen: 'Claim & Entitlement', icon: 'fa-hand-holding-dollar', color: '#10b981', items: [
      ['报销类型', 'Claim Types', '定义可报销的费用类目(餐饮/交通/住宿…)及每类的单据要求与限额', 'Define claimable expense categories (meals/transport/lodging…) with receipt rules & limits'],
      ['报销组', 'Claim Groups', '把报销类型打包成组,按职级/部门批量套用权益规则', 'Bundle claim types into groups, apply entitlements by grade/dept in bulk'],
      ['报销权益', 'Entitlements', '设定每人/每组的年度额度、周期与可报范围', 'Set annual quota, cycle and scope per person/group'],
      ['余额调整', 'Balance Adjust', '对个人额度做增减调整,全程留审批痕迹', 'Increase/decrease individual quota with full audit trail'],
      ['生成权益流程', 'Entitlement Gen', '按规则一键批量生成全员年度权益额度', 'One-click bulk-generate annual entitlements by rule'],
    ] },
    { gzh: '申请与审批', gen: 'Apply & Approve', icon: 'fa-file-circle-check', color: '#3b82f6', items: [
      ['报销申请-自助', 'Self Claim', '员工本人提交报销:拍照识别、填单、查额度、看进度', 'Employee self-submit: OCR, fill form, check quota, track status'],
      ['报销申请-管理', 'Manage Claim', '审批人处理报销:风险分级、批量审批、退回补充', 'Approver handling: risk grading, batch approve, return for revision'],
      ['差旅申请-管理', 'Manage Travel Req', '审批商务差旅预申请,控制行前预算', 'Approve business-travel pre-requests, control pre-trip budget'],
      ['差旅报销-管理', 'Manage Travel Claim', '审批行后差旅实报,核对预算与实际差异', 'Approve post-trip travel claims, reconcile budget vs actual'],
      ['商务差旅申请-自助', 'Self Travel Req', '员工提交差旅预审批(目的地/预算/事由)', 'Employee submits travel pre-approval (destination/budget/reason)'],
      ['商务差旅报销-自助', 'Self Travel Claim', '员工提交行后差旅费用报销与票据', 'Employee submits post-trip travel expenses & receipts'],
    ] },
    { gzh: '薪资与接口', gen: 'Payroll & Interface', icon: 'fa-money-check-dollar', color: '#f59e0b', items: [
      ['汇率', 'FX Rate', '维护多币种汇率,供报销/薪资折算', 'Maintain multi-currency FX rates for claim/payroll conversion'],
      ['报销接口流程', 'Interface Flow', '把已批报销推送到薪资/会计接口的流程编排', 'Orchestrate pushing approved claims to payroll/accounting interface'],
      ['审核接口数据', 'Review Interface', '推送前校验接口数据,拦截异常与跳变', 'Validate interface data pre-push, block anomalies & spikes'],
    ] },
    { gzh: '报表与数据', gen: 'Reports & Data', icon: 'fa-chart-pie', color: '#ec4899', items: [
      ['福利使用报表', 'Benefit Report', '统计各类权益的使用率、剩余与超支分布', 'Stats on entitlement usage rate, remaining & over-spend distribution'],
      ['差旅申请报表', 'Travel Report', '差旅申请/报销的频次、金额、目的地分析', 'Travel request/claim frequency, amount, destination analytics'],
      ['报销申请报表', 'Claim Report', '报销总量、类别占比、月度趋势与导出', 'Total claims, category mix, monthly trend & export'],
      ['家庭信息', 'Family Info', '维护员工家属信息,支撑家庭相关权益核算', 'Maintain employee family info for family-related entitlements'],
    ] },
  ];
  const moduleManualHtml = moduleManual.map(g => `
    <div class="arch-mmx-group">
      <div class="arch-mmx-gt" style="--mc:${g.color}">
        <span class="arch-mmx-gic"><i class="fas ${g.icon}"></i></span>
        <span>${g.gzh} <em>${g.gen}</em></span>
        <span class="arch-mmx-cnt">${g.items.length}</span>
      </div>
      <div class="arch-mmx-items">
        ${g.items.map(m => `
          <div class="arch-mmx-item">
            <div class="arch-mmx-name">${m[0]} <span>${m[1]}</span></div>
            ${biRow(m[2], m[3])}
          </div>`).join('')}
      </div>
    </div>`).join('');

  // ════ 5. 6 角色权限(精确权责描述) ════
  const roleManual = {
    employee:  ['提交报销/差旅、查额度、看本人薪资单、维护家属', 'Submit claims/travel, check quota, view own payslip, manage family'],
    approver:  ['审批本部门报销/差旅,风险分级与批量处理', 'Approve dept claims/travel, risk grading & batch handling'],
    hr_admin:  ['配置报销类型/组/权益、生成权益、AI 配置后台', 'Configure types/groups/entitlements, generate entitlements, AI config'],
    payroll:   ['薪资跑批、接口审核、汇率维护、对账', 'Payroll run, interface review, FX maintenance, reconciliation'],
    finance:   ['费用报表、审计稽查、合规核查、数据导出', 'Expense reports, audit, compliance check, data export'],
    sys_admin: ['全局管理、跨公司切换、系统配置、全权限', 'Global admin, cross-company switch, system config, full access'],
  };
  const roleCards = (S.roles || []).map(r => {
    const m = roleManual[r.id] || ['', ''];
    return `
    <div class="arch-rolex" style="--rc:${r.color}">
      <div class="arch-rolex-head">
        <span class="arch-rolex-ic"><i class="fas ${r.icon}"></i></span>
        <span class="arch-rolex-name">${r.name || ''}<em>${r.name_en || ''}</em></span>
      </div>
      ${biRow(m[0], m[1])}
    </div>`;
  }).join('');

  // ════ 6. 技术栈 ════
  const stack = [
    ['fa-server', '#0d9488', '后端', 'Backend', 'FastAPI · Pydantic · Python'],
    ['fa-diagram-project', '#8b5cf6', '编排', 'Orchestration', 'LangGraph 状态图 / state graph'],
    ['fa-brain', '#ec4899', '大模型', 'LLM', '多供应商网关 · 视觉 OCR / Multi-provider · Vision OCR'],
    ['fa-code', '#0ea5e9', '前端', 'Frontend', 'Vanilla JS · Tailwind · Chart.js'],
  ];
  const stackHtml = stack.map(s => `
    <div class="arch-stack" style="--sc:${s[1]}">
      <span class="arch-stack-ic"><i class="fas ${s[0]}"></i></span>
      <div><div class="arch-stack-t">${s[2]} <em>${s[3]}</em></div><div class="arch-stack-v">${s[4]}</div></div>
    </div>`).join('');

  // ════ 7. 合规精度内核 ════
  const comp = [
    ['fa-file-invoice-dollar', 'EPF / SOCSO / EIS / PCB', '马来西亚法定扣缴精算', 'MY statutory deductions'],
    ['fa-file-contract', 'CP39 / SOCSO 8A / IBG', '政府申报与银行文件', 'Gov filing & bank files'],
    ['fa-magnifying-glass-chart', 'LHDN 审计追踪', '凭证分类账 · 异常稽查', 'Ledger · anomaly audit'],
    ['fa-clock', '加班分级 / 按比例', 'HRDF · 企业总成本', 'HRDF · employer total cost'],
  ];
  const compHtml = comp.map(c => `
    <div class="arch-comp-card"><i class="fas ${c[0]}"></i><b>${c[1]}</b>${biRow(c[2], c[3])}</div>`).join('');

  // ════ 8. 迭代历程(双语) ════
  const waves = [
    ['Wave1', '业务流程引擎', 'Workflow engine'],
    ['Wave2', '薪资精度引擎', 'Payroll precision engine'],
    ['Wave3', '政府法定文件', 'Statutory documents'],
    ['Wave4', 'AI 老板驾驶舱 + 异常稽查', 'AI cockpit + anomaly audit'],
    ['Wave5', '员工自助门户', 'Employee self-portal'],
    ['Wave6', '报销页打通', 'Claim page wired'],
    ['Wave7', '数据一致化 + 布局防溢出', 'Data consistency + layout'],
    ['Wave8', 'AI 对话式拍照识别', 'AI conversational OCR'],
    ['Wave9', '系统架构图谱 + 双语说明书', 'Architecture map + bilingual manual'],
  ];
  const waveHtml = waves.map((w, i) => `
    <div class="arch-wave ${i === waves.length - 1 ? 'now' : ''}">
      <span class="arch-wave-dot"></span>
      <span class="arch-wave-tx"><b>${w[0]}</b> ${w[1]} <i>· ${w[2]}</i></span>
    </div>`).join('');

  // ════ 渲染 ════
  $('#view').innerHTML = `
  <div class="arch-page">
    <button class="arch-back" onclick="go('dashboard')"><i class="fas fa-arrow-left"></i> 返回工作台 / Back</button>

    <!-- 品牌头图 -->
    <header class="arch-hero">
      <div class="arch-hero-logo" style="background:${G.color}">${G.logo}</div>
      <h1>Paydaes ClaimGPT</h1>
      <p class="arch-hero-tag">集团级 AI-Native 报销 · 薪资 · 合规智能平台</p>
      <p class="arch-hero-tag-en">Enterprise AI-Native Expense · Payroll · Compliance Platform</p>
      <div class="arch-hero-stats">
        <div><b>5+8</b><span>智能体 / Agents</span></div>
        <div><b>18</b><span>业务模块 / Modules</span></div>
        <div><b>6</b><span>角色权限 / Roles</span></div>
        <div><b>9</b><span>迭代波次 / Waves</span></div>
      </div>
    </header>

    <!-- 锚点导航 -->
    <nav class="arch-toc">
      <a href="#arch-flow"><i class="fas fa-arrows-turn-right"></i> 请求旅程 / Journey</a>
      <a href="#arch-layers"><i class="fas fa-layer-group"></i> 五层架构 / Layers</a>
      <a href="#arch-agents"><i class="fas fa-robot"></i> 智能体手册 / Agents</a>
      <a href="#arch-modules"><i class="fas fa-cubes"></i> 18 模块 / Modules</a>
      <a href="#arch-roles"><i class="fas fa-users-gear"></i> 角色权限 / Roles</a>
      <a href="#arch-tech"><i class="fas fa-screwdriver-wrench"></i> 技术与合规 / Tech</a>
    </nav>

    <section class="arch-sec" id="arch-flow">
      ${biH2('fa-arrows-turn-right', '一次请求的旅程', 'The Journey of a Request')}
      <div class="arch-flowbar">${flowHtml}</div>
    </section>

    <section class="arch-sec" id="arch-layers">
      ${biH2('fa-layer-group', '五层架构图谱', '5-Layer Architecture')}
      <div class="arch-stack-wrap">${layerCards}</div>
    </section>

    <section class="arch-sec" id="arch-agents">
      ${biH2('fa-robot', 'AI 智能体团队 · 功能手册', 'AI Agent Team · Function Manual')}
      <div class="arch-amx-wrap">${agentManualHtml}</div>
      <div class="arch-sublabel">支撑子智能体(8)/ Supporting sub-agents (8)</div>
      <div class="arch-subcards">${subChips}</div>
    </section>

    <section class="arch-sec" id="arch-modules">
      ${biH2('fa-cubes', '18 个业务模块 · 逐条详解', '18 Business Modules · Detailed')}
      <div class="arch-mmx">${moduleManualHtml}</div>
    </section>

    <section class="arch-sec" id="arch-roles">
      ${biH2('fa-users-gear', '6 角色权限模型 · 权责详解', '6-Role Permission Model · Responsibilities')}
      <div class="arch-rolesx">${roleCards}</div>
    </section>

    ${SHOW_INTERNAL ? `
    <section class="arch-sec" id="arch-tech">
      ${biH2('fa-screwdriver-wrench', '技术栈', 'Tech Stack')}
      <div class="arch-stacks">${stackHtml}</div>
    </section>` : ''}

    <section class="arch-sec">
      ${biH2('fa-shield-halved', '合规与精度内核', 'Compliance & Precision Core')}
      <div class="arch-comp">${compHtml}</div>
    </section>

    <section class="arch-sec">
      ${biH2('fa-timeline', '迭代历程 · 九波进化', 'Evolution · 9 Waves')}
      <div class="arch-waves">${waveHtml}</div>
    </section>

    ${SHOW_INTERNAL ? `
    <section class="arch-sec">
      <div class="rm-entry" id="goto-roadmap">
        <div class="rm-entry-ic"><i class="fas fa-rocket"></i></div>
        <div class="rm-entry-tx">
          <div class="rm-entry-zh">商业化路线图 · 从原型到正式商用</div>
          <div class="rm-entry-en">Commercialization Roadmap · From Prototype to Production</div>
        </div>
        <i class="fas fa-arrow-right rm-entry-arrow"></i>
      </div>
    </section>` : ''}

    <footer class="arch-foot">
      Paydaes ClaimGPT · 集团版 V3.0<br>
      <i>Paydaes ClaimGPT · Enterprise V3.0</i>
    </footer>
  </div>`;
  const rmBtn = $('#goto-roadmap');
  if (rmBtn) rmBtn.onclick = () => go('__roadmap');
}
window.renderArchitecture = renderArchitecture;

// ═══════════════════════════════════════════════
// 商业化路线图 · Commercialization Roadmap
// 从已跑通的原型 → 正式商用(多用户·多国家·全程最强AI辅助开发)
// ═══════════════════════════════════════════════
function renderRoadmap() {
  const G = S.group ? S.group : { logo: 'P', color: '#20c997' };

  // ── 现状基线(真实家底) ──
  const baseline = [
    ['6,677 行', 'Python 后端', '13 个 AI Agent 编排已跑通'],
    ['60 个', 'API 接口', '报销/审批/薪资/报表全链路'],
    ['7 国', '多租户税则', 'SG/MY/TH/VN/ID/HK/CN'],
    ['11 张表', 'SQLite 持久化', '真实写库,非内存模拟'],
  ];

  // ── 五大阶段路线图 ──
  const phases = [
    { p:'P0', wk:'第 1-3 周', zh:'生产加固', en:'Production Hardening', color:'#ef4444',
      goal_zh:'补齐"从演示到生产"的安全与质量底座', goal_en:'Build the security & quality foundation',
      items:[
        ['真实认证体系', 'JWT + 会话 + 密码加密(替换"选身份"演示模式)'],
        ['权限分级 RBAC', '6 角色 × 18 模块的细粒度权限矩阵'],
        ['接口安全加固', '限流/防注入/审计日志/敏感数据脱敏'],
        ['自动化测试', 'AI 生成单元+集成测试,覆盖核心 60 接口'],
      ]},
    { p:'P1', wk:'第 4-6 周', zh:'上云部署', en:'Cloud Deployment', color:'#f59e0b',
      goal_zh:'拿到永久稳定地址,数据不再丢失', goal_en:'Permanent URL + persistent data',
      items:[
        ['数据库升级', 'SQLite → PostgreSQL(Supabase/云托管)'],
        ['容器化部署', 'Docker + Railway/云服务器,CI/CD 自动发布'],
        ['对象存储', '票据图片/导出文件迁移到 S3/R2 云存储'],
        ['域名+HTTPS', '绑定企业域名,SSL 证书,CDN 加速'],
      ]},
    { p:'P2', wk:'第 7-12 周', zh:'多租户 SaaS 化', en:'Multi-Tenant SaaS', color:'#20c997',
      goal_zh:'一套系统服务 N 个企业客户,数据彻底隔离', goal_en:'One system, N enterprise clients, fully isolated',
      items:[
        ['租户隔离架构', '企业级数据隔离,每客户独立数据空间'],
        ['企业自助开通', '注册→建组织→邀成员→配模块 全自助'],
        ['订阅计费系统', '按席位/按用量计费,对接 Stripe 支付'],
        ['并发性能优化', '连接池/缓存/异步队列,支撑千人同时在线'],
      ]},
    { p:'P3', wk:'第 13-18 周', zh:'多国合规深化', en:'Multi-Country Compliance', color:'#3b82f6',
      goal_zh:'每个国家的税则/法定报表真实可用、随政策更新', goal_en:'Real, auditable, policy-synced compliance per country',
      items:[
        ['真实税率引擎', '7 国 IRAS/LHDN 等真实税表,可配置版本化'],
        ['法定报表落地', 'EPF/EA Form/IR8A 等格式与官方一致并可申报'],
        ['会计直推接口', '凭证直推 Xero/QuickBooks/SQL Account'],
        ['本地化与货币', '多语言/多币种/本地节假日与汇率自动更新'],
      ]},
    { p:'P4', wk:'第 19-24 周', zh:'商业化运营', en:'Commercial Operations', color:'#8b5cf6',
      goal_zh:'可签约、可交付、可持续运营的正式商用形态', goal_en:'Contract-ready, deliverable, sustainable operations',
      items:[
        ['客户成功体系', '入驻引导/帮助中心/工单/SLA 保障'],
        ['数据看板与BI', '管理者驾驶舱,成本/合规/效率多维分析'],
        ['安全合规认证', '数据隐私合规(PDPA/GDPR),渗透测试'],
        ['灾备与监控', '自动备份/告警/7×24 监控,99.9% 可用性'],
      ]},
  ];

  // ── 多用户·多国家稳定性五支柱 ──
  const pillars = [
    ['fa-key', '身份与权限', 'Identity & Access', 'JWT 认证 + RBAC 权限 + 多租户隔离,确保每个用户只看到自己该看的数据'],
    ['fa-bolt', '高并发性能', 'Performance', '连接池 + 缓存 + 异步队列,千人同时在线不卡顿,接口 P95 < 300ms'],
    ['fa-globe', '多国合规', 'Compliance', '7 国税则版本化管理,政策更新即时同步,报表与官方格式一致'],
    ['fa-database', '数据可靠', 'Reliability', '云数据库 + 自动备份 + 灾备切换,数据零丢失,RPO < 5 分钟'],
    ['fa-chart-line', '可观测运维', 'Observability', '全链路监控 + 告警 + 审计日志,故障 5 分钟内发现,99.9% 可用'],
  ];

  // ── 精简团队配置(全程最强 AI 辅助开发) ──
  const team = [
    ['1 人', '产品负责人 / 您', '需求定义、商业决策、客户对接'],
    ['1-2 人', '全栈工程师 + AI', 'AI 辅助开发,1 人产出≈传统 3-4 人'],
    ['0.5 人', '合规顾问(兼职)', '提供各国真实税则与法定报表口径'],
    ['0.5 人', '测试/运维(可AI替代)', 'AI 自动化测试 + 云平台托管运维'],
  ];

  // ── 关键里程碑(可商用判定标准) ──
  const milestones = [
    ['M1 · 第3周', '安全可上线', '真实认证 + 权限 + 测试通过', '#ef4444'],
    ['M2 · 第6周', '云端永久可访问', '生产环境稳定运行,数据持久化', '#f59e0b'],
    ['M3 · 第12周', '可服务首个付费客户', 'SaaS 多租户 + 计费打通', '#20c997'],
    ['M4 · 第18周', '多国合规真实可用', '税则/报表/会计接口落地', '#3b82f6'],
    ['M5 · 第24周', '✅ 正式商业化运营', 'SLA/监控/灾备/合规认证齐备', '#8b5cf6'],
  ];

  const baselineHtml = baseline.map(b => `
    <div class="rm-base-card">
      <div class="rm-base-num">${b[0]}</div>
      <div class="rm-base-lbl">${b[1]}</div>
      <div class="rm-base-desc">${b[2]}</div>
    </div>`).join('');

  const phaseHtml = phases.map((ph, i) => `
    <div class="rm-phase" style="--pc:${ph.color}">
      <div class="rm-phase-head">
        <span class="rm-phase-tag">${ph.p}</span>
        <div class="rm-phase-titles">
          <div class="rm-phase-zh">${ph.zh}</div>
          <div class="rm-phase-en">${ph.en}</div>
        </div>
        <span class="rm-phase-wk">${ph.wk}</span>
      </div>
      <div class="rm-phase-goal">🎯 ${ph.goal_zh}<br><i>${ph.goal_en}</i></div>
      <div class="rm-phase-items">
        ${ph.items.map(it => `<div class="rm-item"><b>${it[0]}</b><span>${it[1]}</span></div>`).join('')}
      </div>
    </div>`).join('');

  // 甘特时间轴(24 周)
  const ganttRows = phases.map(ph => {
    const m = ph.wk.match(/(\d+)-(\d+)/);
    const s = m ? parseInt(m[1]) : 1, e = m ? parseInt(m[2]) : 24;
    const left = ((s-1)/24*100).toFixed(1), width = ((e-s+1)/24*100).toFixed(1);
    return `<div class="rm-gantt-row">
      <div class="rm-gantt-lbl"><b>${ph.p}</b> ${ph.zh}</div>
      <div class="rm-gantt-track"><div class="rm-gantt-bar" style="left:${left}%;width:${width}%;background:${ph.color}">${ph.wk.replace('第 ','').replace(' 周','w')}</div></div>
    </div>`;
  }).join('');

  const pillarHtml = pillars.map(p => `
    <div class="rm-pillar">
      <div class="rm-pillar-ic"><i class="fas ${p[0]}"></i></div>
      <div class="rm-pillar-zh">${p[1]}</div>
      <div class="rm-pillar-en">${p[2]}</div>
      <div class="rm-pillar-desc">${p[3]}</div>
    </div>`).join('');

  const teamHtml = team.map(t => `
    <tr><td class="rm-team-n">${t[0]}</td><td><b>${t[1]}</b></td><td>${t[2]}</td></tr>`).join('');

  const msHtml = milestones.map(m => `
    <div class="rm-ms" style="--mc:${m[3]}">
      <div class="rm-ms-dot"></div>
      <div class="rm-ms-body">
        <div class="rm-ms-when">${m[0]}</div>
        <div class="rm-ms-what">${m[1]}</div>
        <div class="rm-ms-crit">${m[2]}</div>
      </div>
    </div>`).join('');

  $('#view').innerHTML = `
  <div class="arch-page rm-page">
    <header class="arch-hero" style="--hc:${G.color}">
      <div class="arch-hero-logo" style="background:${G.color}">${G.logo}</div>
      <h1>商业化路线图 <span class="arch-hero-tag-en">Commercialization Roadmap</span></h1>
      <p class="arch-hero-sub">从已跑通的产品原型,到多用户·多国家稳定运营的正式商用<br>
        <i>From a working prototype to multi-user, multi-country production — AI-accelerated delivery</i></p>
      <div class="rm-hero-badge">⚡ 全程最强 AI 辅助开发 · 预计 <b>24 周</b>达成正式商用 / AI-accelerated · ~24 weeks to production</div>
    </header>

    <section class="arch-sec">
      ${biH2('fa-flag-checkered', '现状基线 · 已完成约 75% 功能原型', 'Baseline · ~75% Prototype Done')}
      <div class="rm-baseline">${baselineHtml}</div>
    </section>

    <section class="arch-sec">
      ${biH2('fa-map-signs', '五阶段路线图', 'Five-Phase Roadmap')}
      <div class="rm-phases">${phaseHtml}</div>
    </section>

    <section class="arch-sec">
      ${biH2('fa-bars-staggered', '时间轴 · 24 周甘特图', 'Timeline · 24-Week Gantt')}
      <div class="rm-gantt">
        <div class="rm-gantt-axis"><span>W1</span><span>W6</span><span>W12</span><span>W18</span><span>W24</span></div>
        ${ganttRows}
      </div>
    </section>

    <section class="arch-sec">
      ${biH2('fa-shield-halved', '多用户·多国家稳定性五支柱', '5 Pillars of Multi-User · Multi-Country Stability')}
      <div class="rm-pillars">${pillarHtml}</div>
    </section>

    <section class="arch-sec">
      ${biH2('fa-users-gear', '精简团队配置(AI 提效)', 'Lean Team (AI-Boosted)')}
      <table class="rm-team-table">
        <thead><tr><th>人力 / Headcount</th><th>角色 / Role</th><th>职责 / Responsibility</th></tr></thead>
        <tbody>${teamHtml}</tbody>
      </table>
      <div class="rm-team-note">💡 全程最强 AI 辅助开发:1 名全栈工程师产出 ≈ 传统 3-4 人团队,大幅压缩周期与成本<br>
        <i>With top-tier AI assistance, 1 full-stack engineer ≈ a traditional 3-4 person team</i></div>
    </section>

    <section class="arch-sec">
      ${biH2('fa-trophy', '关键里程碑 · 可商用判定', 'Key Milestones · Go-Live Criteria')}
      <div class="rm-milestones">${msHtml}</div>
    </section>

    <footer class="arch-foot">
      Paydaes ClaimGPT · 商业化路线图 V1.0 · ${new Date().getFullYear()}<br>
      <i>Commercialization Roadmap · Subject to scope & resource adjustment</i>
    </footer>
  </div>`;
  const ws = document.querySelector('#workspace');
  if (ws) ws.scrollTo(0, 0);
}
window.renderRoadmap = renderRoadmap;

