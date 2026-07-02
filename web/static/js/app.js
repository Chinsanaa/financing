const state = {
  sessionId: null,
  categories: [],
  charts: {},
  alipayFile: null,
  wechatFile: null,
};

const COLORS = ['#7c6af7', '#4fc3f7', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c'];

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function setStep(n) {
  document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
  document.querySelectorAll('.step').forEach((s) => {
    const sn = Number(s.dataset.step);
    s.classList.toggle('active', sn === n);
    s.classList.toggle('done', sn < n);
  });
  const panels = ['', 'step-upload', 'step-categories', 'step-label', 'step-dashboard'];
  document.getElementById(panels[n]).classList.add('active');
}

function setupDropzone(dropId, inputId, nameId, key) {
  const drop = document.getElementById(dropId);
  const input = document.getElementById(inputId);
  const nameEl = document.getElementById(nameId);

  const pick = (file) => {
    if (!file) return;
    state[key] = file;
    nameEl.textContent = file.name;
    document.getElementById('btn-parse').disabled = !(state.alipayFile || state.wechatFile);
  };

  drop.addEventListener('click', () => input.click());
  input.addEventListener('change', () => pick(input.files[0]));
  drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('dragover'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    drop.classList.remove('dragover');
    pick(e.dataTransfer.files[0]);
  });
}

function renderCategories() {
  const ul = document.getElementById('category-list');
  ul.innerHTML = '';
  state.categories.forEach((cat, i) => {
    const li = document.createElement('li');
    const inp = document.createElement('input');
    inp.value = cat;
    inp.addEventListener('change', () => { state.categories[i] = inp.value.trim(); });
    const del = document.createElement('button');
    del.className = 'btn';
    del.textContent = 'Remove';
    del.addEventListener('click', () => {
      state.categories.splice(i, 1);
      renderCategories();
    });
    li.append(inp, del);
    ul.appendChild(li);
  });
}

function updateAccuracy(pct) {
  const display = document.getElementById('accuracy-display');
  const bar = document.getElementById('accuracy-bar');
  const val = pct == null ? 0 : Math.min(100, Math.round(pct * 100));
  display.textContent = pct == null ? 'Training…' : `${val}%`;
  bar.style.width = `${val}%`;
}

async function loadLabelQueue() {
  const data = await api(`/api/sessions/${state.sessionId}/label-queue`);
  const container = document.getElementById('merchant-cards');
  container.innerHTML = '';
  if (!data.merchants.length) {
    container.innerHTML = '<p class="hint">No unlabeled merchants left. Submit to retrain.</p>';
    return;
  }
  data.merchants.forEach((m) => {
    const card = document.createElement('div');
    card.className = 'merchant-card';
    card.dataset.merchant = m.merchant;
    const title = m.merchant_en || m.merchant;
    const showMerchantOriginal = m.merchant_en && m.merchant_en !== m.merchant;
    const descEn = m.sample_description_en || m.sample_description || '';
    const showDescOriginal = m.sample_description_en
      && m.sample_description
      && m.sample_description_en !== m.sample_description;
    const sel = document.createElement('select');
    sel.innerHTML = '<option value="">Choose category…</option>' +
      state.categories.map((c) => `<option value="${c}">${c}</option>`).join('');
    card.innerHTML = `
      <h3>${escapeHtml(title)}</h3>
      ${showMerchantOriginal ? `<div class="merchant-original">${escapeHtml(m.merchant)}</div>` : ''}
      <div class="merchant-meta">${m.count} txns · ¥${m.total_spend.toLocaleString()}</div>
      ${descEn ? `<div class="merchant-sample">${escapeHtml(descEn)}</div>` : ''}
      ${showDescOriginal ? `<div class="merchant-original">${escapeHtml(m.sample_description)}</div>` : ''}
    `;
    card.appendChild(sel);
    container.appendChild(card);
  });
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function destroyCharts() {
  Object.values(state.charts).forEach((c) => c.destroy());
  state.charts = {};
}

function makeChart(canvasId, type, labels, values, label) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  if (state.charts[canvasId]) state.charts[canvasId].destroy();
  state.charts[canvasId] = new Chart(ctx, {
    type,
    data: {
      labels,
      datasets: [{
        label,
        data: values,
        backgroundColor: COLORS,
        borderColor: type === 'line' ? COLORS[0] : undefined,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#c8cdd3' } } },
      scales: type === 'line' || type === 'bar' ? {
        x: { ticks: { color: '#8899a6' }, grid: { color: 'rgba(255,255,255,0.06)' } },
        y: { ticks: { color: '#8899a6' }, grid: { color: 'rgba(255,255,255,0.06)' } },
      } : {},
    },
  });
}

async function loadDashboardTab(tab) {
  const data = await api(`/api/sessions/${state.sessionId}/dashboard/${tab}`);
  const panel = document.getElementById(`tab-${tab}`);
  destroyCharts();

  if (tab === 'overview') {
    panel.innerHTML = `
      <div class="kpi-grid">
        <div class="kpi"><div class="kpi-label">Total spend</div><div class="kpi-value">¥${data.total_spend.toLocaleString()}</div></div>
        <div class="kpi"><div class="kpi-label">Transactions</div><div class="kpi-value">${data.transaction_count}</div></div>
        <div class="kpi"><div class="kpi-label">Avg txn</div><div class="kpi-value">¥${data.avg_transaction}</div></div>
        <div class="kpi"><div class="kpi-label">Period</div><div class="kpi-value" style="font-size:0.9rem">${data.date_range.start} → ${data.date_range.end}</div></div>
      </div>
      <div class="chart-row">
        <div class="chart-box"><canvas id="chart-cat-pie"></canvas></div>
        <div class="chart-box"><canvas id="chart-monthly"></canvas></div>
      </div>
      <div class="chart-box"><canvas id="chart-merchants"></canvas></div>
    `;
    makeChart('chart-cat-pie', 'doughnut', data.by_category.labels, data.by_category.values, 'Spend');
    makeChart('chart-monthly', 'line', data.monthly.labels, data.monthly.values, 'Monthly');
    makeChart('chart-merchants', 'bar', data.top_merchants.labels, data.top_merchants.values, 'Merchants');
  }

  if (tab === 'budget') {
    const rows = data.rows.map((r) => `
      <tr><td>${escapeHtml(r.category)}</td><td>¥${r.spent.toLocaleString()}</td>
      <td>¥${r.budget.toLocaleString()}</td><td style="color:${r.variance > 0 ? '#e74c3c' : '#2ecc71'}">¥${r.variance.toLocaleString()}</td></tr>
    `).join('');
    panel.innerHTML = `
      <p class="hint">Monthly income: ¥${Number(data.income).toLocaleString()}</p>
      <table class="data"><thead><tr><th>Category</th><th>Spent</th><th>Budget</th><th>Variance</th></tr></thead><tbody>${rows}</tbody></table>
    `;
  }

  if (tab === 'savings') {
    panel.innerHTML = `
      <div class="kpi-grid">
        <div class="kpi"><div class="kpi-label">YTD spend</div><div class="kpi-value">¥${data.ytd_spend.toLocaleString()}</div></div>
        <div class="kpi"><div class="kpi-label">YTD savings</div><div class="kpi-value">¥${data.ytd_savings.toLocaleString()}</div></div>
        <div class="kpi"><div class="kpi-label">Savings rate</div><div class="kpi-value">${(data.savings_rate * 100).toFixed(1)}%</div></div>
      </div>
      <div class="chart-box"><canvas id="chart-savings-monthly"></canvas></div>
      <h3>High-value outliers</h3>
      <table class="data"><thead><tr><th>Date</th><th>Merchant</th><th>Amount</th><th>Category</th></tr></thead>
      <tbody>${data.outliers.map((o) => `<tr><td>${o.date}</td><td>${escapeHtml(o.merchant)}</td><td>¥${o.amount}</td><td>${o.category}</td></tr>`).join('')}</tbody></table>
    `;
    makeChart('chart-savings-monthly', 'bar', data.monthly_spend.labels, data.monthly_spend.values, 'Spend');
  }

  if (tab === 'action') {
    panel.innerHTML = `
      <div class="chart-box"><canvas id="chart-cuttable"></canvas></div>
      <h3>Top discretionary transactions</h3>
      <table class="data"><thead><tr><th>Merchant</th><th>Amount</th><th>Category</th></tr></thead>
      <tbody>${data.top_discretionary.map((t) => `<tr><td>${escapeHtml(t.merchant)}</td><td>¥${t.amount}</td><td>${t.category}</td></tr>`).join('')}</tbody></table>
    `;
    makeChart('chart-cuttable', 'bar', data.cuttable_merchants.labels, data.cuttable_merchants.values, 'Want spend');
  }

  if (tab === 'reports') {
    panel.innerHTML = `
      <table class="data"><thead><tr><th>Category</th><th>Count</th><th>Total</th><th>Avg</th></tr></thead>
      <tbody>${data.category_summary.map((r) => `<tr><td>${r.category}</td><td>${r.count}</td><td>¥${r.total}</td><td>¥${r.avg}</td></tr>`).join('')}</tbody></table>
    `;
  }
}

async function goDashboard() {
  setStep(4);
  document.getElementById('btn-export').href = `/api/sessions/${state.sessionId}/export`;
  await loadDashboardTab('overview');
}

document.addEventListener('DOMContentLoaded', async () => {
  setupDropzone('drop-alipay', 'input-alipay', 'name-alipay', 'alipayFile');
  setupDropzone('drop-wechat', 'input-wechat', 'name-wechat', 'wechatFile');

  const { session_id } = await api('/api/sessions', { method: 'POST' });
  state.sessionId = session_id;

  document.getElementById('btn-parse').addEventListener('click', async () => {
    const status = document.getElementById('upload-status');
    status.textContent = 'Parsing…';
    status.className = 'status';
    const fd = new FormData();
    if (state.alipayFile) fd.append('alipay', state.alipayFile);
    if (state.wechatFile) fd.append('wechat', state.wechatFile);
    fd.append('monthly_income', document.getElementById('monthly-income').value);
    try {
      const result = await api(`/api/sessions/${state.sessionId}/upload`, { method: 'POST', body: fd });
      status.textContent = `Loaded ${result.transaction_count} transactions (¥${result.total_spend.toLocaleString()}). ${result.rule_matches} matched by starter rules.`;
      status.className = 'status ok';
      const catData = await api(`/api/sessions/${state.sessionId}/categories`);
      state.categories = catData.categories;
      renderCategories();
      setStep(2);
    } catch (e) {
      status.textContent = e.message;
      status.className = 'status error';
    }
  });

  document.getElementById('btn-add-category').addEventListener('click', () => {
    const v = document.getElementById('new-category').value.trim();
    if (v && !state.categories.includes(v)) {
      state.categories.push(v);
      document.getElementById('new-category').value = '';
      renderCategories();
    }
  });

  document.getElementById('btn-save-categories').addEventListener('click', async () => {
    const inputs = document.querySelectorAll('#category-list input');
    state.categories = [...inputs].map((i) => i.value.trim()).filter(Boolean);
    await api(`/api/sessions/${state.sessionId}/categories`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ categories: state.categories }),
    });
    setStep(3);
    await loadLabelQueue();
    const st = await api(`/api/sessions/${state.sessionId}/status`);
    updateAccuracy(st.high_confidence_rate);
  });

  document.getElementById('btn-submit-labels').addEventListener('click', async () => {
    const status = document.getElementById('label-status');
    status.textContent = 'Training…';
    const labels = [];
    document.querySelectorAll('.merchant-card').forEach((card) => {
      const merchant = card.dataset.merchant;
      const category = card.querySelector('select').value;
      if (merchant && category) labels.push({ merchant, category });
    });
    if (!labels.length) {
      status.textContent = 'Pick at least one category.';
      status.className = 'status error';
      return;
    }
    try {
      const result = await api(`/api/sessions/${state.sessionId}/labels`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ labels }),
      });
      updateAccuracy(result.accuracy);
      status.textContent = result.train.message || `Iteration ${result.iteration}`;
      status.className = 'status ok';
      if (result.done) {
        status.textContent += ' — Target reached! Opening dashboard.';
        await goDashboard();
      } else {
        await loadLabelQueue();
      }
    } catch (e) {
      status.textContent = e.message;
      status.className = 'status error';
    }
  });

  document.querySelectorAll('#dash-tabs .tab').forEach((btn) => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('#dash-tabs .tab').forEach((t) => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
      await loadDashboardTab(btn.dataset.tab);
    });
  });
});
