/* AI 面试备考助手 - 单页应用逻辑（纯原生 JS，无构建依赖） */

// ===== 工具函数 =====
const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));

const DIM_LABELS = {
  communication: '沟通表达',
  professional_fit: '岗位专业匹配',
  experience_fit: '经验匹配',
  adaptability: '应变能力',
};
const YEARS_OPTIONS = { '0-1': '0-1 年', '1-3': '1-3 年', '3-5': '3-5 年' };
const SALARY_OPTIONS = { low: '基础/初级', mid: '中级', high: '高级/资深' };
const QUICK_POSITIONS = ['会计', 'HR', '前台', '销售', '技术开发', '运营'];

// ===== 全局状态 =====
const state = {
  token: localStorage.getItem('token') || '',
  email: localStorage.getItem('email') || '',
  sub: null,          // 订阅状态 {status, plan}
  tab: 'interview',   // interview / bank / records / account
  interview: null,    // 面试流程状态
};

// ===== API 封装 =====
async function api(path, method = 'GET', body) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const resp = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || `请求失败（${resp.status}）`);
  }
  return data;
}

// ===== 渲染入口 =====
function render() {
  renderUserBar();
  const app = $('#app');
  if (!state.token) {
    app.innerHTML = renderAuth();
    bindAuth();
  } else {
    app.innerHTML = renderMain();
    bindMain();
  }
}

function renderUserBar() {
  const bar = $('#user-bar');
  if (!state.token) {
    bar.innerHTML = '';
    return;
  }
  const premium = state.sub && state.sub.status === 'premium';
  bar.innerHTML = `
    <span class="muted small">${esc(state.email)}</span>
    ${premium ? '<span class="badge premium">订阅用户</span>' : '<span class="badge">免费用户</span>'}
    <button class="btn ghost small" onclick="logout()">退出</button>
  `;
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('email');
  state.token = '';
  state.email = '';
  state.sub = null;
  state.interview = null;
  render();
}

// ===== 认证视图 =====
function renderAuth() {
  return `
    <div class="card" style="max-width:420px;margin:40px auto;">
      <h2 style="margin-top:0;">登录 / 注册</h2>
      <p class="muted small">邮箱 + 密码即可开始，本地用户系统</p>
      <label>邮箱</label>
      <input id="auth-email" type="email" placeholder="you@example.com">
      <label>密码（至少 6 位）</label>
      <input id="auth-password" type="password" placeholder="请输入密码">
      <div class="row mt">
        <button class="btn" id="btn-login">登录</button>
        <button class="btn secondary" id="btn-register">注册</button>
      </div>
      <p id="auth-msg" class="muted small mt"></p>
    </div>
  `;
}

function bindAuth() {
  const email = () => $('#auth-email').value.trim();
  const password = () => $('#auth-password').value;
  const msg = (m) => { $('#auth-msg').textContent = m; };

  $('#btn-login').onclick = async () => {
    try {
      const r = await api('/api/auth/login', 'POST', { email: email(), password: password() });
      setSession(r);
    } catch (e) { msg(e.message); }
  };
  $('#btn-register').onclick = async () => {
    try {
      const r = await api('/api/auth/register', 'POST', { email: email(), password: password() });
      setSession(r);
    } catch (e) { msg(e.message); }
  };
}

function setSession(r) {
  state.token = r.token;
  state.email = r.email;
  localStorage.setItem('token', r.token);
  localStorage.setItem('email', r.email);
  state.tab = 'interview';
  loadSubThenRender();
}

// ===== 主视图 =====
function renderMain() {
  const tabs = [
    ['interview', '🎤 模拟面试'],
    ['bank', '📚 题库'],
    ['records', '📈 练习记录'],
    ['account', '👤 我的'],
  ];
  return `
    <div class="tabs">
      ${tabs.map(([k, label]) => `<button class="tab ${state.tab === k ? 'active' : ''}" data-tab="${k}">${label}</button>`).join('')}
    </div>
    <div id="view"></div>
  `;
}

function bindMain() {
  document.querySelectorAll('.tab').forEach((el) => {
    el.onclick = () => { state.tab = el.dataset.tab; render(); };
  });
  const view = $('#view');
  if (state.tab === 'interview') view.innerHTML = renderInterview();
  if (state.tab === 'bank') view.innerHTML = renderBank();
  if (state.tab === 'records') view.innerHTML = renderRecords();
  if (state.tab === 'account') view.innerHTML = renderAccount();

  bindInterview();
  bindBank();
  bindRecords();
  bindAccount();
}

// ===== 模拟面试 =====
function newInterview() {
  return {
    position: '', years_range: '0-1', salary_tier: 'mid', job_desc: '',
    questions: [], answers: [], followups: [],
    notice: null, source: '', scorecard: null,
    generating: false, scoring: false,
  };
}

function renderInterview() {
  const it = state.interview || newInterview();
  if (!it.questions.length && !it.scorecard) {
    return renderSetup(it);
  }
  return renderStage(it);
}

function renderSetup(it) {
  const chips = QUICK_POSITIONS
    .map((p) => `<span class="chip ${it.position === p ? 'active' : ''}" data-pos="${p}">${p}</span>`).join('');
  return `
    <div class="card">
      <h2 style="margin-top:0;">🎯 选择你的目标岗位</h2>
      <p class="muted small">任意岗位均可，也可填写职责描述让出题更精准</p>
      <label>目标岗位 *</label>
      <input id="it-position" value="${esc(it.position)}" placeholder="例如：会计 / 新媒体运营 / 前端开发 …">
      <div class="chips" id="quick-chips">${chips}</div>
      <label>岗位职责描述（选填）</label>
      <textarea id="it-desc" placeholder="例如：负责公司全盘账务处理、纳税申报与成本核算…">${esc(it.job_desc)}</textarea>
      <div class="grid-2">
        <div>
          <label>工作年限</label>
          <select id="it-years">
            ${Object.entries(YEARS_OPTIONS).map(([k, v]) => `<option value="${k}" ${it.years_range === k ? 'selected' : ''}>${v}</option>`).join('')}
          </select>
        </div>
        <div>
          <label>期望薪资档</label>
          <select id="it-salary">
            ${Object.entries(SALARY_OPTIONS).map(([k, v]) => `<option value="${k}" ${it.salary_tier === k ? 'selected' : ''}>${v}</option>`).join('')}
          </select>
        </div>
      </div>
      <div class="mt">
        <button class="btn" id="btn-generate">${it.generating ? '出题中…' : '开始模拟面试'}</button>
      </div>
      <p id="setup-msg" class="muted small mt"></p>
    </div>
  `;
}

function renderStage(it) {
  // 评分完成则展示评分卡
  if (it.scorecard) {
    return renderScorecard(it);
  }

  const notice = it.notice ? `<div class="notice">⚠️ ${esc(it.notice)}</div>` : '';
  const qs = it.questions.map((q, i) => {
    const sourceBadge = q.source === '题库'
      ? '<span class="badge bank">来自预设题库</span>'
      : '<span class="badge ai">AI 即时生成</span>';
    const followups = it.followups
      .filter((f) => f.parent === i)
      .map((f, fi) => `
        <div class="question-item">
          <div class="q-text">🔁 追问：${esc(f.question)}</div>
          <textarea data-followup="${i}-${fi}" placeholder="请输入你的回答…">${esc(f.answer)}</textarea>
        </div>
      `).join('');
    return `
      <div class="question-item">
        <div class="row">
          <div class="q-text">${i + 1}. ${esc(q.question)}</div>
          ${sourceBadge}
        </div>
        <textarea data-main="${i}" placeholder="请输入你的回答…">${esc(it.answers[i] || '')}</textarea>
        ${followups}
        <div class="mt">
          <button class="btn secondary small" data-followup-btn="${i}">+ 追问</button>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="card">
      <div class="row">
        <h2 style="margin:0;">🎤 ${esc(it.position)} 面试</h2>
        <span class="badge">${esc(it.source)}</span>
      </div>
      <p class="muted small">年限：${YEARS_OPTIONS[it.years_range]} · 薪资：${SALARY_OPTIONS[it.salary_tier]}</p>
      ${notice}
      ${qs}
      <div class="mt">
        <button class="btn" id="btn-score">${it.scoring ? '评分中…' : '提交并评分'}</button>
        <button class="btn ghost" id="btn-reset">重新出题</button>
      </div>
      <p id="stage-msg" class="muted small mt"></p>
    </div>
  `;
}

function renderScorecard(it) {
  const sc = it.scorecard;
  const dims = Object.entries(sc.dimensions).map(([k, d]) => `
    <div class="score-row">
      <span style="width:110px;">${DIM_LABELS[k]}</span>
      <div class="score-bar"><span style="width:${d.score * 20}%"></span></div>
      <span><b>${d.score}</b>/5</span>
    </div>
    <div class="muted small" style="margin:-4px 0 12px 110px;">${esc(d.comment)}</div>
  `).join('');

  const suggestions = sc.suggestions && sc.suggestions.length
    ? `<ul>${sc.suggestions.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>`
    : `<p class="lock-hint">🔒 ${esc(sc.locked || '订阅后解锁详细改进建议与 AI 深度解析')}</p>`;

  return `
    <div class="card">
      <h2 style="margin-top:0;">📋 面试表现评分卡</h2>
      <div class="grid-2">
        <div>
          <div class="big-number">${sc.total_score}<span class="muted small">/20</span></div>
          <div class="muted small" style="text-align:center;">总分</div>
        </div>
        <div>
          <div class="hire-number">${sc.hire_probability}%</div>
          <div class="muted small" style="text-align:center;">录取概率</div>
        </div>
      </div>
      ${dims}
      <h3>总评</h3>
      <p>${esc(sc.summary)}</p>
      <h3>改进建议</h3>
      ${suggestions}
      <div class="notice" style="margin-top:16px;">⚠️ 模拟结果，仅供参考，不代表真实录取结果</div>
      <div class="mt">
        <button class="btn" id="btn-again">再来一次</button>
        <button class="btn ghost" data-goto="records">查看练习记录</button>
      </div>
    </div>
  `;
}

function bindInterview() {
  const it = state.interview;
  if (!it) return;

  // 设置表单
  const posInput = $('#it-position');
  if (posInput) {
    posInput.oninput = () => { it.position = posInput.value; };
    $('#quick-chips').onclick = (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      it.position = chip.dataset.pos;
      render();
    };
    $('#it-desc').oninput = (e) => { it.job_desc = e.target.value; };
    $('#it-years').onchange = (e) => { it.years_range = e.target.value; };
    $('#it-salary').onchange = (e) => { it.salary_tier = e.target.value; };
    $('#btn-generate').onclick = async () => {
      if (!it.position.trim()) { $('#setup-msg').textContent = '请填写目标岗位'; return; }
      it.generating = true;
      render();
      try {
        const r = await api('/api/interview/generate', 'POST', {
          position: it.position.trim(), years_range: it.years_range,
          salary_tier: it.salary_tier, job_desc: it.job_desc, count: 3,
        });
        it.questions = r.questions;
        it.answers = r.questions.map(() => '');
        it.followups = [];
        it.notice = r.notice;
        it.source = r.source;
        it.generating = false;
        render();
      } catch (e) {
        it.generating = false;
        render();
        $('#setup-msg').textContent = e.message;
      }
    };
  }

  // 答题阶段
  const scoreBtn = $('#btn-score');
  if (scoreBtn) {
    document.querySelectorAll('textarea[data-main]').forEach((ta) => {
      ta.oninput = () => { it.answers[Number(ta.dataset.main)] = ta.value; };
    });
    document.querySelectorAll('textarea[data-followup]').forEach((ta) => {
      ta.oninput = () => {
        const [p, fi] = ta.dataset.followup.split('-').map(Number);
        const f = it.followups.find((x) => x.parent === p && x.index === fi);
        if (f) f.answer = ta.value;
      };
    });
    document.querySelectorAll('[data-followup-btn]').forEach((btn) => {
      btn.onclick = async () => {
        const i = Number(btn.dataset.followupBtn);
        const answer = it.answers[i] || '';
        if (!answer.trim()) { $('#stage-msg').textContent = '请先回答本题再追问'; return; }
        btn.disabled = true;
        btn.textContent = '追问中…';
        try {
          const r = await api('/api/interview/followup', 'POST', {
            position: it.position, years_range: it.years_range, salary_tier: it.salary_tier,
            question: it.questions[i].question, answer,
          });
          it.followups.push({ parent: i, index: it.followups.filter((f) => f.parent === i).length, question: r.question, answer: '' });
          render();
        } catch (e) {
          $('#stage-msg').textContent = e.message;
          btn.disabled = false;
          btn.textContent = '+ 追问';
        }
      };
    });
    scoreBtn.onclick = async () => {
      const qa = [];
      it.questions.forEach((q, i) => {
        const a = (it.answers[i] || '').trim();
        if (a) qa.push({ question: q.question, answer: a, source: q.source });
      });
      it.followups.forEach((f) => {
        if (f.answer.trim()) qa.push({ question: f.question, answer: f.answer, source: 'AI' });
      });
      if (!qa.length) { $('#stage-msg').textContent = '请至少回答一道题再提交'; return; }
      it.scoring = true;
      render();
      try {
        const r = await api('/api/interview/score', 'POST', {
          position: it.position, years_range: it.years_range, salary_tier: it.salary_tier, qa,
        });
        it.scorecard = r.scorecard;
        it.scoring = false;
        render();
      } catch (e) {
        it.scoring = false;
        render();
        $('#stage-msg').textContent = e.message;
      }
    };
    $('#btn-reset').onclick = () => { state.interview = newInterview(); render(); };
  }

  // 评分卡按钮
  const againBtn = $('#btn-again');
  if (againBtn) {
    againBtn.onclick = () => { state.interview = newInterview(); render(); };
    document.querySelector('[data-goto="records"]').onclick = () => { state.tab = 'records'; render(); };
  }
}

// ===== 题库视图 =====
function renderBank() {
  return `
    <div class="card">
      <h2 style="margin-top:0;">📚 预设题库</h2>
      <p class="muted small">高频面试题 + AI 深度解析（解析为订阅内容）</p>
      <label>选择岗位</label>
      <div class="chips" id="bank-chips">加载中…</div>
      <div id="bank-list" class="mt"></div>
    </div>
  `;
}

async function bindBank() {
  const chipsEl = $('#bank-chips');
  const listEl = $('#bank-list');
  let positions = [];
  try {
    const r = await api('/api/bank/positions');
    positions = r.positions;
  } catch (e) { chipsEl.textContent = '加载失败：' + e.message; return; }

  if (!positions.length) {
    chipsEl.innerHTML = '<span class="muted small">暂无预设题库</span>';
    return;
  }
  chipsEl.innerHTML = positions.map((p, i) =>
    `<span class="chip ${i === 0 ? 'active' : ''}" data-pos="${esc(p.position)}">${esc(p.position)}（${p.count}）</span>`
  ).join('');
  const load = async (pos) => {
    listEl.innerHTML = '<p class="muted small">加载中…</p>';
    try {
      const r = await api(`/api/bank?position=${encodeURIComponent(pos)}`);
      listEl.innerHTML = r.questions.map((q) => `
        <div class="question-item">
          <div class="q-text">${esc(q.question)}</div>
          ${q.locked
            ? `<div class="lock-hint">🔒 解析为订阅内容，<a href="#" data-goto="account">去订阅</a>后解锁</div>`
            : `<div class="analysis-box">${esc(q.analysis)}</div>`}
        </div>
      `).join('') || '<p class="muted small">该岗位暂无预设题目</p>';
      listEl.querySelectorAll('[data-goto="account"]').forEach((a) => {
        a.onclick = (e) => { e.preventDefault(); state.tab = 'account'; render(); };
      });
    } catch (e) { listEl.innerHTML = `<p class="muted small">加载失败：${esc(e.message)}</p>`; }
  };
  chipsEl.onclick = (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    chipsEl.querySelectorAll('.chip').forEach((c) => c.classList.remove('active'));
    chip.classList.add('active');
    load(chip.dataset.pos);
  };
  load(positions[0].position);
}

// ===== 练习记录视图 =====
function renderRecords() {
  return `
    <div class="card">
      <h2 style="margin-top:0;">📈 练习记录与成长曲线</h2>
      <canvas id="growth-chart" class="hidden"></canvas>
      <div id="records-table" class="mt"><p class="muted small">加载中…</p></div>
    </div>
  `;
}

async function bindRecords() {
  const tableEl = $('#records-table');
  try {
    const [recR, growthR] = await Promise.all([
      api('/api/records'),
      api('/api/records/growth'),
    ]);
    const records = recR.records;
    if (!records.length) {
      tableEl.innerHTML = '<p class="muted small">暂无练习记录，快去模拟面试吧～</p>';
      return;
    }
    tableEl.innerHTML = `
      <table>
        <thead><tr><th>时间</th><th>岗位</th><th>题目来源</th><th>总分</th><th>录取概率</th><th>薄弱维度</th></tr></thead>
        <tbody>
          ${records.map((r) => `
            <tr>
              <td class="small">${esc(r.created_at)}</td>
              <td>${esc(r.position)}</td>
              <td><span class="badge ${r.source === '题库' ? 'bank' : 'ai'}">${esc(r.source)}</span></td>
              <td><b>${r.total_score}</b>/20</td>
              <td>${r.hire_probability}%</td>
              <td class="small">${esc(r.weak_dimension || '—')}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    `;
    drawGrowth(growthR.points);
  } catch (e) {
    tableEl.innerHTML = `<p class="muted small">加载失败：${esc(e.message)}</p>`;
  }
}

function drawGrowth(points) {
  if (!points || points.length < 1) return;
  const canvas = $('#growth-chart');
  canvas.classList.remove('hidden');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 800;
  const h = 240;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const pad = { l: 40, r: 20, t: 20, b: 30 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const max = 20, min = 0;

  ctx.clearRect(0, 0, w, h);
  // 网格与刻度
  ctx.strokeStyle = '#e5e7eb';
  ctx.fillStyle = '#6b7280';
  ctx.font = '11px sans-serif';
  for (let v = 0; v <= max; v += 4) {
    const y = pad.t + innerH - (v - min) / (max - min) * innerH;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    ctx.fillText(String(v), 8, y + 4);
  }
  // 折线
  const xs = points.map((_, i) => pad.l + (points.length === 1 ? innerW / 2 : innerW * i / (points.length - 1)));
  const ys = points.map((p) => pad.t + innerH - (p.total_score - min) / (max - min) * innerH);

  ctx.strokeStyle = '#4f46e5';
  ctx.lineWidth = 2;
  ctx.beginPath();
  xs.forEach((x, i) => i === 0 ? ctx.moveTo(x, ys[i]) : ctx.lineTo(x, ys[i]));
  ctx.stroke();
  ctx.fillStyle = '#4f46e5';
  xs.forEach((x, i) => {
    ctx.beginPath(); ctx.arc(x, ys[i], 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillText(String(points[i].total_score), x - 6, ys[i] - 8);
  });
}

// ===== 我的 / 订阅视图 =====
function renderAccount() {
  const premium = state.sub && state.sub.status === 'premium';
  return `
    <div class="card">
      <h2 style="margin-top:0;">👤 我的账户</h2>
      <p>邮箱：<b>${esc(state.email)}</b></p>
      <p>当前状态：${premium ? '<span class="badge premium">订阅用户</span>' : '<span class="badge">免费用户（每日 3 次模拟）</span>'}</p>
      <div class="mt">
        ${premium
          ? '<p class="muted small">已解锁：完整题库、AI 深度解析、无限次模拟</p>'
          : `<button class="btn" id="btn-pay">升级订阅（Vibe Pay）</button>
             <button class="btn ghost" id="btn-test-activate">测试：一键开通订阅</button>
             <p class="muted small mt">真实支付尚未接入，可先点「测试开关」演示订阅功能</p>`}
      </div>
      <p id="account-msg" class="muted small mt"></p>
    </div>
  `;
}

function bindAccount() {
  const payBtn = $('#btn-pay');
  if (payBtn) {
    payBtn.onclick = async () => {
      try {
        const r = await api('/api/pay/create-order', 'POST');
        $('#account-msg').textContent = `已生成占位订单 ${r.order_id}，金额 ${r.amount} 元。${r.note}`;
      } catch (e) { $('#account-msg').textContent = e.message; }
    };
  }
  const testBtn = $('#btn-test-activate');
  if (testBtn) {
    testBtn.onclick = async () => {
      try {
        await api('/api/pay/test-activate', 'POST');
        await loadSub();
        render();
      } catch (e) { $('#account-msg').textContent = e.message; }
    };
  }
}

// ===== 订阅状态加载 =====
async function loadSub() {
  if (!state.token) { state.sub = null; return; }
  try { state.sub = await api('/api/pay/status'); }
  catch (e) { state.sub = null; }
}

async function loadSubThenRender() {
  await loadSub();
  render();
}

// ===== 启动 =====
(async () => {
  if (state.token) await loadSub();
  render();
})();
