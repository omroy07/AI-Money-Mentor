// Navigation and Global State
document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', function() {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.getElementById(this.dataset.page).classList.add('active');
        this.classList.add('active');
        
        // Loader router
        if (this.dataset.page === 'dashboard') { refreshDashboardStats(); }
        if (this.dataset.page === 'portfolio') { refreshPortfolio(); loadAlerts(); }
        if (this.dataset.page === 'expense') { loadExpenses(); }
        if (this.dataset.page === 'networth') { loadNetWorth(); }
        if (this.dataset.page === 'budget') { updateBudgetStats(); renderBudgetCharts(); }
        if (this.dataset.page === 'profile') { loadUserProfile(); }
    });
});

function toggleTheme() {
    document.body.classList.toggle('light-theme');
    const btn = document.getElementById('themeToggle');
    btn.innerHTML = document.body.classList.contains('light-theme') ? '🌙 Dark Mode' : '☀️ Light Mode';
    
    // Redraw any charts to update text colors in charts
    if (portfolioChart) refreshPortfolio();
    if (expenseChart) loadExpenses();
    if (netWorthChartObj) loadNetWorth();
    if (budgetPieChart || budgetBarChart) renderBudgetCharts();
}

function fmtNum(n) { 
    return new Intl.NumberFormat('en-IN').format(Math.round(n)); 
}

// Global Chart References
let portfolioChart = null;
let sipDoughnutChart = null;
let scoreGaugeChart = null;
let netWorthChartObj = null;
let expenseChart = null;

// ========== DYNAMIC DASHBOARD STATS ==========
async function refreshDashboardStats() {
    try {
        // Fetch Portfolio
        const portRes = await fetch('/portfolio/list');
        const portData = await portRes.json();
        let portfolioVal = 0;
        if (portData.success && portData.summary) {
            portfolioVal = portData.summary.total_current;
        } else {
            // Check fallback from script.js mock
            portfolioVal = 58250; 
        }

        // Fetch Net Worth
        const nwRes = await fetch('/net-worth');
        const nwData = await nwRes.json();
        const netWorthVal = nwData.net_worth || 0;
        const incomeVal = parseFloat(document.getElementById('budgetIncome')?.value) || 120000;

        // Fetch Tax Saved
        let taxSaved = 0;
        const taxResultEl = document.getElementById('taxResult');
        if (taxResultEl && taxResultEl.dataset.savings) {
            taxSaved = parseFloat(taxResultEl.dataset.savings);
        }

        // Update Dashboard UI Cards
        const statVals = document.querySelectorAll('#dashboard .stat-val');
        if (statVals.length >= 4) {
            statVals[0].innerHTML = `₹${fmtNum(portfolioVal)}`;
            statVals[1].innerHTML = `₹${fmtNum(incomeVal)}`;
            statVals[2].innerHTML = `₹${fmtNum(taxSaved)}`;
            statVals[3].innerHTML = `₹${fmtNum(netWorthVal)}`;
        }
    } catch (e) {
        console.error("Dashboard refresh error:", e);
    }
}

// ========== PORTFOLIO TRACKER ==========
async function refreshPortfolio() {
    const res = await fetch('/portfolio/list');
    const data = await res.json();
    if (!data.success || data.holdings.length === 0) {
        loadMockPortfolioData();
        return;
    }
    updatePortfolioUI(data.holdings, data.summary);
}

function loadMockPortfolioData() {
    const mockHoldings = [
        { id: 1, symbol: "RELIANCE", name: "Reliance Industries", quantity: 10, buy_price: 2500, current_price: 2850 },
        { id: 2, symbol: "TCS", name: "Tata Consultancy", quantity: 5, buy_price: 3500, current_price: 3950 },
        { id: 3, symbol: "HDFCBANK", name: "HDFC Bank", quantity: 20, buy_price: 1600, current_price: 1680 },
        { id: 4, symbol: "INFY", name: "Infosys", quantity: 8, buy_price: 1400, current_price: 1520 },
        { id: 5, symbol: "ICICIBANK", name: "ICICI Bank", quantity: 15, buy_price: 1100, current_price: 1250 }
    ];
    
    const holdings = mockHoldings.map(h => {
        const invested = h.quantity * h.buy_price;
        const current = h.quantity * h.current_price;
        const pnl = current - invested;
        const pnlPercent = (pnl / invested * 100).toFixed(1);
        return { ...h, invested_value: invested, current_value: current, pnl, pnlPercent };
    });
    
    const totalInvested = holdings.reduce((s, h) => s + h.invested_value, 0);
    const totalCurrent = holdings.reduce((s, h) => s + h.current_value, 0);
    const totalPnl = totalCurrent - totalInvested;
    const totalPercent = (totalPnl / totalInvested * 100).toFixed(1);
    
    updatePortfolioUI(holdings, { 
        total_invested: totalInvested, 
        total_current: totalCurrent, 
        total_pnl: totalPnl, 
        total_pnl_percent: totalPercent 
    });
}

function updatePortfolioUI(holdings, summary) {
    document.getElementById('portTotalInvested').innerHTML = `₹${fmtNum(summary.total_invested)}`;
    document.getElementById('portCurrentValue').innerHTML = `₹${fmtNum(summary.total_current)}`;
    
    const pnlClass = summary.total_pnl >= 0 ? 'positive' : 'negative';
    const pnlSign = summary.total_pnl >= 0 ? '+' : '';
    document.getElementById('portTotalPnL').innerHTML = `<span class="${pnlClass}">${pnlSign}₹${fmtNum(summary.total_pnl)}</span>`;
    document.getElementById('portReturns').innerHTML = `<span class="${pnlClass}">${pnlSign}${summary.total_pnl_percent}%</span>`;
    
    const tbody = document.getElementById('portfolioTableBody');
    tbody.innerHTML = '';
    holdings.forEach(h => {
        const itemPnLClass = h.pnl >= 0 ? 'positive' : 'negative';
        const itemPnLSign = h.pnl >= 0 ? '+' : '';
        
        tbody.innerHTML += `
            <tr>
                <td><strong>${h.symbol}</strong><br><small>${h.name}</small></td>
                <td style="text-align:right">${h.quantity}</td>
                <td style="text-align:right">₹${fmtNum(h.buy_price)}</td>
                <td style="text-align:right">₹${fmtNum(h.current_price)}</td>
                <td style="text-align:right">₹${fmtNum(h.invested_value)}</td>
                <td style="text-align:right">₹${fmtNum(h.current_value)}</td>
                <td style="text-align:right" class="${itemPnLClass}">${itemPnLSign}₹${fmtNum(h.pnl)} (${h.pnlPercent}%)</td>
                <td><button class="btn btn-ghost" style="padding:4px 8px;" onclick="deleteFromPortfolio(${h.id})">✖</button></td>
            </tr>`;
    });
    
    const canvas = document.getElementById('portfolioAllocationChart');
    if (canvas) {
        if (portfolioChart) portfolioChart.destroy();
        const ctx = canvas.getContext('2d');
        const isDark = !document.body.classList.contains('light-theme');
        portfolioChart = new Chart(ctx, {
            type: 'pie',
            data: { 
                labels: holdings.map(h => h.symbol), 
                datasets: [{ 
                    data: holdings.map(h => h.current_value), 
                    backgroundColor: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#d4a843', '#2ecc8a'],
                    borderWidth: 0
                }] 
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: true, 
                plugins: { 
                    legend: { 
                        position: 'bottom', 
                        labels: { color: isDark ? '#eef0f5' : '#1f2937' } 
                    } 
                } 
            }
        });
    }
    
    const sorted = [...holdings].sort((a, b) => parseFloat(b.pnlPercent) - parseFloat(a.pnlPercent));
    document.getElementById('topPerformers').innerHTML = sorted.slice(0, 3).map(p => {
        const itemPnLPercent = parseFloat(p.pnlPercent);
        const itemClass = itemPnLPercent >= 0 ? 'positive' : 'negative';
        const itemSign = itemPnLPercent >= 0 ? '+' : '';
        return `
            <div class="performer-card">
                <div><strong>${p.symbol}</strong><br><small>${p.name}</small></div>
                <div class="${itemClass}">${itemSign}${p.pnlPercent}%<br><small>${itemSign}₹${fmtNum(p.pnl)}</small></div>
            </div>`;
    }).join('');
    initTiltEffect();
}

async function addToPortfolio() {
    const symbol = document.getElementById('stockSymbol').value.toUpperCase().trim();
    const quantity = parseFloat(document.getElementById('stockQuantity').value);
    const buy_price = parseFloat(document.getElementById('stockBuyPrice').value);
    const buy_date = document.getElementById('stockBuyDate').value || new Date().toISOString().split('T')[0];
    
    if (!symbol || !quantity || !buy_price) { alert('Fill all fields'); return; }
    
    const res = await fetch('/portfolio/add', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ symbol, quantity, buy_price, buy_date }) 
    });
    const data = await res.json();
    if (data.success) { 
        alert(data.message); 
        refreshPortfolio(); 
        document.getElementById('stockSymbol').value = '';
        document.getElementById('stockQuantity').value = '';
        document.getElementById('stockBuyPrice').value = '';
    } else {
        alert('Error: ' + data.error);
    }
}

async function deleteFromPortfolio(id) {
    if (!confirm('Are you sure you want to remove this holding?')) return;
    const res = await fetch(`/portfolio/delete/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
        alert(data.message);
        refreshPortfolio();
    } else {
        alert('Error: ' + data.error);
    }
}

async function addPriceAlert() {
    const symbol = document.getElementById('alertSymbol').value.toUpperCase().trim();
    const target_price = parseFloat(document.getElementById('alertPrice').value);
    const condition = document.getElementById('alertCondition').value;
    if (!symbol || !target_price) { alert('Fill all fields'); return; }
    const res = await fetch('/portfolio/alert/add', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ symbol, target_price, condition }) 
    });
    const data = await res.json();
    if (data.success) { 
        alert(data.message); 
        loadAlerts(); 
        document.getElementById('alertSymbol').value = '';
        document.getElementById('alertPrice').value = '';
    } else {
        alert('Error: ' + data.error);
    }
}

async function loadAlerts() {
    const res = await fetch('/portfolio/alerts');
    const data = await res.json();
    const alertsDiv = document.getElementById('alertsList');
    if (data.success && data.alerts.length) {
        alertsDiv.innerHTML = data.alerts.map(a => `
            <div style="display:flex;justify-content:space-between;padding:10px;border-bottom:1px solid var(--border);">
                <span><strong>${a.symbol}</strong> ${a.condition} ₹${fmtNum(a.target_price)}</span>
                <span class="${a.is_triggered ? 'positive' : 'negative'}">${a.is_triggered ? '✓ Triggered' : '● Active'}</span>
            </div>`).join('');
    } else {
        alertsDiv.innerHTML = '<div style="text-align:center;padding:20px;color:var(--muted);">No alerts set</div>';
    }
}

async function checkAlerts() {
    const res = await fetch('/portfolio/check-alerts');
    const data = await res.json();
    if (data.success && data.triggered.length) {
        alert(`🔔 Price alerts triggered:\n` + data.triggered.map(t => `${t.symbol} is now ₹${fmtNum(t.current)} (Target was ₹${fmtNum(t.target)})`).join('\n'));
    } else {
        alert('No alerts triggered at current prices.');
    }
    loadAlerts();
    refreshPortfolio();
}

// ========== AI CHATBOT WITH MEMORY & SPECIALIZED AGENTS ==========
let chatHistory = [];
let dashHistory = [];

function appendMsg(boxId, role, text, agentName, specialization) {
    const box = document.getElementById(boxId);
    if (!box) return;

    // Remove typing indicator if it exists
    const typingNode = box.querySelector('.msg.typing');
    if (typingNode) { box.removeChild(typingNode); }

    const d = document.createElement('div');
    d.className = `msg ${role}`;

    let content;
    if (role === 'bot') {
        content = DOMPurify.sanitize(marked.parse(text || ''));
    } else {
        content = document.createTextNode(text).textContent;
    }

    let headerText = role === 'user' ? 'You' : 'AI Advisor';
    let badgeHtml = '';
    
    if (role === 'bot' && agentName) {
        headerText = agentName;
        if (specialization) {
            badgeHtml = `<span class="agent-specialization-badge" style="background: rgba(212,168,67,0.15); color: var(--gold); border: 1px solid rgba(212,168,67,0.3); font-size:10px; padding:2px 8px; border-radius:99px; margin-left: 8px;">${specialization}</span>`;
        }
    }

    d.innerHTML = `
        <div class="sender" style="font-weight: 700; font-size: 11px; margin-bottom: 6px; display: flex; align-items: center; justify-content: ${role === 'user' ? 'flex-end' : 'flex-start'};">
            ${role === 'user' ? headerText : `🤖 ${headerText} ${badgeHtml}`}
        </div>
        <div class="msg-body">${content}</div>
    `;

    box.appendChild(d);
    box.scrollTop = box.scrollHeight;
}

function showTypingIndicator(boxId) {
    const box = document.getElementById(boxId);
    if (!box) return;

    // Check if typing indicator already exists
    if (box.querySelector('.msg.typing')) return;

    const d = document.createElement('div');
    d.className = 'msg bot typing';
    d.innerHTML = `
        <div class="sender" style="font-weight: 700; font-size: 11px; margin-bottom: 6px;">🤖 AI Advisor</div>
        <div class="typing-indicator" style="display: flex; gap: 4px; padding: 4px 0;">
            <span style="width: 6px; height: 6px; background: var(--muted); border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both;"></span>
            <span style="width: 6px; height: 6px; background: var(--muted); border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both; animation-delay: 0.2s;"></span>
            <span style="width: 6px; height: 6px; background: var(--muted); border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both; animation-delay: 0.4s;"></span>
        </div>
    `;
    box.appendChild(d);
    box.scrollTop = box.scrollHeight;
}

async function dashSend() {
    const msgInput = document.getElementById('dashMsg');
    const msg = msgInput.value.trim();
    if (!msg) return;
    
    appendMsg('dashChat', 'user', msg);
    msgInput.value = '';
    showTypingIndicator('dashChat');
    
    try {
        const res = await fetch('/chat', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ message: msg, history: dashHistory }) 
        });
        const data = await res.json();
        
        appendMsg('dashChat', 'bot', data.reply, data.agent_used, data.specialization);
        
        // Push to conversation history
        dashHistory.push({ user: msg, assistant: data.reply });
        if (dashHistory.length > 5) dashHistory.shift();
    } catch (e) {
        appendMsg('dashChat', 'bot', 'Sorry, I failed to connect to the advisor service.');
    }
}

async function chatSend() {
    const msgInput = document.getElementById('chatInput');
    const msg = msgInput.value.trim();
    if (!msg) return;
    
    appendMsg('chatMessages', 'user', msg);
    msgInput.value = '';
    showTypingIndicator('chatMessages');
    
    try {
        const res = await fetch('/chat', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ message: msg, history: chatHistory }) 
        });
        const data = await res.json();
        
        appendMsg('chatMessages', 'bot', data.reply, data.agent_used, data.specialization);
        
        chatHistory.push({ user: msg, assistant: data.reply });
        if (chatHistory.length > 5) chatHistory.shift();
    } catch (e) {
        appendMsg('chatMessages', 'bot', 'Sorry, I failed to connect to the advisor service.');
    }
}

function clearChat() {
    document.getElementById('chatMessages').innerHTML = '<div class="msg bot"><div class="sender">🤖 AI Advisor</div>Hello! I\'m your AI financial advisor. How can I help?</div>';
    chatHistory = [];
}

// ========== SIP CALCULATOR WITH DOUGHNUT AND DETAILED GROWTH TABLE ==========
async function calcSIP() {
    const monthlyInput = document.getElementById('sip_monthly');
    const rateInput = document.getElementById('sip_rate');
    const yearsInput = document.getElementById('sip_years');
    
    const monthly = parseFloat(monthlyInput.value) || 10000;
    const rate = parseFloat(rateInput.value) || 12;
    const years = parseInt(yearsInput.value) || 10;
    
    const res = await fetch('/sip', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ monthly, rate, years }) 
    });
    const data = await res.json();
    
    const fv = data.future_value;
    const totalInvested = monthly * years * 12;
    const wealthGained = fv - totalInvested;
    
    // Display summary
    document.getElementById('sipResult').innerHTML = `
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:15px; margin-bottom:20px;">
            <div style="background: rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:12px; padding:15px; text-align:center;">
                <div style="font-size:11px; color:var(--muted);">TOTAL INVESTED</div>
                <div style="font-size:18px; font-weight:800; color:var(--text); margin-top:5px;">₹${fmtNum(totalInvested)}</div>
            </div>
            <div style="background: rgba(46,204,138,0.08); border:1px solid rgba(46,204,138,0.2); border-radius:12px; padding:15px; text-align:center;">
                <div style="font-size:11px; color:var(--muted);">EST. RETURNS</div>
                <div style="font-size:18px; font-weight:800; color:var(--green); margin-top:5px;">₹${fmtNum(wealthGained)}</div>
            </div>
            <div style="background: rgba(20,200,191,0.08); border:1px solid rgba(20,200,191,0.2); border-radius:12px; padding:15px; text-align:center;">
                <div style="font-size:11px; color:var(--muted);">TOTAL FUTURE VALUE</div>
                <div style="font-size:18px; font-weight:800; color:var(--teal); margin-top:5px;">₹${fmtNum(fv)}</div>
            </div>
        </div>
        
        <div style="margin-top:20px;">
            <div class="card-title" style="margin-bottom: 8px;">📅 Year-on-Year Growth Projection</div>
            <div style="overflow-x:auto;">
                <table class="holdings-table" style="font-size:12px;">
                    <thead>
                        <tr>
                            <th style="text-align:left;">Year</th>
                            <th>Total Invested</th>
                            <th>Future Value</th>
                            <th>Est. Returns</th>
                        </tr>
                    </thead>
                    <tbody id="sipGrowthTableBody">
                    </tbody>
                </table>
            </div>
        </div>`;
        
    // Generate Amortization Table
    const tableBody = document.getElementById('sipGrowthTableBody');
    const r_monthly = rate / 12 / 100;
    
    for (let y = 1; y <= years; y++) {
        const months = y * 12;
        let yearlyFV = 0;
        if (r_monthly === 0) {
            yearlyFV = monthly * months;
        } else {
            yearlyFV = monthly * (((1 + r_monthly) ** months - 1) / r_monthly) * (1 + r_monthly);
        }
        
        const yearlyInvested = monthly * months;
        const yearlyReturns = yearlyFV - yearlyInvested;
        
        tableBody.innerHTML += `
            <tr>
                <td style="text-align:left; font-weight:600;">Year ${y}</td>
                <td>₹${fmtNum(yearlyInvested)}</td>
                <td class="positive" style="font-weight:600;">₹${fmtNum(yearlyFV)}</td>
                <td class="positive">₹${fmtNum(yearlyReturns)}</td>
            </tr>`;
    }
    
    // Render chart
    const canvas = document.getElementById('sipChart');
    if (canvas) {
        if (sipDoughnutChart) sipDoughnutChart.destroy();
        const ctx = canvas.getContext('2d');
        const isDark = !document.body.classList.contains('light-theme');
        sipDoughnutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Invested Amount', 'Est. Returns'],
                datasets: [{
                    data: [totalInvested, wealthGained],
                    backgroundColor: ['#d4a843', '#2ecc8a'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: isDark ? '#eef0f5' : '#1f2937' }
                    }
                }
            }
        });
    }
}

// ========== STOCK SENTIMENT ==========
async function checkStock() {
    const symbolInput = document.getElementById('stockSym');
    const symbol = symbolInput.value.toUpperCase().trim();
    if (!symbol) { alert('Enter a stock ticker (e.g. AAPL, RELIANCE.NS)'); return; }
    
    const stockResultEl = document.getElementById('stockResult');
    stockResultEl.innerHTML = '<div style="color:var(--muted); font-size:13px;">Checking market prices...</div>';
    
    try {
        const res = await fetch('/portfolio', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ stock: symbol }) 
        });
        const data = await res.json();
        
        if (data.error) {
            stockResultEl.innerHTML = `<div class="negative" style="font-size:13px;">Error: ${data.error}</div>`;
            return;
        }
        
        const sentimentClass = data.sentiment === 'Bullish' ? 'positive' : data.sentiment === 'Bearish' ? 'negative' : 'var(--text)';
        const sentimentIcon = data.sentiment === 'Bullish' ? '📈' : data.sentiment === 'Bearish' ? '📉' : '➖';
        
        stockResultEl.innerHTML = `
            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius:14px; padding:15px; display:flex; flex-direction:column; gap:10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:18px; font-weight:800; color:var(--text);">${data.symbol}</span>
                    <span style="font-size:18px; font-weight:800; color:var(--gold);">₹${fmtNum(data.price)}</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border); padding-top:8px;">
                    <span style="font-size:12px; color:var(--muted);">Sentiment: <strong class="${sentimentClass}">${data.sentiment} ${sentimentIcon}</strong></span>
                    <span style="font-size:11px; color:var(--muted);">PE Ratio: ${data.metrics?.pe_ratio || 'N/A'}</span>
                </div>
                <div style="background: rgba(255,255,255,0.02); border-radius:8px; padding:10px; font-size:12px; line-height:1.6; border-left:3px solid var(--gold);">
                    <strong>AI Analysis:</strong> ${data.analysis}
                </div>
            </div>`;
        initTiltEffect();
    } catch (e) {
        stockResultEl.innerHTML = `<div class="negative" style="font-size:13px;">Error: Could not retrieve stock details.</div>`;
    }
}

// ========== TAX PLANNER WITH OLD VS NEW COMPARISON ==========
async function calcTax() {
    const incomeInput = document.getElementById('taxIncome');
    const income = parseFloat(incomeInput.value);
    
    if (!income || income <= 0) { alert('Enter a valid annual income.'); return; }
    
    const deductions_80c = parseFloat(document.getElementById('tax80C').value) || 0;
    const deductions_80d = parseFloat(document.getElementById('tax80D').value) || 0;
    const hra = parseFloat(document.getElementById('taxHRA').value) || 0;
    
    const res = await fetch('/tax', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ income, deductions_80c, deductions_80d, hra }) 
    });
    const data = await res.json();
    
    if (data.error) {
        document.getElementById('taxResult').innerHTML = `<div class="negative">Error: ${data.error}</div>`;
        return;
    }
    
    const t = data.tax;
    const recBadgeColor = t.recommended === 'New Regime' ? 'var(--teal)' : 'var(--gold)';
    
    // Store savings value for dashboard refresh
    document.getElementById('taxResult').dataset.savings = t.savings;
    
    document.getElementById('taxResult').innerHTML = `
        <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:14px; padding:16px; margin-bottom:15px; border-left:4px solid ${recBadgeColor}">
            <div style="font-size:12px; color:var(--muted); font-weight:600; text-transform:uppercase;">RECOMMENDED OPTION</div>
            <div style="font-size:20px; font-weight:800; color:${recBadgeColor}; margin-top:4px;">${t.recommended}</div>
            <div style="font-size:13px; color:var(--text); margin-top:4px;">
                Choosing this regime will save you <strong class="positive">₹${fmtNum(t.savings)}</strong> in tax payments.
            </div>
        </div>

        <table class="holdings-table" style="font-size:12px;">
            <thead>
                <tr>
                    <th style="text-align:left;">Component</th>
                    <th>Old Regime</th>
                    <th>New Regime</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="text-align:left;">Gross Income</td>
                    <td>₹${fmtNum(t.gross_income)}</td>
                    <td>₹${fmtNum(t.gross_income)}</td>
                </tr>
                <tr>
                    <td style="text-align:left;">Standard Deduction</td>
                    <td>-₹${fmtNum(t.old_regime.standard_deduction)}</td>
                    <td>-₹${fmtNum(t.new_regime.standard_deduction)}</td>
                </tr>
                <tr>
                    <td style="text-align:left;">Section 80C Applied</td>
                    <td>-₹${fmtNum(t.old_regime.deductions_80c_applied)}</td>
                    <td>-₹0 <small style="color:var(--muted);">(Unavailable)</small></td>
                </tr>
                <tr>
                    <td style="text-align:left;">Section 80D Applied</td>
                    <td>-₹${fmtNum(t.old_regime.deductions_80d_applied)}</td>
                    <td>-₹0 <small style="color:var(--muted);">(Unavailable)</small></td>
                </tr>
                <tr>
                    <td style="text-align:left;">HRA Exemption Applied</td>
                    <td>-₹${fmtNum(t.old_regime.hra_applied)}</td>
                    <td>-₹0 <small style="color:var(--muted);">(Unavailable)</small></td>
                </tr>
                <tr style="border-top:1px solid var(--border); font-weight:600;">
                    <td style="text-align:left;">Taxable Income</td>
                    <td>₹${fmtNum(t.old_regime.taxable_income)}</td>
                    <td>₹${fmtNum(t.new_regime.taxable_income)}</td>
                </tr>
                <tr>
                    <td style="text-align:left;">Base Tax Payable</td>
                    <td>₹${fmtNum(t.old_regime.base_tax)}</td>
                    <td>₹${fmtNum(t.new_regime.base_tax)}</td>
                </tr>
                <tr>
                    <td style="text-align:left;">Health & Education Cess (4%)</td>
                    <td>₹${fmtNum(t.old_regime.cess)}</td>
                    <td>₹${fmtNum(t.new_regime.cess)}</td>
                </tr>
                <tr style="border-top:2px solid var(--border); font-weight:800; font-size:13px;">
                    <td style="text-align:left; color:var(--text);">Total Tax Payable</td>
                    <td class="${t.recommended === 'Old Regime' ? 'positive' : 'var(--text)'}">₹${fmtNum(t.old_regime.total_tax)}</td>
                    <td class="${t.recommended === 'New Regime' ? 'positive' : 'var(--text)'}">₹${fmtNum(t.new_regime.total_tax)}</td>
                </tr>
            </tbody>
        </table>`;
    initTiltEffect();
        
    // Trigger dashboard stats refresh to sync values
    refreshDashboardStats();
}

// ========== MONEY SCORE WITH SEMI-CIRCLE GAUGE & AI ADVICE ==========
let lastScoreData = null;

async function calcScore() {
    const s_income = parseFloat(document.getElementById('s_income').value) || 0;
    const s_expenses = parseFloat(document.getElementById('s_expenses').value) || 0;
    const s_savings = parseFloat(document.getElementById('s_savings').value) || 0;
    const s_invest = parseFloat(document.getElementById('s_invest').value) || 0;
    const s_debt = parseFloat(document.getElementById('s_debt').value) || 0;
    const s_emergency = parseFloat(document.getElementById('s_emergency').value) || 0;
    
    if (s_income <= 0) { alert('Enter monthly income first'); return; }
    
    const res = await fetch('/money-score', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ 
            income: s_income, 
            expenses: s_expenses, 
            savings: s_savings, 
            investments: s_invest, 
            debt: s_debt, 
            emergency: s_emergency 
        }) 
    });
    const data = await res.json();
    
    if (data.error) {
        document.getElementById('scoreResult').innerHTML = `<div class="negative">Error: ${data.error}</div>`;
        return;
    }
    
    const details = data.details;
    lastScoreData = details;
    
    const getScoreColor = (sc) => {
        if (sc >= 80) return '#2ecc8a';
        if (sc >= 60) return '#d4a843';
        if (sc >= 40) return '#f0cc6e';
        return '#e05252';
    };
    
    const scoreColor = getScoreColor(details.score);
    
    document.getElementById('scoreResult').innerHTML = `
        <div style="display:flex; flex-direction:column; align-items:center; margin-bottom:20px;">
            <div style="font-size:38px; font-weight:800; color:${scoreColor};">${details.score}</div>
            <div style="font-size:16px; font-weight:700; color:var(--text); margin-top:4px;">${data.status}</div>
        </div>

        <div style="margin-top:20px;">
            <div class="card-title">📊 Scoring Breakdown</div>
            
            <div style="margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                    <span>Savings Rate (${details.savings_rate}%)</span>
                    <strong>${details.savings_score} / 30 pts</strong>
                </div>
                <div class="progress-track">
                    <div class="progress-fill gold" style="width:${(details.savings_score/30)*100}%;"></div>
                </div>
            </div>

            <div style="margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                    <span>Investment Rate (${details.investment_rate}%)</span>
                    <strong>${details.investment_score} / 25 pts</strong>
                </div>
                <div class="progress-track">
                    <div class="progress-fill green" style="width:${(details.investment_score/25)*100}%;"></div>
                </div>
            </div>

            <div style="margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                    <span>Debt Ratio (${details.debt_ratio}%)</span>
                    <strong>${details.debt_score} / 25 pts</strong>
                </div>
                <div class="progress-track">
                    <div class="progress-fill red" style="width:${(details.debt_score/25)*100}%;"></div>
                </div>
            </div>

            <div style="margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                    <span>Emergency Fund (${details.months_cover} months expenses)</span>
                    <strong>${details.emergency_score} / 20 pts</strong>
                </div>
                <div class="progress-track">
                    <div class="progress-fill teal" style="width:${(details.emergency_score/20)*100}%;"></div>
                </div>
            </div>
        </div>

        <button class="btn btn-ghost" onclick="getAIScoreAdvice()" style="margin-top:15px; width: 100%;">🤖 Get AI Score Advice</button>
        <div id="scoreAiAdvice" style="margin-top:15px; font-size:13px; line-height:1.6; display:none;"></div>`;
    initTiltEffect();
        
    // Render Gauge Speedometer
    const canvas = document.getElementById('scoreChart');
    if (canvas) {
        if (scoreGaugeChart) scoreGaugeChart.destroy();
        const ctx = canvas.getContext('2d');
        scoreGaugeChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [details.score, 100 - details.score],
                    backgroundColor: [scoreColor, 'rgba(255,255,255,0.04)'],
                    borderWidth: 0
                }]
            },
            options: {
                circumference: 180,
                rotation: 270,
                cutout: '82%',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    }
}

async function getAIScoreAdvice() {
    if (!lastScoreData) return;
    const adviceEl = document.getElementById('scoreAiAdvice');
    adviceEl.style.display = 'block';
    adviceEl.innerHTML = '<span style="color:var(--muted)">Asking AI advisor...</span>';
    
    try {
        const prompt = `Give me 3 extremely actionable, concise bullet points of financial advice based on my financial details:
        Savings Rate: ${lastScoreData.savings_rate}% (Score: ${lastScoreData.savings_score}/30)
        Investment Rate: ${lastScoreData.investment_rate}% (Score: ${lastScoreData.investment_score}/25)
        Debt Ratio: ${lastScoreData.debt_ratio}% (Score: ${lastScoreData.debt_score}/25)
        Emergency Fund Coverage: ${lastScoreData.months_cover} months of expenses (Score: ${lastScoreData.emergency_score}/20)
        My Total Money Score is ${lastScoreData.score}/100. Be numbers-specific.`;
        
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: prompt })
        });
        const data = await res.json();
        adviceEl.innerHTML = `<div style="background: rgba(255,255,255,0.02); border:1px dashed var(--border); padding:15px; border-radius:12px; margin-top:10px;">${DOMPurify.sanitize(marked.parse(data.reply))}</div>`;
    } catch (e) {
        adviceEl.innerHTML = '<span class="negative">Could not load AI advice.</span>';
    }
}

// ========== PDF PARSER WITH DETAILED DASHBOARD & AUTO-IMPORT ==========
let lastParsedPdfData = null;

async function uploadPDF() {
    const fileEl = document.getElementById('pdfFile');
    const file = fileEl.files[0];
    if (!file) { alert('Please select a PDF document first.'); return; }
    
    const parseBtn = document.getElementById('pdfParseBtn');
    parseBtn.disabled = true;
    parseBtn.textContent = 'Parsing...';
    
    const resultEl = document.getElementById('pdfResult');
    resultEl.innerHTML = '<div style="color:var(--muted); font-size:13px;">Extracting text & running AI analysis...</div>';
    
    const formData = new FormData(); 
    formData.append('file', file);
    
    try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();
        
        parseBtn.disabled = false;
        parseBtn.textContent = 'Parse PDF';
        
        if (data.error) {
            resultEl.innerHTML = `<div class="negative" style="font-size:13px;">Error: ${data.error}</div>`;
            return;
        }
        
        const p = data.data;
        lastParsedPdfData = p;
        
        let allowancesListHtml = '';
        if (p.allowances_deductions && Object.keys(p.allowances_deductions).length) {
            allowancesListHtml = Object.entries(p.allowances_deductions).map(([dedKey, dedVal]) => `
                <div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom: 1px dashed var(--border);">
                    <span>${dedKey}</span>
                    <strong style="color:var(--text);">₹${fmtNum(dedVal)}</strong>
                </div>`).join('');
        } else {
            allowancesListHtml = '<div style="color:var(--muted); font-size:12px; text-align:center; padding:10px;">No specific deductions detected</div>';
        }
        
        resultEl.innerHTML = `
            <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:16px; padding:18px; display:flex; flex-direction:column; gap:15px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="background:rgba(20,200,191,0.15); color:var(--teal); font-size:10px; padding:3px 8px; border-radius:99px; font-weight:700; text-transform:uppercase;">${p.document_type || 'Document'}</span>
                        <h4 style="margin-top:6px; font-size:15px; font-weight:700;">${p.employer_organization || 'Unknown Employer'}</h4>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:11px; color:var(--muted);">Confidence</span>
                        <div style="font-size:14px; font-weight:800; color:var(--green);">${Math.round((p.confidence_score || 0.8)*100)}%</div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
                    <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border); border-radius:10px; padding:12px;">
                        <span style="font-size:10px; color:var(--muted); text-transform:uppercase;">Gross Income</span>
                        <div style="font-size:18px; font-weight:800; color:var(--text); margin-top:4px;">₹${fmtNum(p.gross_income || 0)}</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border); border-radius:10px; padding:12px;">
                        <span style="font-size:10px; color:var(--muted); text-transform:uppercase;">Tax Deducted (TDS)</span>
                        <div style="font-size:18px; font-weight:800; color:var(--red); margin-top:4px;">₹${fmtNum(p.tax_deducted_tds || 0)}</div>
                    </div>
                </div>

                <div>
                    <span style="font-size:11px; color:var(--muted); text-transform:uppercase; font-weight:600;">Extracted Deductions</span>
                    <div style="margin-top:6px; background:rgba(0,0,0,0.1); border-radius:10px; padding:12px;">
                        ${allowancesListHtml}
                    </div>
                </div>

                <div style="background: rgba(212,168,67,0.05); border-radius:10px; padding:12px; font-size:12px; line-height:1.6; border-left:3px solid var(--gold);">
                    <strong>Findings Summary:</strong> ${p.summary_findings || 'No summary generated.'}
                </div>

                <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:5px;">
                    <button class="btn btn-gold" onclick="importPdfToTax()" style="flex:1; min-width: 150px;">📥 Import to Tax Planner</button>
                    <button class="btn btn-ghost" onclick="importPdfToNetWorth()" style="flex:1; min-width: 150px;">📥 Import to Assets</button>
                </div>
            </div>`;
        initTiltEffect();
    } catch (e) {
        parseBtn.disabled = false;
        parseBtn.textContent = 'Parse PDF';
        resultEl.innerHTML = `<div class="negative" style="font-size:13px;">Error: PDF parsing failed.</div>`;
    }
}

function importPdfToTax() {
    if (!lastParsedPdfData) return;
    
    document.getElementById('taxIncome').value = lastParsedPdfData.gross_income || 0;
    
    const d = lastParsedPdfData.allowances_deductions || {};
    document.getElementById('tax80C').value = d['80C'] || 0;
    document.getElementById('tax80D').value = d['80D'] || 0;
    document.getElementById('taxHRA').value = d['HRA'] || 0;
    
    // Switch navigation tab to Tax Planner
    const taxNavItem = document.querySelector('[data-page="tools"]');
    if (taxNavItem) { 
        taxNavItem.click(); 
        calcTax();
    }
}

async function importPdfToNetWorth() {
    if (!lastParsedPdfData) return;
    
    const income = lastParsedPdfData.gross_income || 0;
    const org = lastParsedPdfData.employer_organization || 'Parsed Employer';
    
    try {
        await fetch('/add-asset', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ name: `Salary (${org})`, amount: income / 12 }) 
        });
        alert('Successfully added monthly salary to assets!');
        
        // Refresh net worth tab
        loadNetWorth();
    } catch (e) {
        alert('Failed to import into net worth.');
    }
}

// ========== EXPENSES TRACKER WITH HISTORIC DETAILS & AI ACCURACY ==========
async function loadExpenses() {
    try {
        const res = await fetch('/calculate');
        const data = await res.json();
        const expenses = data.expenses || [];
        
        // Total Spend
        const total = expenses.reduce((s, e) => s + e.amount, 0) || 0;
        document.getElementById('totalSpend').innerHTML = `₹${fmtNum(total)}`;
        
        // Average Spend
        const avg = expenses.length > 0 ? (total / expenses.length) : 0;
        document.getElementById('avgExpense').innerHTML = `₹${fmtNum(avg)}`;
        
        // AI Accuracy Rate Calculation
        // AI Accuracy = (Total count of AI categorizations - user corrections) / Total AI categorizations
        const aiRecords = expenses.filter(e => e.ai_confidence > 0);
        const corrected = aiRecords.filter(e => e.user_corrected).length;
        const accuracy = aiRecords.length > 0 ? (((aiRecords.length - corrected) / aiRecords.length) * 100) : 100;
        document.getElementById('aiAccuracy').innerHTML = `${Math.round(accuracy)}%`;
        
        // Populate Expense Table
        const tbody = document.getElementById('expenseTableBody');
        tbody.innerHTML = '';
        
        const categories = ["Food Dining", "Transportation", "Shopping", "Entertainment", "Bills", "Groceries", "Healthcare", "Education", "Rent", "Travel", "Subscription", "Other"];
        
        expenses.forEach(e => {
            const dateFmt = e.date || new Date().toISOString().split('T')[0];
            const confidenceVal = Math.round((e.ai_confidence || 0) * 100);
            
            // Build Category Dropdown options
            const selectOptions = categories.map(cat => `
                <option value="${cat}" ${cat.toLowerCase() === e.category.toLowerCase() ? 'selected' : ''}>${cat}</option>
            `).join('');
            
            tbody.innerHTML += `
                <tr>
                    <td style="text-align:left;">${dateFmt}</td>
                    <td style="text-align:left; font-weight:600;">${e.merchant_name || e.category}</td>
                    <td style="text-align:left;">
                        <select onchange="correctExpenseCategory(${e.id}, this.value, '${e.merchant_name || ''}')" style="padding:4px 8px; font-size:12px; background:rgba(0,0,0,0.2); border:1px solid var(--border); border-radius:6px; max-width: 140px;">
                            ${selectOptions}
                        </select>
                    </td>
                    <td style="font-weight:700;">₹${fmtNum(e.amount)}</td>
                    <td>
                        <span style="font-size:11px; padding:2px 8px; border-radius:99px; background:rgba(20,200,191,0.08); color:var(--teal);">
                            ${confidenceVal > 0 ? `${confidenceVal}% AI` : 'Manual'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-ghost" style="padding:4px 8px; color:var(--red);" onclick="deleteExpense(${e.id})">✖</button>
                    </td>
                </tr>`;
        });
        
        // Update Chart
        const categoriesSpend = {};
        expenses.forEach(e => {
            categories_name = e.category || 'Other';
            categories_name = categories_name.charAt(0).toUpperCase() + categories_name.slice(1);
            categoriesSpend[categories_name] = (categoriesSpend[categories_name] || 0) + e.amount;
        });
        
        const canvas = document.getElementById('expenseChart');
        if (canvas && Object.keys(categoriesSpend).length > 0) {
            if (expenseChart) expenseChart.destroy();
            const ctx = canvas.getContext('2d');
            const isDark = !document.body.classList.contains('light-theme');
            expenseChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: Object.keys(categoriesSpend),
                    datasets: [{
                        label: 'Spending by Category',
                        data: Object.values(categoriesSpend),
                        backgroundColor: 'rgba(20,200,191,0.7)',
                        borderRadius: 6,
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { ticks: { color: isDark ? '#5a6a82' : '#1f2937' }, grid: { display: false } },
                        y: { ticks: { color: isDark ? '#5a6a82' : '#1f2937' }, grid: { color: 'rgba(255,255,255,0.04)' } }
                    }
                }
            });
        }
        
        // Fetch and load insights
        loadExpenseInsights();
    } catch (e) {
        console.error("loadExpenses error:", e);
    }
}

async function loadExpenseInsights() {
    try {
        const res = await fetch('/insights');
        const data = await res.json();
        const insightEl = document.getElementById('insights');
        if (insightEl) insightEl.innerHTML = data.insights || 'Add expenses to see AI recommendations.';
    } catch(e) {}
}

async function addExpenseWithAI() {
    const descInput = document.getElementById('ai_description');
    const amtInput = document.getElementById('ai_amount');
    const dateInput = document.getElementById('ai_date');
    
    const description = descInput.value.trim();
    const amount = parseFloat(amtInput.value);
    const date = dateInput.value || new Date().toISOString().split('T')[0];
    
    if (!description || !amount) { alert('Fill all fields'); return; }
    
    const res = await fetch('/add_expense_ai', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ description, amount, date }) 
    });
    const data = await res.json();
    if (data.status === 'success') {
        alert(data.message);
        descInput.value = '';
        amtInput.value = '';
        loadExpenses();
    } else {
        alert('Error: ' + data.error);
    }
}

async function correctExpenseCategory(expenseId, correctCategory, description) {
    try {
        const res = await fetch('/correct_category', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                expense_id: expenseId, 
                correct_category: correctCategory, 
                description: description 
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            loadExpenses();
        } else {
            alert('Error updating category: ' + data.error);
        }
    } catch (e) {
        console.error("correct category error:", e);
    }
}

async function deleteExpense(id) {
    if (!confirm('Are you sure you want to delete this expense?')) return;
    const res = await fetch(`/expense/delete/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.status === 'success' || data.success) {
        loadExpenses();
    } else {
        alert('Error: ' + data.error);
    }
}

// ========== NET WORTH TRACKER WITH ALLOCATION CHART ==========
async function loadNetWorth() {
    try {
        const res = await fetch('/net-worth');
        const data = await res.json();
        
        document.getElementById('nwAssets').innerHTML = `₹${fmtNum(data.total_assets)}`;
        document.getElementById('nwLiabilities').innerHTML = `₹${fmtNum(data.total_liabilities)}`;
        document.getElementById('nwTotal').innerHTML = `₹${fmtNum(data.net_worth)}`;
        
        // Populate asset list with delete button targeting DB id
        document.getElementById('assetList').innerHTML = data.assets.map(a => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px; border-bottom:1px solid var(--border);">
                <span>${a.name}: <strong style="color:var(--text);">₹${fmtNum(a.amount)}</strong></span>
                <button class="btn btn-ghost" style="padding:2px 6px; font-size:10px; color:var(--red);" onclick="deleteNWItem('asset', ${a.id})">✖</button>
            </div>`).join('');
            
        // Populate liability list with delete button targeting DB id
        document.getElementById('liabList').innerHTML = data.liabilities.map(l => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px; border-bottom:1px solid var(--border);">
                <span>${l.name}: <strong style="color:var(--text);">₹${fmtNum(l.amount)}</strong></span>
                <button class="btn btn-ghost" style="padding:2px 6px; font-size:10px; color:var(--red);" onclick="deleteNWItem('liability', ${l.id})">✖</button>
            </div>`).join('');
            
        // Draw Chart.js Doughnut for Asset vs Liabilities
        const canvas = document.getElementById('netWorthChart');
        if (canvas) {
            if (netWorthChartObj) netWorthChartObj.destroy();
            const ctx = canvas.getContext('2d');
            const isDark = !document.body.classList.contains('light-theme');
            netWorthChartObj = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Assets', 'Liabilities'],
                    datasets: [{
                        data: [data.total_assets || 1, data.total_liabilities || 0],
                        backgroundColor: ['#2ecc8a', '#e05252'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: isDark ? '#eef0f5' : '#1f2937' }
                        }
                    }
                }
            });
        }
        
        // Sync values to Dashboard stats
        refreshDashboardStats();
    } catch (e) {
        console.error("loadNetWorth error:", e);
    }
}

async function deleteNWItem(type, id) {
    if (!confirm('Are you sure you want to remove this item?')) return;
    try {
        const res = await fetch('/delete-item', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, id })
        });
        const data = await res.json();
        if (data.status === 'success') {
            loadNetWorth();
        } else {
            alert('Error deleting item: ' + data.error);
        }
    } catch (e) {
        console.error(e);
    }
}

function initTiltEffect() {
    const cards = document.querySelectorAll('.card, .stat-card');
    cards.forEach(card => {
        if (card.dataset.tiltBound) return;
        card.dataset.tiltBound = 'true';
        
        // Add a smooth transition property for hover and leave
        card.style.transition = 'transform 0.15s ease, box-shadow 0.3s ease, border-color 0.4s ease';
        
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const xc = rect.width / 2;
            const yc = rect.height / 2;
            
            const maxAngle = 3.5;
            const angleX = -((yc - y) / yc) * maxAngle;
            const angleY = ((x - xc) / xc) * maxAngle;
            
            card.style.transform = `perspective(1000px) rotateX(${angleX.toFixed(2)}deg) rotateY(${angleY.toFixed(2)}deg) scale3d(1.006, 1.006, 1.006)`;
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transition = 'transform 0.6s cubic-bezier(0.165, 0.84, 0.44, 1), box-shadow 0.6s cubic-bezier(0.165, 0.84, 0.44, 1)';
            card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
        });
        
        card.addEventListener('mouseenter', () => {
            card.style.transition = 'transform 0.15s ease, box-shadow 0.3s ease';
        });
    });
}

// ========== USER AUTHENTICATION ==========
function switchAuthTab(mode) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const loginToggle = document.getElementById('authLoginToggle');
    const registerToggle = document.getElementById('authRegisterToggle');
    const msg = document.getElementById('authMessage');
    
    if (msg) msg.style.display = 'none';
    
    if (mode === 'login') {
        loginForm.style.display = 'flex';
        registerForm.style.display = 'none';
        loginToggle.style.background = 'var(--ghost-btn-hover-bg)';
        registerToggle.style.background = 'transparent';
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'flex';
        loginToggle.style.background = 'transparent';
        registerToggle.style.background = 'var(--ghost-btn-hover-bg)';
    }
    initTiltEffect();
}

async function handleAuthSubmit(e, mode) {
    e.preventDefault();
    const msg = document.getElementById('authMessage');
    msg.style.display = 'none';
    
    let url = '/login';
    let bodyData = {};
    
    if (mode === 'login') {
        bodyData.username = document.getElementById('loginUsername').value;
        bodyData.password = document.getElementById('loginPassword').value;
    } else {
        url = '/register';
        const p1 = document.getElementById('registerPassword').value;
        const p2 = document.getElementById('registerConfirmPassword').value;
        if (p1 !== p2) {
            msg.className = 'negative';
            msg.innerHTML = 'Passwords do not match.';
            msg.style.display = 'block';
            return;
        }
        bodyData.username = document.getElementById('registerUsername').value;
        bodyData.password = p1;
    }
    
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bodyData)
        });
        const data = await res.json();
        
        if (res.ok && data.success) {
            msg.className = 'positive';
            msg.innerHTML = data.message;
            msg.style.display = 'block';
            
            setTimeout(() => {
                window.location.reload();
            }, 800);
        } else {
            msg.className = 'negative';
            msg.innerHTML = data.message || 'Authentication failed.';
            msg.style.display = 'block';
        }
    } catch (err) {
        msg.className = 'negative';
        msg.innerHTML = 'Failed to connect to authentication server.';
        msg.style.display = 'block';
    }
}

async function logoutUser(e) {
    e.preventDefault();
    try {
        const res = await fetch('/logout', {
            method: 'POST',
            headers: { 'Accept': 'application/json' }
        });
        if (res.ok) {
            window.location.reload();
        }
    } catch (err) {
        window.location.href = '/logout';
    }
}

// ========== USER PROFILE & ACCOUNT SETTINGS ==========
async function loadUserProfile() {
    try {
        const res = await fetch('/profile/summary');
        const data = await res.json();
        if (data.success) {
            document.getElementById('profUsername').innerText = data.username;
            document.getElementById('profJoinedDate').innerText = data.joined_date;
            
            document.getElementById('profAssets').innerText = `₹${fmtNum(data.assets_total)}`;
            document.getElementById('profLiabilities').innerText = `₹${fmtNum(data.liabilities_total)}`;
            
            const nwSign = data.net_worth >= 0 ? '' : '-';
            const nwClass = data.net_worth >= 0 ? 'positive' : 'negative';
            document.getElementById('profNetWorth').className = nwClass;
            document.getElementById('profNetWorth').innerText = `${nwSign}₹${fmtNum(Math.abs(data.net_worth))}`;
            
            document.getElementById('profExpenses').innerText = `₹${fmtNum(data.expenses_total)}`;
            document.getElementById('profPortfolio').innerText = `₹${fmtNum(data.portfolio_invested)}`;
            document.getElementById('profAlerts').innerText = data.alerts_count;
            
            initTiltEffect();
        }
    } catch (e) {
        console.error("Failed to load user profile:", e);
    }
}

async function handlePasswordChange(e) {
    e.preventDefault();
    const msg = document.getElementById('passwordChangeMessage');
    if (msg) msg.style.display = 'none';
    
    const old_password = document.getElementById('oldPasswordInput').value;
    const new_password = document.getElementById('newPasswordInput').value;
    const confirm_password = document.getElementById('confirmNewPasswordInput').value;
    
    if (new_password !== confirm_password) {
        if (msg) {
            msg.className = 'negative';
            msg.innerText = 'New passwords do not match.';
            msg.style.display = 'block';
        }
        return;
    }
    
    try {
        const res = await fetch('/profile/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password, new_password })
        });
        const data = await res.json();
        
        if (res.ok && data.success) {
            if (msg) {
                msg.className = 'positive';
                msg.innerText = data.message;
                msg.style.display = 'block';
            }
            document.getElementById('changePasswordForm').reset();
        } else {
            if (msg) {
                msg.className = 'negative';
                msg.innerText = data.message || 'Password update failed.';
                msg.style.display = 'block';
            }
        }
    } catch (err) {
        if (msg) {
            msg.className = 'negative';
            msg.innerText = 'Failed to connect to server.';
            msg.style.display = 'block';
        }
    }
}

async function resetAllUserData() {
    if (!confirm('🧹 Are you sure you want to reset all account data?\nThis will permanently delete all your logged assets, liabilities, portfolio holdings, expenses, and alerts. This cannot be undone.')) return;
    
    try {
        const res = await fetch('/profile/reset', { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.success) {
            alert(data.message);
            loadUserProfile();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to reset account data.');
    }
}

async function deleteUserAccount() {
    if (!confirm('❌ Are you sure you want to permanently delete your account?\nThis will delete your login credentials and purge all your personal financial records completely. This cannot be undone.')) return;
    
    try {
        const res = await fetch('/profile/delete', { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.success) {
            alert(data.message);
            window.location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (e) {
        alert('Failed to delete account.');
    }
}

// Initialise App state
document.addEventListener('DOMContentLoaded', () => {
    if (document.body.classList.contains('not-logged-in')) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const auth = document.getElementById('authPage');
        if (auth) {
            auth.style.display = 'flex';
            initTiltEffect();
        }
        return;
    }
    refreshDashboardStats();
    initTiltEffect();
});