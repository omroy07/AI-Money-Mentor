// Navigation
document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', function() {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById(this.dataset.page).classList.add('active');
    this.classList.add('active');
    if (this.dataset.page === 'portfolio') { refreshPortfolio(); loadAlerts(); }
    if (this.dataset.page === 'expense') loadExpenses();
    if (this.dataset.page === 'networth') loadNetWorth();
    if (this.dataset.page === 'budget') { updateBudgetStats(); renderBudgetCharts(); }
    });
});

function applyChartTheme(isLight) {
    const mutedColor = isLight ? '#6b7a92' : '#5a6a82';
    const textColor  = isLight ? '#1a2235' : '#eef0f5';
    const gridColor  = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.04)';

    Chart.defaults.color = mutedColor;
    Chart.defaults.borderColor = gridColor;

    [portfolioChart, budgetPieChart, budgetBarChart].forEach(chart => {
        if (!chart) return;
        try {
            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(scale => {
                    if (scale.ticks) scale.ticks.color = mutedColor;
                    if (scale.grid)  scale.grid.color  = gridColor;
                });
            }
            if (chart.options.plugins?.legend?.labels) {
                chart.options.plugins.legend.labels.color = textColor;
            }
            chart.update();
        } catch(e) {}
    });
}

function toggleTheme() {
    document.body.classList.toggle('light-theme');
    const isLight = document.body.classList.contains('light-theme');
    const btn = document.getElementById('themeToggle');
    btn.innerHTML = isLight ? '🌙 Dark Mode' : '☀️ Light Mode';
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    applyChartTheme(isLight);
}

// Restore saved theme on page load
(function () {
    if (localStorage.getItem('theme') === 'light') {
        document.body.classList.add('light-theme');
        const btn = document.getElementById('themeToggle');
        if (btn) btn.innerHTML = '🌙 Dark Mode';
        window.addEventListener('load', () => applyChartTheme(true));
    }
})();

function fmtNum(n) { return new Intl.NumberFormat('en-IN').format(Math.round(n)); }

// ========== PORTFOLIO TRACKER ==========
let portfolioChart = null;

async function refreshPortfolio() {
    const res = await fetch('/portfolio/list');
    const data = await res.json();
    if (!data.success || data.holdings.length === 0) {
    // Load mock data for demo
    loadMockPortfolioData();
    return;
    }
    updatePortfolioUI(data.holdings, data.summary);
}

function loadMockPortfolioData() {
    const mockHoldings = [
    { symbol: "RELIANCE", name: "Reliance Industries", quantity: 10, buy_price: 2500, current_price: 2850 },
    { symbol: "TCS", name: "Tata Consultancy", quantity: 5, buy_price: 3500, current_price: 3950 },
    { symbol: "HDFCBANK", name: "HDFC Bank", quantity: 20, buy_price: 1600, current_price: 1680 },
    { symbol: "INFY", name: "Infosys", quantity: 8, buy_price: 1400, current_price: 1520 },
    { symbol: "ICICIBANK", name: "ICICI Bank", quantity: 15, buy_price: 1100, current_price: 1250 }
    ];
    
    const holdings = mockHoldings.map(h => {
    const invested = h.quantity * h.buy_price;
    const current = h.quantity * h.current_price;
    const pnl = current - invested;
    const pnlPercent = (pnl / invested * 100).toFixed(1);
    return { ...h, invested, current, pnl, pnlPercent };
    });
    
    const totalInvested = holdings.reduce((s, h) => s + h.invested, 0);
    const totalCurrent = holdings.reduce((s, h) => s + h.current, 0);
    const totalPnl = totalCurrent - totalInvested;
    const totalPercent = (totalPnl / totalInvested * 100).toFixed(1);
    
    updatePortfolioUI(holdings, { total_invested: totalInvested, total_current: totalCurrent, total_pnl: totalPnl, total_pnl_percent: totalPercent });
}

function updatePortfolioUI(holdings, summary) {
    // Update summary
    document.getElementById('portTotalInvested').innerHTML = `₹${fmtNum(summary.total_invested)}`;
    document.getElementById('portCurrentValue').innerHTML = `₹${fmtNum(summary.total_current)}`;
    document.getElementById('portTotalPnL').innerHTML = `<span class="positive">+₹${fmtNum(summary.total_pnl)}</span>`;
    document.getElementById('portReturns').innerHTML = `<span class="positive">+${summary.total_pnl_percent}%</span>`;
    
    // Update table
    const tbody = document.getElementById('portfolioTableBody');
    tbody.innerHTML = '';
    holdings.forEach(h => {
    tbody.innerHTML += `<tr><td><strong>${h.symbol}</strong><br><small>${h.name}</small></td><td style="text-align:right">${h.quantity}</td><td style="text-align:right">₹${fmtNum(h.buy_price)}</td><td style="text-align:right">₹${fmtNum(h.current_price)}</td><td style="text-align:right">₹${fmtNum(h.invested)}</td><td style="text-align:right">₹${fmtNum(h.current)}</td><td style="text-align:right" class="positive">+₹${fmtNum(h.pnl)} (${h.pnlPercent}%)</td><td><button class="btn btn-ghost" style="padding:4px 8px;" onclick="deleteFromPortfolio(${h.id})">✖</button></td></tr>`;
    });
    
    // Create chart
    const canvas = document.getElementById('portfolioAllocationChart');
    if (canvas) {
    if (portfolioChart) portfolioChart.destroy();
    const ctx = canvas.getContext('2d');
    portfolioChart = new Chart(ctx, {
        type: 'pie',
        data: { labels: holdings.map(h => h.symbol), datasets: [{ data: holdings.map(h => h.current), backgroundColor: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'] }] },
        options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#eef0f5' } } } }
    });
    }
    
    // Top performers
    const sorted = [...holdings].sort((a, b) => parseFloat(b.pnlPercent) - parseFloat(a.pnlPercent));
    document.getElementById('topPerformers').innerHTML = sorted.map(p => `
    <div class="performer-card"><div><strong>${p.symbol}</strong><br><small>${p.name}</small></div><div class="positive">+${p.pnlPercent}%<br><small>+₹${fmtNum(p.pnl)}</small></div></div>
    `).join('');
}

async function addToPortfolio() {
    const symbol = document.getElementById('stockSymbol').value.toUpperCase();
    const quantity = parseFloat(document.getElementById('stockQuantity').value);
    const buy_price = parseFloat(document.getElementById('stockBuyPrice').value);
    if (!symbol || !quantity || !buy_price) { alert('Fill all fields'); return; }
    const res = await fetch('/portfolio/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol, quantity, buy_price, buy_date: new Date().toISOString().split('T')[0] }) });
    const data = await res.json();
    if (data.success) { alert(data.message); refreshPortfolio(); }
    else alert('Error: ' + data.error);
}

async function addPriceAlert() {
    const symbol = document.getElementById('alertSymbol').value.toUpperCase();
    const target_price = parseFloat(document.getElementById('alertPrice').value);
    const condition = document.getElementById('alertCondition').value;
    if (!symbol || !target_price) { alert('Fill all fields'); return; }
    const res = await fetch('/portfolio/alert/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol, target_price, condition }) });
    const data = await res.json();
    if (data.success) { alert(data.message); loadAlerts(); }
}

async function loadAlerts() {
    const res = await fetch('/portfolio/alerts');
    const data = await res.json();
    const alertsDiv = document.getElementById('alertsList');
    if (data.success && data.alerts.length) {
    alertsDiv.innerHTML = data.alerts.map(a => `<div style="display:flex;justify-content:space-between;padding:10px;border-bottom:1px solid var(--border);"><span><strong>${a.symbol}</strong> ${a.condition} ₹${a.target_price}</span><span class="${a.is_triggered ? 'positive' : ''}">${a.is_triggered ? '✓ Triggered' : '● Active'}</span></div>`).join('');
    } else {
    alertsDiv.innerHTML = '<div style="text-align:center;padding:20px;color:var(--muted);">No alerts set</div>';
    }
}

async function checkAlerts() {
    const res = await fetch('/portfolio/check-alerts');
    const data = await res.json();
    if (data.success && data.triggered.length) alert(`🔔 ${data.triggered.map(t => `${t.symbol} reached ₹${t.current}`).join(', ')}`);
    else alert('No alerts triggered');
    loadAlerts();
    refreshPortfolio();
}

function exportCSV() {
    fetch('/portfolio/list').then(res => res.json()).then(data => {
    if (!data.success) return;
    let csv = "Symbol,Quantity,Buy Price,Current Price,Invested,Current Value,P&L\n";
    data.holdings.forEach(h => csv += `${h.symbol},${h.quantity},${h.buy_price},${h.current_price},${h.invested_value},${h.current_value},${h.pnl}\n`);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `portfolio_${new Date().toISOString().split('T')[0]}.csv`; a.click();
    URL.revokeObjectURL(url);
    });
}

// Chat functions
function appendMsg(boxId, role, text) {
    const box = document.getElementById(boxId);

    const d = document.createElement('div');
    d.className = `msg ${role}`;

    let content;

    if (role === 'bot') {
        content = DOMPurify.sanitize(
            marked.parse(text || '')
        );
    } else {
        content = text;
    }

    d.innerHTML = `
        <div class="sender">
            ${role === 'user' ? 'You' : 'AI Advisor'}
        </div>
        ${content}
    `;

    box.appendChild(d);
    box.scrollTop = box.scrollHeight;
}

async function dashSend() {
    const msg = document.getElementById('dashMsg').value;
    if (!msg) return;
    const chatDiv = document.getElementById('dashChat');
    appendMsg('dashChat', 'user', msg);
    document.getElementById('dashMsg').value = '';
    const res = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) });
    const data = await res.json();
    appendMsg('dashChat', 'bot', data.reply);
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

async function chatSend() {
    const msg = document.getElementById('chatInput').value;
    if (!msg) return;
    const chatDiv = document.getElementById('chatMessages');
    appendMsg('chatMessages', 'user', msg);
    document.getElementById('chatInput').value = '';
    const res = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) });
    const data = await res.json();
    appendMsg('chatMessages', 'bot', data.reply);
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

function clearChat() {
    document.getElementById('chatMessages').innerHTML = '<div class="msg bot">Hello! I\'m your AI financial advisor. How can I help?</div>';
}

// Other functions (simplified)
async function calcSIP() {
    const res = await fetch('/sip', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ monthly: parseFloat(document.getElementById('sip_monthly').value), rate: parseFloat(document.getElementById('sip_rate').value), years: parseInt(document.getElementById('sip_years').value) }) });
    const data = await res.json();
    document.getElementById('sipResult').innerHTML = `<div class="positive" style="font-size:24px;font-weight:800;">₹${fmtNum(data.future_value)}</div>`;
}

async function checkStock() {
    const res = await fetch('/portfolio', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stock: document.getElementById('stockSym').value }) });
    const data = await res.json();
    document.getElementById('stockResult').innerHTML = `<div><strong>${data.symbol}</strong> ₹${fmtNum(data.price)}</div><div>${data.analysis}</div>`;
}

async function calcTax() {
    const res = await fetch('/tax', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ income: parseFloat(document.getElementById('taxIncome').value) }) });
    const data = await res.json();
    document.getElementById('taxResult').innerHTML = `<div class="positive" style="font-size:24px;font-weight:800;">Tax: ₹${fmtNum(data.tax)}</div>`;
}

async function calcScore() {
    const res = await fetch('/money-score', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ income: parseFloat(document.getElementById('s_income').value), expenses: parseFloat(document.getElementById('s_expenses').value), savings: parseFloat(document.getElementById('s_savings').value), investments: parseFloat(document.getElementById('s_invest').value), debt: parseFloat(document.getElementById('s_debt').value), emergency: parseFloat(document.getElementById('s_emergency').value) }) });
    const data = await res.json();
    document.getElementById('scoreResult').innerHTML = `<div class="positive" style="font-size:24px;font-weight:800;">Score: ${data.score}</div><div>${data.status}</div>`;
}

async function uploadPDF() {
    const file = document.getElementById('pdfFile').files[0];
    if (!file) return;
    const formData = new FormData(); formData.append('file', file);
    const res = await fetch('/upload', { method: 'POST', body: formData });
    const data = await res.json();
    document.getElementById('pdfResult').innerHTML = `<pre style="white-space:pre-wrap;">${JSON.stringify(data, null, 2)}</pre>`;
}

async function loadExpenses() {
    const res = await fetch('/calculate');
    const data = await res.json();
    const total = data.expenses?.reduce((s, e) => s + e.amount, 0) || 0;
    document.getElementById('totalSpend').innerHTML = `₹${fmtNum(total)}`;
}

async function addExpenseWithAI() {
    const description = document.getElementById('ai_description').value;
    const amount = document.getElementById('ai_amount').value;
    if (!description || !amount) { alert('Fill fields'); return; }
    const res = await fetch('/add_expense_ai', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ description, amount: parseFloat(amount), date: new Date().toISOString().split('T')[0] }) });
    const data = await res.json();
    if (data.status === 'success') alert(`Added as ${data.ai_category}`);
    loadExpenses();
}

async function detectAnomalies() {
    const res = await fetch('/anomaly_detection');
    const data = await res.json();
    document.getElementById('anomaliesResult').innerHTML = data.anomalies?.length ? data.anomalies.map(a => `<div class="performer-card">⚠️ ${a.reason}</div>`).join('') : '<div>No anomalies</div>';
}

async function loadNetWorth() {
    const res = await fetch('/net-worth');
    const data = await res.json();
    document.getElementById('nwAssets').innerHTML = `₹${fmtNum(data.total_assets)}`;
    document.getElementById('nwLiabilities').innerHTML = `₹${fmtNum(data.total_liabilities)}`;
    document.getElementById('nwTotal').innerHTML = `₹${fmtNum(data.net_worth)}`;
    document.getElementById('assetList').innerHTML = data.assets.map(a => `<div style="padding:8px;border-bottom:1px solid var(--border);">${a.name}: ₹${fmtNum(a.amount)}</div>`).join('');
    document.getElementById('liabList').innerHTML = data.liabilities.map(l => `<div style="padding:8px;border-bottom:1px solid var(--border);">${l.name}: ₹${fmtNum(l.amount)}</div>`).join('');
}

async function addNWItem(type) {
    const name = document.getElementById(type === 'asset' ? 'assetName' : 'liabName').value;
    const amount = parseFloat(document.getElementById(type === 'asset' ? 'assetAmt' : 'liabAmt').value);
    await fetch(`/add-${type}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, amount }) });
    loadNetWorth();
}

// Auto-refresh portfolio every 30 seconds
setInterval(refreshPortfolio, 30000);
refreshPortfolio();

// ========== MONTHLY BUDGET PLANNER ==========
let budgetCategories = [];
let budgetPieChart = null;
let budgetBarChart = null;

// Set current month as default
document.addEventListener('DOMContentLoaded', () => {
    const monthInput = document.getElementById('budgetMonth');
    if (monthInput) monthInput.value = new Date().toISOString().slice(0, 7);
});

function quickAdd(name) {
    document.getElementById('bCatName').value = name;
    document.getElementById('bCatBudget').focus();
}

function addBudgetCategory() {
    const name = document.getElementById('bCatName').value.trim();
    const budgeted = parseFloat(document.getElementById('bCatBudget').value) || 0;
    const spent = parseFloat(document.getElementById('bCatSpent').value) || 0;

    if (!name || budgeted <= 0) { alert('Enter a category name and budgeted amount.'); return; }

    const existing = budgetCategories.findIndex(c => c.name.toLowerCase() === name.toLowerCase());
    if (existing >= 0) {
    budgetCategories[existing] = { name, budgeted, spent };
    } else {
    budgetCategories.push({ name, budgeted, spent });
    }

    document.getElementById('bCatName').value = '';
    document.getElementById('bCatBudget').value = '';
    document.getElementById('bCatSpent').value = '';
    renderBudgetTable();
    updateBudgetStats();
    renderBudgetCharts();
}

function removeBudgetCategory(index) {
    budgetCategories.splice(index, 1);
    renderBudgetTable();
    updateBudgetStats();
    renderBudgetCharts();
}

function renderBudgetTable() {
    const container = document.getElementById('budgetTable');
    if (!budgetCategories.length) {
    container.innerHTML = '<div style="text-align:center;padding:30px;color:var(--muted);">No categories yet — add one above.</div>';
    return;
    }

    const rows = budgetCategories.map((c, i) => {
    const pct = c.budgeted > 0 ? Math.round(c.spent / c.budgeted * 100) : 0;
    const overBudget = c.spent > c.budgeted;
    const barColor = overBudget ? 'var(--red)' : pct >= 80 ? 'var(--gold)' : 'var(--teal)';
    const statusClass = overBudget ? 'negative' : 'positive';
    const diff = c.budgeted - c.spent;
    return `
        <tr>
        <td style="text-align:left;font-weight:600;">${c.name}</td>
        <td style="text-align:right;">₹${fmtNum(c.budgeted)}</td>
        <td style="text-align:right;" class="${statusClass}">₹${fmtNum(c.spent)}</td>
        <td style="text-align:right;" class="${diff < 0 ? 'negative' : 'positive'}">${diff < 0 ? '-' : '+'}₹${fmtNum(Math.abs(diff))}</td>
        <td style="min-width:120px;padding:12px;">
            <div style="background:rgba(255,255,255,0.06);border-radius:99px;height:6px;overflow:hidden;">
            <div style="height:100%;width:${Math.min(pct,100)}%;background:${barColor};border-radius:99px;transition:width 0.3s;"></div>
            </div>
            <div style="font-size:10px;color:var(--muted);margin-top:3px;">${pct}% used</div>
        </td>
        <td><button class="btn btn-ghost" style="padding:4px 8px;" onclick="removeBudgetCategory(${i})">✖</button></td>
        </tr>`;
    }).join('');

    container.innerHTML = `
    <table class="holdings-table">
        <thead><tr>
        <th>Category</th>
        <th style="text-align:right">Budgeted</th>
        <th style="text-align:right">Spent</th>
        <th style="text-align:right">Difference</th>
        <th>Progress</th>
        <th></th>
        </tr></thead>
        <tbody>${rows}</tbody>
    </table>`;
}

function updateBudgetStats() {
    const income = parseFloat(document.getElementById('budgetIncome').value) || 0;
    const totalBudgeted = budgetCategories.reduce((s, c) => s + c.budgeted, 0);
    const totalSpent = budgetCategories.reduce((s, c) => s + c.spent, 0);
    const remaining = income - totalSpent;

    document.getElementById('bIncome').innerHTML = `₹${fmtNum(income)}`;
    document.getElementById('bBudgeted').innerHTML = `₹${fmtNum(totalBudgeted)}`;
    document.getElementById('bSpent').innerHTML = `₹${fmtNum(totalSpent)}`;
    document.getElementById('bRemaining').innerHTML = `<span class="${remaining < 0 ? 'negative' : 'positive'}">₹${fmtNum(remaining)}</span>`;
}

function renderBudgetCharts() {
    if (!budgetCategories.length) return;

    const labels = budgetCategories.map(c => c.name);
    const budgetedVals = budgetCategories.map(c => c.budgeted);
    const spentVals = budgetCategories.map(c => c.spent);
    const colors = ['#d4a843','#14c8bf','#2ecc8a','#e05252','#7c72e0','#f0cc6e','#4ecdc4','#96ceb4'];

    // Pie chart — budget allocation
    const pieCanvas = document.getElementById('budgetPieChart');
    if (pieCanvas) {
    if (budgetPieChart) budgetPieChart.destroy();
    budgetPieChart = new Chart(pieCanvas.getContext('2d'), {
        type: 'doughnut',
        data: { labels, datasets: [{ data: budgetedVals, backgroundColor: colors, borderWidth: 2, borderColor: 'rgba(0,0,0,0.3)' }] },
        options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#eef0f5', font: { size: 11 } } } } }
    });
    }

    // Bar chart — budgeted vs spent
    const barCanvas = document.getElementById('budgetBarChart');
    if (barCanvas) {
    if (budgetBarChart) budgetBarChart.destroy();
    budgetBarChart = new Chart(barCanvas.getContext('2d'), {
        type: 'bar',
        data: {
        labels,
        datasets: [
            { label: 'Budgeted', data: budgetedVals, backgroundColor: 'rgba(212,168,67,0.7)', borderRadius: 6 },
            { label: 'Spent', data: spentVals, backgroundColor: 'rgba(20,200,191,0.7)', borderRadius: 6 }
        ]
        },
        options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { labels: { color: '#eef0f5', font: { size: 11 } } } },
        scales: { x: { ticks: { color: '#5a6a82' }, grid: { color: 'rgba(255,255,255,0.04)' } }, y: { ticks: { color: '#5a6a82' }, grid: { color: 'rgba(255,255,255,0.04)' } } }
        }
    });
    }
}

async function analyzeBudget() {
    const income = parseFloat(document.getElementById('budgetIncome').value) || 0;
    if (!income) { alert('Enter your monthly income first.'); return; }
    if (!budgetCategories.length) { alert('Add at least one budget category first.'); return; }

    const btn = document.getElementById('analyzeBtn');
    const adviceDiv = document.getElementById('budgetAdvice');
    btn.disabled = true;
    btn.textContent = 'Analysing…';
    adviceDiv.innerHTML = '<div style="color:var(--muted);font-size:13px;">Asking AI advisor…</div>';

    try {
    const res = await fetch('/budget-planner/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ income, categories: budgetCategories })
    });
    const data = await res.json();

    if (data.success) {
        const s = data.summary;
        adviceDiv.innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;">
            <div style="background:rgba(20,200,191,0.08);border-radius:12px;padding:12px;text-align:center;">
            <div style="font-size:11px;color:var(--muted);">SAVINGS RATE</div>
            <div style="font-size:20px;font-weight:800;color:var(--teal);">${s.savings_rate}%</div>
            </div>
            <div style="background:rgba(212,168,67,0.08);border-radius:12px;padding:12px;text-align:center;">
            <div style="font-size:11px;color:var(--muted);">TOTAL SPENT</div>
            <div style="font-size:20px;font-weight:800;color:var(--gold);">₹${fmtNum(s.total_spent)}</div>
            </div>
            <div style="background:rgba(46,204,138,0.08);border-radius:12px;padding:12px;text-align:center;">
            <div style="font-size:11px;color:var(--muted);">REMAINING</div>
            <div style="font-size:20px;font-weight:800;" class="${s.remaining < 0 ? 'negative' : 'positive'}">₹${fmtNum(s.remaining)}</div>
            </div>
        </div>
        <div style="background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:14px;padding:16px;font-size:13px;line-height:1.7;white-space:pre-wrap;">${data.advice}</div>`;
    } else {
        adviceDiv.innerHTML = `<div class="negative" style="font-size:13px;">Error: ${data.error}</div>`;
    }
    } catch (e) {
    adviceDiv.innerHTML = `<div class="negative" style="font-size:13px;">Failed to get AI advice. Check your connection.</div>`;
    }

    btn.disabled = false;
    btn.textContent = 'Analyse My Budget';
}

function resetBudget() {
    budgetCategories = [];
    document.getElementById('budgetIncome').value = '';
    document.getElementById('budgetMonth').value = new Date().toISOString().slice(0, 7);
    document.getElementById('budgetAdvice').innerHTML = '';
    renderBudgetTable();
    updateBudgetStats();
    if (budgetPieChart) { budgetPieChart.destroy(); budgetPieChart = null; }
    if (budgetBarChart) { budgetBarChart.destroy(); budgetBarChart = null; }
}