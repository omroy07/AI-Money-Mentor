// HTML escape helper (issue #517)
function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}

// Interactive Dashboard with Drag-and-Drop Widgets

class DashboardManager {
  constructor() {
    this.widgets = [];
    this.layouts = {};
    this.currentLayout = 'default';
    this.draggedItem = null;
    this.isDragging = false;
    this.init();
  }

  init() {
    this.loadLayouts();
    this.renderDashboard();
    this.setupDragAndDrop();
    this.setupWebSocket();
  }

  loadLayouts() {
    // Load saved layouts from localStorage
    const saved = localStorage.getItem('dashboard_layouts');
    if (saved) {
      this.layouts = JSON.parse(saved);
      if (this.layouts[this.currentLayout]) {
        this.widgets = this.layouts[this.currentLayout].widgets;
        return;
      }
    }
    this.widgets = this.getDefaultWidgets();
    this.saveLayouts();
  }

  getDefaultWidgets() {
    return [
      {
        id: 'net_worth',
        title: '💎 Net Worth',
        type: 'net_worth',
        size: 'medium',
      },
      {
        id: 'spending_trend',
        title: '📈 Spending Trend',
        type: 'spending_trend',
        size: 'large',
      },
      {
        id: 'budget_health',
        title: '🎯 Budget Health',
        type: 'budget_health',
        size: 'medium',
      },
      {
        id: 'recent_transactions',
        title: '💳 Recent Transactions',
        type: 'recent_transactions',
        size: 'medium',
      },
      {
        id: 'portfolio_summary',
        title: '📊 Portfolio Summary',
        type: 'portfolio_summary',
        size: 'large',
      },
      {
        id: 'goals_progress',
        title: '🎯 Goals Progress',
        type: 'goals_progress',
        size: 'medium',
      },
      {
        id: 'cash_flow',
        title: '💰 Cash Flow',
        type: 'cash_flow',
        size: 'medium',
      },
      {
        id: 'add_widget',
        title: '➕ Add Widget',
        type: 'add_widget',
        size: 'small',
      },
    ];
  }

  saveLayouts() {
    if (!this.layouts[this.currentLayout]) {
      this.layouts[this.currentLayout] = {
        id: this.currentLayout,
        name: 'Default Layout',
        widgets: this.widgets,
        created_at: new Date().toISOString(),
      };
    } else {
      this.layouts[this.currentLayout].widgets = this.widgets;
      this.layouts[this.currentLayout].updated_at = new Date().toISOString();
    }
    localStorage.setItem('dashboard_layouts', JSON.stringify(this.layouts));
    // Save to server
    this.saveToServer();
  }

  async saveToServer() {
    try {
      const response = await fetch('/api/dashboard/layouts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          layout_id: this.currentLayout,
          widgets: this.widgets,
        }),
      });
      const data = await response.json();
      if (!data.success) {
        console.error('Failed to save layout:', data.error);
      }
    } catch (error) {
      console.error('Error saving layout:', error);
    }
  }

  renderDashboard() {
    const container = document.getElementById('dashboardGrid');
    if (!container) return;

    container.innerHTML = '';
    this.widgets.forEach((widget, index) => {
      const widgetEl = this.createWidgetElement(widget, index);
      container.appendChild(widgetEl);
    });
  }

  createWidgetElement(widget, index) {
    const div = document.createElement('div');
    div.className = `widget-container widget-size-${widget.size || 'medium'}`;
    div.dataset.id = widget.id;
    div.dataset.index = index;
    div.draggable = true;

    div.innerHTML = `
            <div class="widget-header">
                <span class="drag-handle">⠿</span>
                <span class="widget-title">${esc(widget.title)}</span>
                <div class="widget-actions">
                    ${
                      widget.id !== 'add_widget'
                        ? `
                        <button onclick="dashboardManager.removeWidget('${esc(widget.id)}')" title="Remove">✖</button>
                    `
                        : ''
                    }
                    <button onclick="dashboardManager.refreshWidget('${esc(widget.id)}')" title="Refresh">⟳</button>
                </div>
            </div>
            <div class="widget-content" id="widget-content-${esc(widget.id)}">
                <div style="text-align:center;padding:20px;color:#5a6a82;">
                    <div class="spinner"></div>
                    <div style="margin-top:8px;">Loading...</div>
                </div>
            </div>
        `;

    // Load widget data
    this.loadWidgetData(widget.id);

    // Drag events
    div.addEventListener('dragstart', (e) => {
      this.isDragging = true;
      this.draggedItem = index;
      div.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/html', div.outerHTML);
    });

    div.addEventListener('dragend', () => {
      this.isDragging = false;
      div.classList.remove('dragging');
    });

    div.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });

    div.addEventListener('drop', (e) => {
      e.preventDefault();
      if (this.draggedItem !== null && this.draggedItem !== index) {
        this.reorderWidgets(this.draggedItem, index);
        this.draggedItem = null;
      }
    });

    return div;
  }

  async loadWidgetData(widgetId) {
    try {
      const response = await fetch(`/api/dashboard/widget/${widgetId}`);
      const data = await response.json();
      if (data.success) {
        this.renderWidgetContent(widgetId, data.data);
      }
    } catch (error) {
      console.error('Error loading widget data:', error);
    }
  }

  renderWidgetContent(widgetId, data) {
    const container = document.getElementById(`widget-content-${widgetId}`);
    if (!container) return;

    // Render based on widget type
    switch (widgetId) {
      case 'net_worth':
        container.innerHTML = this.renderNetWorth(data);
        break;
      case 'spending_trend':
        container.innerHTML = this.renderSpendingTrend(data);
        break;
      case 'budget_health':
        container.innerHTML = this.renderBudgetHealth(data);
        break;
      case 'recent_transactions':
        container.innerHTML = this.renderRecentTransactions(data);
        break;
      case 'portfolio_summary':
        container.innerHTML = this.renderPortfolioSummary(data);
        break;
      case 'goals_progress':
        container.innerHTML = this.renderGoalsProgress(data);
        break;
      case 'cash_flow':
        container.innerHTML = this.renderCashFlow(data);
        break;
      case 'add_widget':
        container.innerHTML = this.renderAddWidget();
        break;
      default:
        container.innerHTML = `<div class="text-muted">Widget data loaded</div>`;
    }
  }

  renderNetWorth(data) {
    const isPositive = data.net_worth >= 0;
    return `
            <div class="widget-net-worth">
                <div class="value">₹${this.formatNumber(data.net_worth)}</div>
                <div class="${isPositive ? 'positive' : 'negative'}">
                    ${isPositive ? '▲' : '▼'} ${Math.abs(data.change)}% from last month
                </div>
                <div style="font-size:12px;color:#5a6a82;margin-top:4px;">
                    Assets: ₹${this.formatNumber(data.total_assets)} | Liabilities: ₹${this.formatNumber(data.total_liabilities)}
                </div>
            </div>
        `;
  }

  renderSpendingTrend(data) {
    return `
            <div class="widget-spending-trend">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                    <span>This Month: <strong>₹${this.formatNumber(data.current_month)}</strong></span>
                    <span class="${data.change_percent >= 0 ? 'negative' : 'positive'}">
                        ${data.change_percent >= 0 ? '▲' : '▼'} ${Math.abs(data.change_percent)}%
                    </span>
                </div>
                <div class="chart-container">
                    <canvas id="trendChart"></canvas>
                </div>
                <script>
                    setTimeout(() => {
                        const ctx = document.getElementById('trendChart');
                        if (ctx) {
                            new Chart(ctx, {
                                type: 'line',
                                data: {
                                    labels: ${JSON.stringify(data.trend.map((_, i) => `Week ${i + 1}`))},
                                    datasets: [{
                                        label: 'Spending',
                                        data: ${JSON.stringify(data.trend)},
                                        borderColor: '#d4a843',
                                        backgroundColor: 'rgba(212,168,67,0.1)',
                                        fill: true,
                                        tension: 0.4
                                    }]
                                },
                                options: {
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: { legend: { display: false } },
                                    scales: {
                                        y: { ticks: { color: '#5a6a82' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                                        x: { ticks: { color: '#5a6a82' }, grid: { display: false } }
                                    }
                                }
                            });
                        }
                    }, 100);
                </script>
            </div>
        `;
  }

  renderBudgetHealth(data) {
    const pct = Math.min(data.health_percent || 0, 100);
    const color = pct > 80 ? '#2ecc8a' : pct > 60 ? '#d4a843' : '#e05252';
    return `
            <div class="widget-budget-health">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                    <span>Budget Used</span>
                    <span>${pct}%</span>
                </div>
                <div class="budget-bar">
                    <div class="fill" style="width:${pct}%;background:${color};"></div>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:12px;color:#5a6a82;">
                    <span>₹${this.formatNumber(data.total_spent)} spent</span>
                    <span>₹${this.formatNumber(data.remaining)} remaining</span>
                </div>
                <div style="margin-top:8px;">
                    ${data.categories
                      .map(
                        (c) => `
                        <div style="display:flex;justify-content:space-between;font-size:12px;padding:2px 0;">
                            <span>${esc(c.name)}</span>
                            <span>₹${this.formatNumber(c.spent)} / ₹${this.formatNumber(c.budget)}</span>
                        </div>
                    `,
                      )
                      .join('')}
                </div>
            </div>
        `;
  }

  renderRecentTransactions(data) {
    return `
            <div class="widget-recent-transactions">
                ${data.transactions
                  .map(
                    (t) => `
                    <div class="transaction-item">
                        <div>
                            <div>${esc(t.category)}</div>
                            <div style="font-size:11px;color:#5a6a82;">${esc(t.date)}</div>
                        </div>
                        <div style="font-weight:600;color:${t.amount < 0 ? '#e05252' : '#2ecc8a'};">
                            ${t.amount < 0 ? '-' : '+'}₹${this.formatNumber(Math.abs(t.amount))}
                        </div>
                    </div>
                `,
                  )
                  .join('')}
            </div>
        `;
  }

  renderPortfolioSummary(data) {
    return `
            <div class="widget-portfolio">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                    <span>Total Value</span>
                    <span style="font-size:20px;font-weight:800;color:#d4a843;">₹${this.formatNumber(data.total_value)}</span>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:13px;color:#5a6a82;margin-bottom:8px;">
                    <span>Returns: ${data.returns}%</span>
                </div>
                ${data.holdings
                  .map(
                    (h) => `
                    <div style="display:flex;justify-content:space-between;font-size:12px;padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
                        <span>${esc(h.symbol)}</span>
                        <span>₹${this.formatNumber(h.value)} (${h.percent}%)</span>
                    </div>
                `,
                  )
                  .join('')}
            </div>
        `;
  }

  renderGoalsProgress(data) {
    return `
            <div class="widget-goals-progress">
                ${data.goals
                  .map(
                    (g) => `
                    <div class="goal-item">
                        <div style="display:flex;justify-content:space-between;font-size:13px;">
                            <span>${esc(g.name)}</span>
                            <span>${g.progress}%</span>
                        </div>
                        <div class="goal-progress-bar">
                            <div class="fill" style="width:${Math.min(g.progress, 100)}%;"></div>
                        </div>
                        <div style="font-size:11px;color:#5a6a82;">
                            ₹${this.formatNumber(g.current)} / ₹${this.formatNumber(g.target)}
                        </div>
                    </div>
                `,
                  )
                  .join('')}
            </div>
        `;
  }

  renderCashFlow(data) {
    return `
            <div class="widget-cash-flow">
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;text-align:center;">
                    <div style="background:rgba(46,204,138,0.05);border-radius:8px;padding:8px;">
                        <div style="font-size:11px;color:#5a6a82;">Income</div>
                        <div style="font-size:18px;font-weight:700;color:#2ecc8a;">₹${this.formatNumber(data.income)}</div>
                    </div>
                    <div style="background:rgba(224,82,82,0.05);border-radius:8px;padding:8px;">
                        <div style="font-size:11px;color:#5a6a82;">Expenses</div>
                        <div style="font-size:18px;font-weight:700;color:#e05252;">₹${this.formatNumber(data.expenses)}</div>
                    </div>
                    <div style="background:rgba(212,168,67,0.05);border-radius:8px;padding:8px;">
                        <div style="font-size:11px;color:#5a6a82;">Net</div>
                        <div style="font-size:18px;font-weight:700;color:${data.net >= 0 ? '#2ecc8a' : '#e05252'};">
                            ₹${this.formatNumber(data.net)}
                        </div>
                    </div>
                </div>
            </div>
        `;
  }

  renderAddWidget() {
    return `
            <div class="widget-add">
                <button class="add-widget-btn" onclick="dashboardManager.showAddWidgetModal()">
                    ➕ Add New Widget
                </button>
            </div>
        `;
  }

  showAddWidgetModal() {
    const widgetTypes = [
      { id: 'net_worth', title: '💎 Net Worth' },
      { id: 'spending_trend', title: '📈 Spending Trend' },
      { id: 'budget_health', title: '🎯 Budget Health' },
      { id: 'recent_transactions', title: '💳 Recent Transactions' },
      { id: 'portfolio_summary', title: '📊 Portfolio Summary' },
      { id: 'goals_progress', title: '🎯 Goals Progress' },
      { id: 'cash_flow', title: '💰 Cash Flow' },
      { id: 'investment_returns', title: '📈 Investment Returns' },
      { id: 'savings_rate', title: '💾 Savings Rate' },
      { id: 'credit_score', title: '⭐ Credit Score' },
      { id: 'market_news', title: '📰 Market News' },
      { id: 'tax_estimator', title: '💸 Tax Estimator' },
      { id: 'emergency_fund', title: '🛡️ Emergency Fund' },
      { id: 'expense_categories', title: '📊 Expense Categories' },
    ];

    let html = `
            <div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;" onclick="this.remove()">
                <div style="background:#0d1320;border-radius:18px;padding:30px;max-width:600px;width:90%;max-height:80vh;overflow-y:auto;" onclick="event.stopPropagation()">
                    <h3 style="color:#d4a843;margin-bottom:16px;">➕ Add Widget</h3>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                        ${widgetTypes
                          .map(
                            (w) => `
                            <button onclick="dashboardManager.addWidget('${esc(w.id)}','${esc(w.title)}')" 
                                    style="padding:10px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:8px;color:#eef0f5;cursor:pointer;transition:all 0.2s;"
                                    onmouseover="this.style.borderColor='#d4a843'" 
                                    onmouseout="this.style.borderColor='rgba(255,255,255,0.06)'">
                                ${esc(w.title)}
                            </button>
                        `,
                          )
                          .join('')}
                    </div>
                    <button onclick="this.closest('div[style]').remove()" style="margin-top:16px;padding:8px 20px;background:transparent;border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:#5a6a82;cursor:pointer;width:100%;">
                        Cancel
                    </button>
                </div>
            </div>
        `;
    document.body.insertAdjacentHTML('beforeend', html);
  }

  addWidget(widgetId, widgetTitle) {
    // Check if widget already exists
    if (this.widgets.some((w) => w.id === widgetId)) {
      alert('Widget already exists on dashboard!');
      document.querySelector('div[style*="position:fixed"]')?.remove();
      return;
    }

    this.widgets.push({
      id: widgetId,
      title: widgetTitle,
      type: widgetId,
      size: 'medium',
    });

    this.saveLayouts();
    this.renderDashboard();
    document.querySelector('div[style*="position:fixed"]')?.remove();
  }

  removeWidget(widgetId) {
    if (widgetId === 'add_widget') return;
    this.widgets = this.widgets.filter((w) => w.id !== widgetId);
    this.saveLayouts();
    this.renderDashboard();
  }

  refreshWidget(widgetId) {
    this.loadWidgetData(widgetId);
  }

  reorderWidgets(fromIndex, toIndex) {
    const [removed] = this.widgets.splice(fromIndex, 1);
    this.widgets.splice(toIndex, 0, removed);
    this.saveLayouts();
    this.renderDashboard();
  }

  setupDragAndDrop() {
    // Additional drag-and-drop setup if needed
  }

  setupWebSocket() {
    // Connect to WebSocket for real-time updates
    try {
      const socket = io();
      socket.on('connect', () => {
        console.log('🔌 Dashboard WebSocket connected');
      });
      socket.on('dashboard_update', (data) => {
        console.log('📊 Dashboard update received:', data);
        this.refreshWidget(data.widget_id);
      });
    } catch (e) {
      console.log('WebSocket not available');
    }
  }

  formatNumber(num) {
    if (!num) return '0';
    return new Intl.NumberFormat('en-IN').format(Math.round(num));
  }
}

// Initialize dashboard
let dashboardManager;

document.addEventListener('DOMContentLoaded', () => {
  dashboardManager = new DashboardManager();
});
