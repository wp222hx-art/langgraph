// ClaimGPT 前端核心交互
let AGENTS = [], current = null, busy = false;
const threadId = 'web-' + Math.random().toString(36).slice(2, 8);

const $ = s => document.querySelector(s);
const messages = $('#messages');

// ── 初始化:加载 5 主 Agent ──
async function init() {
  const r = await fetch('/api/agents').then(r => r.json());
  AGENTS = r.agents;
  const m = await fetch('/api/modules').then(r => r.json());
  $('#module-count').textContent = m.count;
  renderAgentList();
  selectAgent(AGENTS[0]);
}

function renderAgentList() {
  $('#agent-list').innerHTML = AGENTS.map(a => `
    <div class="agent-item rounded-xl p-3 hover:bg-slate-50" data-id="${a.id}" style="--c:${a.color}">
      <div class="flex items-center gap-2.5">
        <span class="text-xl">${a.emoji}</span>
        <div class="min-w-0 flex-1">
          <div class="font-medium text-sm text-slate-800">${a.name}</div>
          <div class="text-[11px] text-slate-400 truncate">${a.modules.length} 个模块</div>
        </div>
      </div>
    </div>`).join('');
  document.querySelectorAll('.agent-item').forEach(el =>
    el.onclick = () => selectAgent(AGENTS.find(a => a.id === el.dataset.id)));
}

function selectAgent(a) {
  current = a;
  document.querySelectorAll('.agent-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === a.id));
  $('#header-emoji').textContent = a.emoji;
  $('#header-name').textContent = a.name;
  $('#header-desc').textContent = a.desc;
  $('#header-modules').innerHTML = a.modules.map(m =>
    `<span class="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">${m}</span>`).join('');
  $('#samples').innerHTML = a.samples.map(s =>
    `<button class="sample-chip text-xs px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-600 hover:border-indigo-300 hover:text-indigo-600"
       onclick="quickSend('${s}')">${s}</button>`).join('');
  if (!messages.dataset.greeted || messages.dataset.lastAgent !== a.id) {
    addAI(`${a.emoji} 你好,我是**${a.name}**。${a.desc}。直接和我对话,或点下方示例试试 👇`);
    messages.dataset.greeted = '1';
    messages.dataset.lastAgent = a.id;
  }
}

function quickSend(t) { $('#input').value = t; send(); }

// ── 消息渲染 ──
function addUser(text) {
  messages.insertAdjacentHTML('beforeend',
    `<div class="msg-user flex justify-end"><div class="bubble">${esc(text)}</div></div>`);
  scroll();
}
function addAI(text) {
  const id = 'ai' + Date.now();
  messages.insertAdjacentHTML('beforeend',
    `<div class="msg-ai flex gap-3"><span class="text-xl mt-1">${current.emoji}</span>
       <div class="flex-1"><div class="bubble" id="${id}">${fmt(text)}</div></div></div>`);
  scroll(); return id;
}

// ── 流式发送(SSE)──
function send() {
  const input = $('#input');
  const text = input.value.trim();
  if (!text || busy) return;
  input.value = ''; input.style.height = 'auto';
  addUser(text);
  busy = true; $('#send-btn').disabled = true;

  // 思考框
  const thinkId = 'think' + Date.now();
  messages.insertAdjacentHTML('beforeend',
    `<div class="msg-ai flex gap-3" id="wrap-${thinkId}"><span class="text-xl mt-1">${current.emoji}</span>
       <div class="flex-1 space-y-2"><div class="think-box" id="${thinkId}">
         <div class="text-[11px] text-slate-400 mb-1"><span class="think-dot">●</span> 智能体团队正在协作思考…</div>
       </div></div></div>`);
  scroll();

  let bubbleId = null, routeBadge = '';
  const es = new EventSource(`/api/chat/stream?message=${encodeURIComponent(text)}&thread_id=${threadId}`);

  es.addEventListener('route', e => {
    const d = JSON.parse(e.data);
    // 自动切到对应 Agent
    const target = AGENTS.find(a => a.id === d.agent);
    if (target && target.id !== current.id) selectAgent(target);
    routeBadge = `<span class="text-[10px] px-2 py-0.5 rounded bg-indigo-50 text-indigo-500 ml-1">${d.module}</span>`;
    if (d.needs_human)
      routeBadge += `<span class="text-[10px] px-2 py-0.5 rounded bg-red-50 text-red-500 ml-1"><i class="fas fa-user-shield"></i> ${d.hil_level} 人机协同</span>`;
  });

  es.addEventListener('think', e => {
    const d = JSON.parse(e.data);
    $('#' + thinkId).insertAdjacentHTML('beforeend',
      `<div class="think-step flex items-center gap-2 text-xs text-slate-500 py-0.5">
        <i class="fas fa-check-circle text-emerald-400"></i>
        <b class="text-slate-600">${d.agent}</b>
        <span>${d.action}</span>
        ${d.detail ? `<span class="text-slate-300">· ${d.detail}</span>` : ''}
      </div>`);
    scroll();
  });

  es.addEventListener('token', e => {
    if (!bubbleId) {
      // 思考完成,折叠思考框,开始正式回复
      const tb = $('#' + thinkId);
      tb.querySelector('.text-\\[11px\\]').innerHTML =
        `<i class="fas fa-check-double text-emerald-400"></i> 思考完成 ${routeBadge}`;
      bubbleId = addAI('');
      $('#' + bubbleId).classList.add('cursor');
    }
    const b = $('#' + bubbleId);
    b._raw = (b._raw || '') + JSON.parse(e.data).char;
    b.innerHTML = fmt(b._raw);
    b.classList.add('cursor');
    scroll();
  });

  es.addEventListener('card', e => {
    renderCard(JSON.parse(e.data));
    scroll();
  });

  es.addEventListener('done', e => {
    if (bubbleId) $('#' + bubbleId).classList.remove('cursor');
    es.close(); busy = false; $('#send-btn').disabled = false;
  });

  es.onerror = () => { es.close(); busy = false; $('#send-btn').disabled = false; };
}

// ── 卡片渲染(混合界面)──
function renderCard(card) {
  let body = '';
  const d = card.data;
  switch (card.type) {
    case 'claim':
      body = Object.entries(d).map(([k, v]) =>
        `<div class="flex justify-between py-1 text-sm border-b border-slate-50"><span class="text-slate-400">${k}</span><b class="text-slate-700">${v}</b></div>`).join('') +
        `<div class="flex gap-2 mt-3"><button class="flex-1 bg-indigo-600 text-white text-sm py-2 rounded-lg">确认提交</button><button class="px-4 text-sm py-2 rounded-lg border border-slate-200 text-slate-500">修改</button></div>`;
      break;
    case 'entitlement':
      body = Object.entries(d).map(([k, v]) =>
        `<div class="flex justify-between py-1 text-sm"><span class="text-slate-400">${k}</span><b class="text-slate-700">${v}</b></div>`).join('');
      break;
    case 'approval':
      body = approvalTable(d); break;
    case 'payroll':
      body = d.steps.map(s =>
        `<div class="flex items-center gap-2 py-1.5 text-sm"><i class="fas fa-check-circle text-emerald-500"></i><span class="flex-1">${s.step}</span><span class="text-slate-400 text-xs">${s.result}</span></div>`).join('') +
        `<div class="mt-2 text-xs text-emerald-600 bg-emerald-50 rounded-lg px-3 py-2">✅ 共处理 ${d.total} 条单据,全部成功</div>`;
      break;
    case 'chart':
      body = `<canvas id="ch${Date.now()}" height="160"></canvas>`; break;
    case 'table':
      body = genTable(d); break;
    case 'family':
      body = (d.members || []).map(m => `<div class="flex items-center gap-2 py-1 text-sm"><i class="fas fa-user text-slate-300"></i>${m.relation}:<b>${m.name}</b></div>`).join('');
      break;
    case 'report':
      body = (d.options || []).map(o => `<button class="block w-full text-left text-sm px-3 py-2 rounded-lg hover:bg-slate-50 border border-slate-100 mb-1.5"><i class="fas fa-file-export text-indigo-400 mr-2"></i>${o}</button>`).join('');
      break;
    default:
      body = `<pre class="text-xs">${JSON.stringify(d, null, 2)}</pre>`;
  }
  const cid = 'card' + Date.now();
  messages.insertAdjacentHTML('beforeend',
    `<div class="msg-ai flex gap-3"><span class="text-xl opacity-0">·</span>
      <div class="card" id="${cid}"><div class="card-head">${card.title}</div><div class="card-body">${body}</div></div></div>`);
  if (card.type === 'chart') drawChart($('#' + cid).querySelector('canvas'), d);
}

function approvalTable(d) {
  const rows = d.rows.map(r =>
    `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td><span class="risk-badge risk-${r[4]}">${r[4]}</span></td><td class="text-slate-400">${r[5]}</td></tr>`).join('');
  const s = d.summary;
  return `<div class="flex gap-2 mb-3 text-xs">
      <span class="risk-badge risk-低">🟢 低 ${s['低风险']}</span>
      <span class="risk-badge risk-中">🟡 中 ${s['中风险']}</span>
      <span class="risk-badge risk-高">🔴 高 ${s['高风险']}</span></div>
    <table class="mini-table"><thead><tr>${d.headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>
    <div class="flex gap-2 mt-3"><button class="flex-1 bg-emerald-600 text-white text-sm py-2 rounded-lg">一键批量通过低风险</button><button class="flex-1 border border-red-200 text-red-500 text-sm py-2 rounded-lg">逐张审高风险</button></div>`;
}

function genTable(d) {
  const head = d.headers ? `<thead><tr>${d.headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>` : '';
  const rows = d.rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('');
  return `<table class="mini-table">${head}<tbody>${rows}</tbody></table>`;
}

function drawChart(canvas, d) {
  new Chart(canvas, {
    type: d.kind || 'bar',
    data: { labels: d.labels, datasets: d.series.map(s => ({ label: s.name, data: s.data,
      backgroundColor: 'rgba(99,102,241,.7)', borderRadius: 6 })) },
    options: { plugins: { legend: { display: true, labels: { font: { size: 11 } } } },
      scales: { y: { beginAtZero: true } }, responsive: true, maintainAspectRatio: false }
  });
}

// ── 工具 ──
function esc(s) { return s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])); }
function fmt(s) {
  return esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
}
function scroll() { messages.scrollTop = messages.scrollHeight; }

// 输入框自适应高度 + 回车发送
$('#input').addEventListener('input', e => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px'; });
$('#input').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
$('#send-btn').onclick = send;
$('#photo-btn').onclick = () => quickSend('我拍了张发票要报销');

init();
