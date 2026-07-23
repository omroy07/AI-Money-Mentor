// HTML escape helper (issue #517)
function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}

// Recurring Expenses - JavaScript

// Load recurring expenses
function loadRecurring() {
  const container = document.getElementById('recurringList');
  container.innerHTML = `
        <div class="text-center text-muted py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading recurring expenses...</p>
        </div>
    `;

  fetch('/api/recurring/list')
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        renderRecurringList(data.recurring);
        updateStats(data.recurring);
      } else {
        container.innerHTML = `
                    <div class="alert alert-danger">❌ Error: ${esc(data.error)}</div>
                `;
      }
    })
    .catch((err) => {
      console.error('Error loading recurring:', err);
      container.innerHTML = `
                <div class="alert alert-danger">❌ Failed to load recurring expenses</div>
            `;
    });
}

function renderRecurringList(recurring) {
  const container = document.getElementById('recurringList');

  if (!recurring || recurring.length === 0) {
    container.innerHTML = `
            <div class="text-center text-muted py-4">
                <div style="font-size: 48px;">📭</div>
                <p class="mt-2">No recurring expenses yet</p>
                <p class="small">Add one manually or scan for patterns</p>
            </div>
        `;
    return;
  }

  const frequencyLabels = {
    weekly: '📅 Weekly',
    monthly: '📅 Monthly',
    quarterly: '📅 Quarterly',
    yearly: '📅 Yearly',
  };

  let html =
    '<div class="table-responsive"><table class="table table-dark table-hover">';
  html += `
        <thead>
            <tr>
                <th>Merchant</th>
                <th>Category</th>
                <th>Amount</th>
                <th>Frequency</th>
                <th>Next Due</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
    `;

  recurring.forEach((r) => {
    const statusClass = r.is_active ? 'text-success' : 'text-muted';
    const statusText = r.is_active ? 'Active ✅' : 'Paused ⏸️';

    html += `
            <tr>
                <td><strong>${r.merchant || 'N/A'}</strong></td>
                <td><span class="badge bg-secondary">${esc(r.category)}</span></td>
                <td><strong>₹${formatNumber(r.amount)}</strong></td>
                <td>${frequencyLabels[r.frequency] || r.frequency}</td>
                <td>${formatDate(r.next_due_date)}</td>
                <td class="${statusClass}">${statusText}</td>
                <td>
                    <button class="btn btn-sm btn-${r.is_active ? 'warning' : 'success'}" onclick="toggleRecurring(${r.id})">
                        ${r.is_active ? '⏸️' : '▶️'}
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteRecurring(${r.id})">🗑️</button>
                </td>
            </tr>
        `;
  });

  html += '</tbody></table></div>';
  container.innerHTML = html;
}
function startOfDay(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function updateStats(recurring) {
  const active = recurring.filter((r) => r.is_active);
  const totalMonthly = active.reduce((sum, r) => {
    if (r.frequency === 'monthly') return sum + r.amount;
    if (r.frequency === 'weekly') return sum + r.amount * 4;
    if (r.frequency === 'quarterly') return sum + r.amount / 3;
    if (r.frequency === 'yearly') return sum + r.amount / 12;
    return sum + r.amount;
  }, 0);

  const today = startOfDay(new Date());
  const weekLater = startOfDay(new Date());
  weekLater.setDate(today.getDate() + 7);

  const dueThisWeek = active.filter((r) => {
    if (!r.next_due_date) return false;
    const dueDate = startOfDay(new Date(r.next_due_date + 'T00:00:00'));
    return dueDate >= today && dueDate <= weekLater;
  });

  const autoAddCount = active.filter((r) => r.auto_add).length;

  document.getElementById('totalMonthly').textContent =
    '₹' + formatNumber(totalMonthly);
  document.getElementById('activeCount').textContent = active.length;
  document.getElementById('dueThisWeek').textContent = dueThisWeek.length;
  document.getElementById('autoAddCount').textContent = autoAddCount;
}

function formatNumber(n) {
  if (!n) return '0';
  return new Intl.NumberFormat('en-IN').format(Math.round(n));
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

// Detect recurring expenses
function detectRecurring() {
  const container = document.getElementById('detectionResults');
  const btn = container.previousElementSibling;

  btn.disabled = true;
  btn.textContent = '🔍 Scanning...';
  container.innerHTML =
    '<div class="text-center"><div class="spinner-border text-primary"></div><p class="mt-2">Scanning your expenses...</p></div>';

  fetch('/api/recurring/detect')
    .then((res) => res.json())
    .then((data) => {
      btn.disabled = false;
      btn.textContent = '🔍 Scan for Patterns';

      if (data.success && data.detected && data.detected.length > 0) {
        let html = `
                    <div class="alert alert-success">
                        ✅ Found <strong>${data.detected.length}</strong> recurring patterns!
                    </div>
                `;

        data.detected.forEach((p) => {
          const confidenceColor =
            p.confidence === 'high' ? 'success' : 'warning';
          html += `
                        <div class="detected-item" style="background: rgba(46, 204, 138, 0.1); border-left: 4px solid #2ecc8a; padding: 12px; margin-bottom: 8px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                            <div class="info">
                                <strong>${p.merchant}</strong>
                                <span class="badge bg-secondary">${p.category}</span>
                                <span class="badge bg-${confidenceColor}">${p.confidence} confidence</span>
                                <br>
                                <small>₹${formatNumber(p.amount)} • ${p.frequency} • Next: ${formatDate(p.next_due)}</small>
                            </div>
                            <button class="btn btn-sm btn-primary" onclick="addDetectedPattern('${p.merchant}', '${p.category}', ${p.amount}, '${p.frequency}', '${p.next_due}')">
                                ✅ Add
                            </button>
                        </div>
                    `;
        });

        container.innerHTML = html;
      } else {
        container.innerHTML = `
                    <div class="alert alert-info">
                        📭 No recurring patterns found in the last 60 days.<br>
                        <small>Add expenses first or try manually adding a recurring expense.</small>
                    </div>
                `;
      }
    })
    .catch((err) => {
      btn.disabled = false;
      btn.textContent = '🔍 Scan for Patterns';
      container.innerHTML = `<div class="alert alert-danger">❌ Error: ${esc(err.message)}</div>`;
    });
}

function addDetectedPattern(merchant, category, amount, frequency, nextDue) {
  document.getElementById('recMerchant').value = merchant;
  document.getElementById('recCategory').value = category;
  document.getElementById('recAmount').value = amount;
  document.getElementById('recFrequency').value = frequency;

  const today = new Date().toISOString().split('T')[0];
  document.getElementById('recStartDate').value = today;

  if (nextDue) {
    document.getElementById('recNextDue').value = nextDue.split('T')[0];
  }

  document.getElementById('recurringForm').dispatchEvent(new Event('submit'));
}

// Form submission
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('recurringForm');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      const data = {
        merchant: document.getElementById('recMerchant').value,
        category: document.getElementById('recCategory').value,
        amount: parseFloat(document.getElementById('recAmount').value),
        frequency: document.getElementById('recFrequency').value,
        start_date: document.getElementById('recStartDate').value,
        next_due_date: document.getElementById('recNextDue').value,
        end_date: document.getElementById('recEndDate').value || null,
        auto_add: document.getElementById('recAutoAdd').checked,
      };

      if (!data.amount || !data.start_date || !data.next_due_date) {
        alert(
          'Please fill in all required fields (Amount, Start Date, Next Due)',
        );
        return;
      }

      const submitBtn = form.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.textContent = '⏳ Adding...';

      fetch('/api/recurring/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            alert('✅ Recurring expense added successfully!');
            form.reset();
            // Set default date
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('recStartDate').value = today;
            document.getElementById('recNextDue').value = today;
            loadRecurring();
          } else {
            alert('❌ Error: ' + data.error);
          }
        })
        .catch((err) => alert('❌ Error: ' + err.message))
        .finally(() => {
          submitBtn.disabled = false;
          submitBtn.textContent = '➕ Add Recurring Expense';
        });
    });
  }

  // Set default dates
  const today = new Date().toISOString().split('T')[0];
  const startDateInput = document.getElementById('recStartDate');
  const nextDueInput = document.getElementById('recNextDue');
  if (startDateInput) startDateInput.value = today;
  if (nextDueInput) nextDueInput.value = today;

  // Load recurring expenses on page load
  loadRecurring();
});

function toggleRecurring(id) {
  fetch(`/api/recurring/toggle/${id}`, {
    method: 'POST',
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        loadRecurring();
      } else {
        alert('Error: ' + data.error);
      }
    })
    .catch((err) => alert('Error: ' + err.message));
}

function deleteRecurring(id) {
  if (!confirm('Delete this recurring expense?')) return;

  fetch(`/api/recurring/delete/${id}`, {
    method: 'DELETE',
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        loadRecurring();
      } else {
        alert('Error: ' + data.error);
      }
    })
    .catch((err) => alert('Error: ' + err.message));
}
