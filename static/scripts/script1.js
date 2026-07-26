// HTML escape helper
function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}

// Scroll to Top visibility toggle
document.querySelector('.main').addEventListener('scroll', function () {
  const btn = document.getElementById('scrollTopBtn');
  if (this.scrollTop > 300) {
    btn.style.display = 'flex';
  } else {
    btn.style.display = 'none';
  }
});

/* ══════════════════════════════════════════════
       GLOBAL CHART INSTANCES & HELPERS
    ══════════════════════════════════════════════ */
let sipChartInstance = null;
let stockChartInstance = null;
let scoreChartInstance = null;
let portfolioChartInstance = null;

function initPortfolioChart() {
  const canvasEl = document.getElementById('portfolioChart');
  if (!canvasEl) return;
  const ctx = canvasEl.getContext('2d');
  portfolioChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Equity', 'ELSS', 'Debt', 'Insurance'],
      datasets: [
        {
          data: [40, 27, 18, 15],
          backgroundColor: ['#d4a843', '#14c8bf', '#5a6a82', '#2ecc8a'],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      cutout: '70%',
    },
  });
}

window.addEventListener('DOMContentLoaded', () => {
  initPortfolioChart();
});

/* ── NAVIGATION ──────────────────────────────── */
function toggleMobileMenu() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.menu-overlay');
  if (sidebar && overlay) {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('active');
  }
}

function showPage(name, e) {
  document
    .querySelectorAll('.page')
    .forEach((p) => p.classList.remove('active'));
  document
    .querySelectorAll('.nav-item')
    .forEach((n) => n.classList.remove('active'));

  const targetPage = document.getElementById(name);
  if (targetPage) targetPage.classList.add('active');

  document
    .querySelector(`.nav-item[data-page="${name}"]`)
    ?.classList.add('active');

  // Automatically close drawer menu on mobile
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.menu-overlay');
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
  }
}

// Nav-item click listeners — script is at bottom of body, DOM is fully ready
document.querySelectorAll('.nav-item').forEach((el) => {
  el.addEventListener('click', function (e) {
    showPage(this.dataset.page, e);
  });
});

// Mobile overlay dismiss
const overlay = document.querySelector('.menu-overlay');
if (overlay) {
  overlay.addEventListener('click', () => {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) sidebar.classList.remove('open');
    overlay.classList.remove('active');
  });
}

/* ══════════════════════════════════════════════
       HELPERS
    ══════════════════════════════════════════════ */
function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  btn.innerHTML = loading
    ? '<span class="spinner"></span>'
    : btn.dataset.label || btn.innerHTML;
  if (!btn.dataset.label && !loading) return;
  if (!btn.dataset.label) btn.dataset.label = btn.innerHTML;
  if (!loading) btn.innerHTML = btn.dataset.label;
}

function showResult(id, html) {
  const el = document.getElementById(id);
  el.innerHTML = html;
  el.classList.add('visible');
}

async function apiFetch(url, body, isForm = false) {
  const opts = { method: 'POST' };
  if (isForm) {
    opts.body = body;
  } else {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  return res.json();
}

function fmtNum(n) {
  return new Intl.NumberFormat('en-IN').format(Math.round(n));
}

/* ══════════════════════════════════════════════
       DASHBOARD CHAT
    ══════════════════════════════════════════════ */
function appendMsg(boxId, role, text) {
  const box = document.getElementById(boxId);
  const dashWelcome = document.getElementById('chatWelcome');
  const chatWelcome = document.getElementById('chatPageWelcome');
  if (dashWelcome && !dashWelcome.classList.contains('hidden')) {
    dashWelcome.classList.add('hidden');
  }
  if (chatWelcome && !chatWelcome.classList.contains('hidden')) {
    chatWelcome.classList.add('hidden');
  }
  const d = document.createElement('div');
  d.className = `msg ${role}`;
  d.innerHTML = `
        <div class="sender" style="display: flex; justify-content: space-between; align-items: center;">
            <span>${role === 'user' ? 'You' : 'AI Advisor'}</span>
            ${role === 'bot' ? '<button class="btn-ghost copy-btn" style="padding: 4px 10px; font-size: 11px; border-radius: 6px; cursor: pointer; height: 26px; border-width: 1px; font-family: inherit; display: inline-flex; align-items: center; gap: 4px;">📋 Copy</button>' : ''}
        </div>
        ${role === 'user' ? esc(text) : text}
      `;
  if (role === 'bot') {
    const btn = d.querySelector('.copy-btn');
    if (btn) {
      btn.onclick = () => {
        navigator.clipboard.writeText(text).then(() => {
          const original = btn.innerHTML;
          btn.innerHTML = '✅ Copied!';
          setTimeout(() => (btn.innerHTML = original), 2000);
        });
      };
    }
  }
  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

async function dashSend() {
  const inp = document.getElementById('dashMsg');
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';
  appendMsg('dashChat', 'user', msg);
  setLoading('dashBtn', true);
  try {
    const data = await apiFetch('/chat', { message: msg });
    appendMsg('dashChat', 'bot', data.reply || data.error || 'No response');
  } catch (e) {
    appendMsg('dashChat', 'bot', '⚠ Could not reach server. Is Flask running?');
  }
  setLoading('dashBtn', false);
}

function dashQuick(text) {
  document.getElementById('dashMsg').value = text;
  dashSend();
}

/* ══════════════════════════════════════════════
        FULL CHAT PAGE
     ══════════════════════════════════════════════ */
// Stores conversation history as {role, content} pairs for context
const chatHistory = [];

async function chatSend() {
  const inp = document.getElementById('chatInput');
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';
  appendMsg('chatMessages', 'user', msg);
  setLoading('chatBtn', true);
  try {
    const data = await apiFetch('/chat', {
      message: msg,
      history: chatHistory,
    });
    const reply = data.reply || data.error;
    // Save both turns to history so context is passed on next message
    chatHistory.push({ role: 'user', content: msg });
    chatHistory.push({ role: 'assistant', content: reply });
    appendMsg('chatMessages', 'bot', reply);
  } catch (e) {
    appendMsg('chatMessages', 'bot', '⚠ Could not reach server.');
  }
  setLoading('chatBtn', false);
}

function chatQuick(text) {
  document.getElementById('chatInput').value = text;
  chatSend();
}

function clearChat() {
  chatHistory.length = 0;
  const box = document.getElementById('chatMessages');
  box.innerHTML = '';
  const welcome = document.createElement('div');
  welcome.id = 'chatPageWelcome';
  welcome.className = 'chat-welcome';
  welcome.innerHTML = `
                          <div class="chat-welcome-icon">🎯</div>
                          <h3>Financial Guidance at Your Fingertips</h3>
                          <p>Ask questions about investments, tax planning, portfolio strategy, SIPs, risk assessment, or any financial topic.</p>
                          <div class="chat-features">
                            <div class="chat-feature-item" onclick="chatQuick('How should I diversify my portfolio?')">📊 Portfolio</div>
                            <div class="chat-feature-item" onclick="chatQuick('Best tax saving strategies for 2024-25')">💸 Tax Strategy</div>
                            <div class="chat-feature-item" onclick="chatQuick('Should I invest in mutual funds or stocks?')">📈 Investments</div>
                            <div class="chat-feature-item" onclick="chatQuick('How much emergency fund do I need?')">🛡️ Emergency Fund</div>
                          </div>`;
  box.appendChild(welcome);
}

/* ══════════════════════════════════════════════
       MONEY SCORE → POST /money-score
    ══════════════════════════════════════════════ */
async function calcScore() {
  const income = document.getElementById('s_income').value;
  const expenses = document.getElementById('s_expenses').value;
  const savings = document.getElementById('s_savings').value;
  const invest = document.getElementById('s_invest').value;
  const debt = document.getElementById('s_debt').value;
  const emergency = document.getElementById('s_emergency').value;

  if (!income || !expenses || !savings || !invest || !debt || !emergency) {
    showResult('scoreResult', '⚠ Please fill in all fields.');
    return;
  }

  setLoading('scoreBtn', true);
  try {
    const data = await apiFetch('/money-score', {
      income: parseFloat(income),
      expenses: parseFloat(expenses),
      savings: parseFloat(savings),
      investments: parseFloat(invest),
      debt: parseFloat(debt),
      emergency: parseFloat(emergency),
    });

    if (data.error) {
      showResult('scoreResult', `⚠ ${esc(data.error)}`);
    } else {
      const color =
        data.score >= 80 ? '#2ecc8a' : data.score >= 60 ? '#d4a843' : '#e05252';
      const circumference = 2 * Math.PI * 54;
      const offset = circumference - (data.score / 100) * circumference;
      showResult(
        'scoreResult',
        `
            <div style="text-align:center;margin-bottom:10px">
              <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">Your Money Score</div>
              <div class="score-container">
                <svg class="score-circle-svg">
                  <circle class="score-circle-bg" cx="65" cy="65" r="54" />
                  <circle class="score-circle-bar" cx="65" cy="65" r="54" 
                          stroke="${color}" 
                          stroke-dasharray="${circumference}" 
                          stroke-dashoffset="${offset}" />
                </svg>
                <div class="score-text-overlay">
                  <div style="font-family:'Outfit',sans-serif;font-size:42px;font-weight:800;color:${color}">${data.score}</div>
                  <div style="font-size:11px;font-weight:600;color:var(--text);margin-top:-2px">${esc(data.status)}</div>
                </div>
              </div>
            </div>
          `,
      );

      // Compute sub-scores locally for visual rendering
      const savingsRateVal = parseFloat(savings) / parseFloat(income);
      const savingsScore =
        savingsRateVal >= 0.3 ? 30 : savingsRateVal >= 0.2 ? 20 : 10;

      const investRateVal = parseFloat(invest) / parseFloat(income);
      const investScore =
        investRateVal >= 0.2 ? 25 : investRateVal >= 0.1 ? 15 : 5;

      const debtRatioVal = parseFloat(debt) / parseFloat(income);
      const debtScore = debtRatioVal <= 0.2 ? 25 : debtRatioVal <= 0.4 ? 15 : 5;

      const monthsCoverVal = parseFloat(emergency) / parseFloat(expenses);
      const emergencyScore =
        monthsCoverVal >= 6 ? 20 : monthsCoverVal >= 3 ? 10 : 5;

      // Draw Horizontal Bar Chart
      if (scoreChartInstance) scoreChartInstance.destroy();
      const scoreCtx = document.getElementById('scoreChart').getContext('2d');
      scoreChartInstance = new Chart(scoreCtx, {
        type: 'bar',
        data: {
          labels: [
            'Savings Rate',
            'Investment Rate',
            'Debt Ratio',
            'Emergency Fund',
          ],
          datasets: [
            {
              label: 'Your Score',
              data: [savingsScore, investScore, debtScore, emergencyScore],
              backgroundColor: ['#d4a843', '#14c8bf', '#5a6a82', '#2ecc8a'],
              borderRadius: 6,
              barThickness: 16,
            },
          ],
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
          },
          scales: {
            x: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#5a6a82' },
              max: 30,
            },
            y: {
              grid: { display: false },
              ticks: { color: '#eef0f5' },
            },
          },
        },
      });
    }
  } catch (e) {
    showResult('scoreResult', '⚠ Could not reach server.');
  }
  setLoading('scoreBtn', false);
}

/* ══════════════════════════════════════════════
       SIP → POST /sip
    ══════════════════════════════════════════════ */
async function calcSIP() {
  const monthly = document.getElementById('sip_monthly').value;
  const rate = document.getElementById('sip_rate').value;
  const years = document.getElementById('sip_years').value;

  if (!monthly || !rate || !years) {
    showResult('sipResult', '⚠ Please fill all fields.');
    return;
  }

  setLoading('sipBtn', true);
  try {
    const data = await apiFetch('/sip', {
      monthly: parseFloat(monthly),
      rate: parseFloat(rate),
      years: parseInt(years),
    });

    if (data.error) {
      showResult('sipResult', `⚠ ${esc(data.error)}`);
    } else {
      const fv = data.future_value;
      showResult(
        'sipResult',
        `
            <div style="font-size:11px;color:var(--muted);margin-bottom:6px;text-transform:uppercase;letter-spacing:0.06em">Estimated Future Value</div>
            <div class="result-big">₹${fmtNum(fv)}</div>
            <div style="font-size:12px;color:var(--muted);margin-top:6px">
              Invested: ₹${fmtNum(monthly * years * 12)} &nbsp;·&nbsp; 
              Gains: ₹${fmtNum(fv - monthly * years * 12)}
            </div>
          `,
      );

      // Compute compounding points
      const monthlyFloat = parseFloat(monthly);
      const rateFloat = parseFloat(rate);
      const yearsInt = parseInt(years);

      const labels = [];
      const investedData = [];
      const totalData = [];

      const r = rateFloat / 100 / 12;
      for (let y = 1; y <= yearsInt; y++) {
        const n = y * 12;
        const fv_point =
          monthlyFloat * ((Math.pow(1 + r, n) - 1) / r) * (1 + r);
        const invested_point = monthlyFloat * n;
        labels.push(`Year ${y}`);
        investedData.push(Math.round(invested_point));
        totalData.push(Math.round(fv_point));
      }

      // Draw compounding line chart
      if (sipChartInstance) sipChartInstance.destroy();
      const sipCtx = document.getElementById('sipChart').getContext('2d');
      sipChartInstance = new Chart(sipCtx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Est. Wealth Value',
              data: totalData,
              borderColor: '#d4a843',
              backgroundColor: 'rgba(212, 168, 67, 0.1)',
              fill: true,
              tension: 0.3,
            },
            {
              label: 'Amount Invested',
              data: investedData,
              borderColor: '#5a6a82',
              backgroundColor: 'transparent',
              borderDash: [5, 5],
              tension: 0.1,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: '#eef0f5', font: { family: 'Instrument Sans' } },
            },
          },
          scales: {
            x: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#5a6a82' },
            },
            y: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: {
                color: '#5a6a82',
                callback: function (value) {
                  return '₹' + fmtNum(value);
                },
              },
            },
          },
        },
      });
    }
  } catch (e) {
    showResult('sipResult', '⚠ Could not reach server.');
  }
  setLoading('sipBtn', false);
}

/* ══════════════════════════════════════════════
       STOCK → POST /portfolio
    ══════════════════════════════════════════════ */
async function checkStock() {
  const sym = document.getElementById('stockSym').value.trim();
  if (!sym) {
    showResult('stockResult', '⚠ Enter a stock symbol.');
    return;
  }

  setLoading('stockBtn', true);
  try {
    const data = await apiFetch('/portfolio', { stock: sym });

    if (data.error) {
      showResult('stockResult', `⚠ ${esc(data.error)}`);
    } else {
      // Display Stock details table
      const metrics = data.metrics || {};
      const pe =
        metrics.pe_ratio !== 'N/A' && metrics.pe_ratio !== null
          ? parseFloat(metrics.pe_ratio).toFixed(1)
          : 'N/A';
      let cap = metrics.market_cap;
      if (cap && cap !== 'N/A') {
        if (cap >= 1e12) cap = (cap / 1e12).toFixed(2) + 'T';
        else if (cap >= 1e9) cap = (cap / 1e9).toFixed(2) + 'B';
        else if (cap >= 1e7) cap = (cap / 1e7).toFixed(2) + 'Cr';
        else if (cap >= 1e5) cap = (cap / 1e5).toFixed(2) + 'L';
      } else {
        cap = 'N/A';
      }

      let html = `
            <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em">${esc(data.symbol)} — Last Price</div>
            <div class="result-big">₹${fmtNum(data.price)}</div>
            <div style="margin-top: 14px; display: flex; flex-direction: column; gap: 6px; font-size: 12px; border-top: 1px solid var(--border); padding-top: 10px;">
              <div style="display:flex; justify-content:space-between"><span>52W High</span><strong>₹${metrics.high_52w !== 'N/A' && metrics.high_52w !== null ? fmtNum(metrics.high_52w) : 'N/A'}</strong></div>
              <div style="display:flex; justify-content:space-between"><span>52W Low</span><strong>₹${metrics.low_52w !== 'N/A' && metrics.low_52w !== null ? fmtNum(metrics.low_52w) : 'N/A'}</strong></div>
              <div style="display:flex; justify-content:space-between"><span>Market Cap</span><strong>${cap}</strong></div>
              <div style="display:flex; justify-content:space-between"><span>P/E Ratio</span><strong>${pe}</strong></div>
            </div>
          `;
      showResult('stockResult', html);

      // Draw Stock history chart
      const dates = data.history.map((h) => h.date);
      const prices = data.history.map((h) => h.close);

      if (stockChartInstance) stockChartInstance.destroy();
      const stockCtx = document.getElementById('stockChart').getContext('2d');
      stockChartInstance = new Chart(stockCtx, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [
            {
              label: data.symbol,
              data: prices,
              borderColor: '#14c8bf',
              backgroundColor: 'rgba(20, 200, 191, 0.05)',
              fill: true,
              tension: 0.1,
              pointRadius: 1,
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: '#5a6a82', maxTicksLimit: 6 },
            },
            y: {
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: {
                color: '#5a6a82',
                callback: function (value) {
                  return '₹' + fmtNum(value);
                },
              },
            },
          },
        },
      });
    }
  } catch (e) {
    showResult('stockResult', '⚠ Could not reach server.');
  }
  setLoading('stockBtn', false);
}

/* ══════════════════════════════════════════════
       TAX → POST /tax
    ══════════════════════════════════════════════ */
async function calcTax() {
  const income = document.getElementById('taxIncome').value;
  if (!income) {
    showResult('taxResult', '⚠ Enter your annual income.');
    return;
  }

  setLoading('taxBtn', true);
  try {
    const data = await apiFetch('/tax', { income: parseFloat(income) });

    if (data.error) {
      showResult('taxResult', `⚠ ${esc(data.error)}`);
    } else {
      const taxRes = data.tax;
      document.getElementById('taxComparisonCard').style.display = 'block';

      let tableHtml = `
            <table style="width:100%; border-collapse:collapse; font-size:13px; text-align:left; color:var(--text);">
              <thead>
                <tr style="border-bottom:1px solid var(--border); color:var(--muted); font-size:11px; text-transform:uppercase;">
                  <th style="padding:10px 0;">Particulars</th>
                  <th style="padding:10px 0;">Old Regime</th>
                  <th style="padding:10px 0; color:var(--gold);">New Regime</th>
                </tr>
              </thead>
              <tbody>
                <tr style="border-bottom:1px solid var(--border);">
                  <td style="padding:10px 0;">Gross Income</td>
                  <td style="padding:10px 0;">₹${fmtNum(taxRes.gross_income)}</td>
                  <td style="padding:10px 0; color:var(--gold);">₹${fmtNum(taxRes.gross_income)}</td>
                </tr>
                <tr style="border-bottom:1px solid var(--border);">
                  <td style="padding:10px 0;">Std Deduction</td>
                  <td style="padding:10px 0;">-₹${fmtNum(taxRes.old_regime.standard_deduction)}</td>
                  <td style="padding:10px 0; color:var(--gold);">-₹${fmtNum(taxRes.new_regime.standard_deduction)}</td>
                </tr>
                <tr style="border-bottom:1px solid var(--border);">
                  <td style="padding:10px 0;">Taxable Income</td>
                  <td style="padding:10px 0;">₹${fmtNum(taxRes.old_regime.taxable_income)}</td>
                  <td style="padding:10px 0; color:var(--gold);">₹${fmtNum(taxRes.new_regime.taxable_income)}</td>
                </tr>
                <tr style="border-bottom:1px solid var(--border);">
                  <td style="padding:10px 0;">Base Tax</td>
                  <td style="padding:10px 0;">₹${fmtNum(taxRes.old_regime.base_tax)}</td>
                  <td style="padding:10px 0; color:var(--gold);">₹${fmtNum(taxRes.new_regime.base_tax)}</td>
                </tr>
                <tr style="border-bottom:1px solid var(--border);">
                  <td style="padding:10px 0;">Cess (4%)</td>
                  <td style="padding:10px 0;">₹${fmtNum(taxRes.old_regime.cess)}</td>
                  <td style="padding:10px 0; color:var(--gold);">₹${fmtNum(taxRes.new_regime.cess)}</td>
                </tr>
                <tr style="font-weight:700; font-size:15px; border-bottom:2px solid var(--border);">
                  <td style="padding:12px 0;">Total Tax</td>
                  <td style="padding:12px 0;">₹${fmtNum(taxRes.old_regime.total_tax)}</td>
                  <td style="padding:12px 0; color:#2ecc8a;">₹${fmtNum(taxRes.new_regime.total_tax)}</td>
                </tr>
              </tbody>
            </table>
            
            <div style="margin-top:16px; padding:12px 14px; background:rgba(46,204,138,0.08); border:1px solid rgba(46,204,138,0.2); border-radius:8px; color:#2ecc8a; font-size:13px; line-height:1.5;">
              <strong>Recommendation:</strong> Select the <strong>${esc(taxRes.recommended)}</strong>.<br/>
              You will save <strong>₹${fmtNum(taxRes.savings)}</strong> annually with this regime.
            </div>
          `;
      document.getElementById('taxComparisonResult').innerHTML = tableHtml;

      showResult(
        'taxResult',
        `
            <div style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em">Tax Payable (${esc(taxRes.recommended)})</div>
            <div class="result-big" style="color:#2ecc8a;">₹${fmtNum(taxRes.recommended === 'New Regime' ? taxRes.new_regime.total_tax : taxRes.old_regime.total_tax)}</div>
            <div style="font-size:12px;color:var(--muted);margin-top:4px">Annual Savings: ₹${fmtNum(taxRes.savings)}</div>
          `,
      );
    }
  } catch (e) {
    showResult('taxResult', '⚠ Could not reach server.');
  }
  setLoading('taxBtn', false);
}

/* ══════════════════════════════════════════════
       PDF → POST /upload  (multipart)
    ══════════════════════════════════════════════ */
async function uploadPDF() {
  const file = document.getElementById('pdfFile').files[0];
  if (!file) {
    showResult('pdfResult', '⚠ Please select a PDF file.');
    return;
  }

  const form = new FormData();
  form.append('file', file);

  setLoading('pdfBtn', true);
  try {
    const data = await apiFetch('/upload', form, true);
    if (data.error) {
      showResult('pdfResult', `⚠ ${esc(data.error)}`);
    } else {
      // Parse structured document data
      if (data.data && typeof data.data === 'object') {
        const docData = data.data;
        const docType = docData.document_type || 'Unknown Document';
        const emp = docData.employer_organization || 'N/A';
        const gross = docData.gross_income
          ? '₹' + fmtNum(docData.gross_income)
          : 'N/A';
        const tds = docData.tax_deducted_tds
          ? '₹' + fmtNum(docData.tax_deducted_tds)
          : 'N/A';
        const score = docData.confidence_score
          ? (docData.confidence_score * 100).toFixed(0) + '%'
          : 'N/A';
        const summary = docData.summary_findings || 'No summary available.';

        let deductionsHtml = '';
        if (
          docData.allowances_deductions &&
          Object.keys(docData.allowances_deductions).length > 0
        ) {
          deductionsHtml = Object.entries(docData.allowances_deductions)
            .map(
              ([k, v]) =>
                `<div style="display:flex; justify-content:space-between"><span>${k}:</span> <strong>₹${fmtNum(v)}</strong></div>`,
            )
            .join('');
        } else {
          deductionsHtml = 'None detected';
        }

        let html = `
              <div style="font-size:13px; font-weight:700; color:var(--gold); border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-bottom: 10px;">
                Parsed: ${docType} (Confidence: ${score})
              </div>
              <div style="display:flex; flex-direction:column; gap:8px; font-size:12px;">
                <div style="display:flex; justify-content:space-between;"><span>Issuer / Employer:</span> <strong>${emp}</strong></div>
                <div style="display:flex; justify-content:space-between;"><span>Gross Income:</span> <strong>${gross}</strong></div>
                <div style="display:flex; justify-content:space-between;"><span>TDS (Tax Deducted):</span> <strong>${tds}</strong></div>
                <div style="margin-top: 6px; border-top: 1px solid var(--border); padding-top: 6px;">
                  <span style="font-size:10px; color:var(--muted); text-transform:uppercase;">Deductions & Allowances:</span>
                  <div style="margin-top:4px; display:flex; flex-direction:column; gap:4px;">
                    ${deductionsHtml}
                  </div>
                </div>
                <div style="margin-top:6px; font-size:11px; color:var(--teal); font-style:italic; background:rgba(20,200,191,0.05); padding:8px; border-radius:6px; line-height:1.4;">
                  💡 ${summary}
                </div>
              </div>
            `;
        showResult('pdfResult', html);
      } else {
        const content = data.data || data.text || JSON.stringify(data);
        showResult(
          'pdfResult',
          `<pre style="white-space:pre-wrap;font-family:'JetBrains Mono',monospace;font-size:12px">${content}</pre>`,
        );
      }
    }
  } catch (e) {
    showResult('pdfResult', '⚠ Could not reach server.');
  }
  setLoading('pdfBtn', false);
}

/* ══════════════════════════════════════════════
       MULTI AGENT → POST /agent
    ══════════════════════════════════════════════ */
async function runAgent() {
  const query = document.getElementById('agentQuery').value.trim();
  if (!query) {
    showResult('agentResult', '⚠ Enter a query.');
    return;
  }

  setLoading('agentBtn', true);
  try {
    const data = await apiFetch('/agent', { query });
    if (data.error) {
      showResult('agentResult', `⚠ ${esc(data.error)}`);
    } else {
      const resp = data.response || JSON.stringify(data);
      showResult(
        'agentResult',
        `<div style="white-space:pre-wrap;font-size:13px;line-height:1.7">${resp}</div>`,
      );
    }
  } catch (e) {
    showResult('agentResult', '⚠ Could not reach server.');
  }
  setLoading('agentBtn', false);
}

/* ══════════════════════════════════════════════
       SIP SLIDER (dashboard)
    ══════════════════════════════════════════════ */
function updateSIP() {
  const m = +document.getElementById('sipAmt').value;
  const y = +document.getElementById('sipYrs').value;
  const r = +document.getElementById('sipRt').value / 100 / 12;
  const n = y * 12;
  const fv = m * ((Math.pow(1 + r, n) - 1) / r) * (1 + r);

  document.getElementById('sipAmtLbl').textContent = fmtNum(m);
  document.getElementById('sipYrLbl').textContent = y;
  document.getElementById('sipRtLbl').textContent =
    document.getElementById('sipRt').value;
  document.getElementById('sipOut').textContent =
    fv >= 1e7
      ? '₹' + (fv / 1e7).toFixed(2) + 'Cr'
      : '₹' + (fv / 1e5).toFixed(1) + 'L';
}

updateSIP();

/* ══════════════════════════════════════════════
              EXPENSE TRACKER
    ══════════════════════════════════════════════ */
/* ══════════════════════════════════════════════
              EXPENSE TRACKER
    ══════════════════════════════════════════════ */

const _expenseForm = document.getElementById('expenseForm');
if (_expenseForm) {
  _expenseForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    const expense = {
      category: document.getElementById('category').value,
      amount: parseFloat(document.getElementById('amount').value),
      date: document.getElementById('date').value,
    };

    try {
      const response = await fetch('/add_expense', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(expense),
      });

      const data = await response.json();

      if (data.status === 'success') {
        document.getElementById('expenseForm').reset();
        loadExpenses();
      }
    } catch (error) {
      console.error(error);
      alert('Error adding expense');
    }
  });
}

async function loadExpenses() {
  try {
    const calcRes = await fetch('/calculate');
    const calcData = await calcRes.json();

    document.getElementById('insights').innerHTML = `
              <div class="ai-loader-wrapper">
                  <div class="ai-loader"></div>
              </div>
              `;

    let insightData = {
      insights: 'No insights available',
    };

    try {
      const insightRes = await fetch('/insights');
      insightData = await insightRes.json();
    } catch (err) {
      console.log('Insights failed', err);
    }

    /* ---------- TOTAL CARD ---------- */

    document.getElementById('totalCard').innerHTML = `
            <h2>Total Spend</h2>
            <p>₹${esc(calcData.Total || 0)}</p>
        `;

    /* ---------- AVERAGE CARD ---------- */

    document.getElementById('avgCard').innerHTML = `
            <h2>Average Expense</h2>
            <p>₹${(calcData.Average || 0).toFixed(2)}</p>
        `;

    /* ---------- EXPENSE HISTORY TABLE ---------- */

    const tableBody = document.getElementById('expenseTableBody');

    tableBody.innerHTML = '';

    (calcData.expenses || []).forEach((expense) => {
      const formattedDate = new Date(expense.date).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });

      tableBody.innerHTML += `
                <tr>
                    <td style="padding:10px;border-bottom:1px solid #222;">
                        ${formattedDate}
                    </td>

                    <td style="padding:10px;border-bottom:1px solid #222;">
                        ${esc(expense.category)}
                    </td>

                    <td style="padding:10px;border-bottom:1px solid #222;">
                        ₹${esc(expense.amount)}
                    </td>
                </tr>
            `;
    });

    /* ---------- PIE CHART ---------- */

    // Get category data from Flask response
    const categories = calcData['By Category'] || {};

    // Check if canvas exists
    const chartCanvas = document.getElementById('expenseChart');

    if (chartCanvas) {
      const ctx = chartCanvas.getContext('2d');

      // Destroy old chart before creating new one
      if (window.expenseChartInstance) {
        window.expenseChartInstance.destroy();
      }

      // If no expense data available
      if (Object.keys(categories).length === 0) {
        ctx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);
      } else {
        // Ensure Chart.js is loaded
        if (typeof Chart === 'undefined') {
          console.error('Chart.js is not loaded');
          return;
        }

        window.expenseChartInstance = new Chart(ctx, {
          type: 'pie',
          data: {
            labels: Object.keys(categories),
            datasets: [
              {
                data: Object.values(categories),
                backgroundColor: [
                  '#ff6384',
                  '#36a2eb',
                  '#ffce56',
                  '#4caf50',
                  '#9c27b0',
                  '#ff9800',
                  '#00bcd4',
                ],
                borderWidth: 1,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  color: 'white',
                  font: {
                    size: 12,
                  },
                },
              },
              tooltip: {
                callbacks: {
                  label: function (context) {
                    return context.label + ': ₹' + context.raw;
                  },
                },
              },
            },
          },
        });
      }
    }

    /* ---------- AI INSIGHTS ---------- */

    document.getElementById('insights').innerHTML =
      insightData.insights || 'No insights available';
  } catch (error) {
    console.error('Expense Loading Error:', error);
  }
}

loadExpenses();

/* ══════════════════════════════════════════════
       NET WORTH TRACKER — Add / Delete helpers
    ══════════════════════════════════════════════ */
async function addNWItem(type) {
  const nameEl = document.getElementById(
    type === 'asset' ? 'assetName' : 'liabName',
  );
  const amtEl = document.getElementById(
    type === 'asset' ? 'assetAmt' : 'liabAmt',
  );
  const name = nameEl.value.trim();
  const amount = parseFloat(amtEl.value);
  if (!name || !amount || amount <= 0) {
    alert('Enter a valid name and amount.');
    return;
  }
  try {
    await apiFetch('/net-worth', { action: 'add', type, name, amount });
    nameEl.value = '';
    amtEl.value = '';
    loadNetWorth();
  } catch (e) {
    alert('Could not save. Is Flask running?');
  }
}

async function deleteNWItem(type, index) {
  try {
    await apiFetch('/net-worth', { action: 'delete', type, index });
    loadNetWorth();
  } catch (e) {
    alert('Could not delete. Is Flask running?');
  }
}

/* ══════════════════════════════════════════════
       NET WORTH TRACKER
    ══════════════════════════════════════════════ */
async function loadNetWorth() {
  try {
    const data = await apiFetch('/net-worth', {});

    document.getElementById('nwAssets').textContent =
      '₹' + fmtNum(data.total_assets);
    document.getElementById('nwLiabilities').textContent =
      '₹' + fmtNum(data.total_liabilities);
    document.getElementById('nwTotal').textContent =
      '₹' + fmtNum(data.net_worth);

    const assetList = document.getElementById('assetList');
    assetList.innerHTML = '';
    if (data.assets.length === 0) {
      assetList.innerHTML =
        '<tr><td colspan="3" style="text-align: center; padding: 20px; color: var(--muted); font-style: italic;">No assets added yet</td></tr>';
    } else {
      data.assets.forEach((item, idx) => {
        assetList.innerHTML += `
              <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 8px;">${esc(item.name)}</td>
                <td style="padding: 8px; text-align: right;">₹${fmtNum(item.amount)}</td>
                <td style="padding: 8px; text-align: center;"><button class="btn btn-ghost" style="padding: 4px 8px; font-size: 10px;" onclick="deleteNWItem('asset', ${idx})">✖</button></td>
              </tr>
            `;
      });
    }

    const liabList = document.getElementById('liabList');
    liabList.innerHTML = '';
    if (data.liabilities.length === 0) {
      liabList.innerHTML =
        '<tr><td colspan="3" style="text-align: center; padding: 20px; color: var(--muted); font-style: italic;">No liabilities added yet</td></tr>';
    } else {
      data.liabilities.forEach((item, idx) => {
        liabList.innerHTML += `
                <tr style="border-bottom: 1px solid var(--border);">
                  <td style="padding: 8px;">${esc(item.name)}</td>
                  <td style="padding: 8px; text-align: right;">₹${fmtNum(item.amount)}</td>
                  <td style="padding: 8px; text-align: center;"><button class="btn btn-ghost" style="padding: 4px 8px; font-size: 10px;" onclick="deleteNWItem('liability', ${idx})">✖</button></td>
                </tr>
              `;
      });
    }
  } catch (e) {
    console.error('Net worth error:', e);
  }
}

// ── Override showPage to auto-load net worth ──
const _origShowPage = showPage;
showPage = function (name, e) {
  _origShowPage(name, e);
  if (name === 'networth') loadNetWorth();
};

/* ══════════════════════════════════════════════
       GOAL TRACKER (global scope)
    ══════════════════════════════════════════════ */
let goals = [];

function addGoal() {
  const name = document.getElementById('goalName').value.trim();

  const target = parseFloat(document.getElementById('goalTarget').value);

  if (!name || !target) {
    alert('Enter valid goal details');
    return;
  }

  goals.push({
    name: name,
    target: target,
    saved: 0,
  });

  document.getElementById('goalName').value = '';
  document.getElementById('goalTarget').value = '';

  renderGoals();
}

function addSavings(index) {
  const amount = parseFloat(document.getElementById(`save-${index}`).value);

  if (!amount || amount <= 0) {
    alert('Enter valid amount');
    return;
  }

  goals[index].saved += amount;

  renderGoals();
}

function deleteGoal(index) {
  goals.splice(index, 1);

  renderGoals();
}

function renderGoals() {
  const container = document.getElementById('goalContainer');

  container.innerHTML = '';

  goals.forEach((goal, index) => {
    const percent = Math.min((goal.saved / goal.target) * 100, 100);

    const remaining = Math.max(goal.target - goal.saved, 0);

    container.innerHTML += `

<div class="goal-card">

<div class="goal-top">

<div>

<h3>${esc(goal.name)}</h3>

<div class="goal-amount">
₹${goal.saved.toLocaleString()}
/
₹${goal.target.toLocaleString()}
</div>

<div style="margin-top:6px;color:#94a3b8;">
Remaining:
₹${remaining.toLocaleString()}
</div>

</div>

<div style="
display:flex;
align-items:center;
gap:10px;
">

<div class="goal-percent">
${percent.toFixed(0)}%
</div>

<button
class="delete-btn"
onclick="deleteGoal(${index})"
>
🗑
</button>

</div>

</div>

<div class="goal-progress">

<div
class="goal-fill"
style="width:${percent}%"
></div>

</div>

<div class="goal-save-row">

<input
id="save-${index}"
type="number"
placeholder="Add savings amount (₹)"
>

<button
class="save-btn"
onclick="addSavings(${index})"
>
Add Savings
</button>

</div>

</div>
`;
  });
}

/* ══════════════════════════════════════════════
       CHART THEME HELPER — updates Chart.js defaults for light/dark
    ══════════════════════════════════════════════ */
function applyChartTheme(isLight) {
  const textColor = isLight ? '#1a2235' : '#eef0f5';
  const mutedColor = isLight ? '#6b7a92' : '#5a6a82';
  const gridColor = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.05)';

  Chart.defaults.color = mutedColor;
  Chart.defaults.borderColor = gridColor;

  [
    sipChartInstance,
    stockChartInstance,
    scoreChartInstance,
    portfolioChartInstance,
  ].forEach((chart) => {
    if (!chart) return;
    try {
      if (chart.options.scales) {
        Object.values(chart.options.scales).forEach((scale) => {
          if (scale.ticks) scale.ticks.color = mutedColor;
          if (scale.grid) scale.grid.color = gridColor;
        });
      }
      if (chart.options.plugins?.legend?.labels) {
        chart.options.plugins.legend.labels.color = textColor;
      }
      chart.update();
    } catch (e) {
      /* chart may not have scales */
    }
  });
}

function toggleTheme() {
  document.body.classList.toggle('light-theme');
  const isLight = document.body.classList.contains('light-theme');
  const btn = document.getElementById('themeToggle');
  if (isLight) {
    localStorage.setItem('theme', 'light');
    btn.innerHTML = '🌙 Dark Mode';
  } else {
    localStorage.setItem('theme', 'dark');
    btn.innerHTML = '☀️ Light Mode';
  }
  applyChartTheme(isLight);
}

// Restore saved theme on load (script is at bottom, DOM is ready)
(function () {
  const savedTheme = localStorage.getItem('theme');
  const btn = document.getElementById('themeToggle');
  if (savedTheme === 'light') {
    document.body.classList.add('light-theme');
    if (btn) btn.innerHTML = '🌙 Dark Mode';
    window.addEventListener('load', () => applyChartTheme(true));
  }
})();
