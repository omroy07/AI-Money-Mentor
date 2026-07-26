// Group Expenses — frontend logic
let currentGroupId = null;
let currentGroupData = null;
let currentSplitType = 'EQUAL';
let currentUserId = null;

// Detect current user ID from session
fetch('/api/user/me')
  .then((r) => (r.ok ? r.json() : null))
  .then((d) => {
    if (d && d.user) currentUserId = d.user.id;
  })
  .catch(() => {});

document.addEventListener('DOMContentLoaded', loadGroups);

// ── Toast ──
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  setTimeout(() => {
    t.style.display = 'none';
  }, 3000);
}

// ── Modal helpers ──
function closeModal(id) {
  document.getElementById(id).style.display = 'none';
}

function openModal(id) {
  document.getElementById(id).style.display = 'flex';
}

function showCreateGroupModal() {
  document.getElementById('groupName').value = '';
  document.getElementById('groupDesc').value = '';
  document.getElementById('groupCurrency').value = 'INR';
  openModal('createGroupModal');
}

function showAddExpenseModal() {
  if (!currentGroupData) return;
  document.getElementById('expDescription').value = '';
  document.getElementById('expAmount').value = '';
  document.getElementById('expDate').value = new Date()
    .toISOString()
    .slice(0, 10);
  document.getElementById('expCategory').value = 'Food';
  document.getElementById('expNotes').value = '';
  currentSplitType = 'EQUAL';
  document
    .querySelectorAll('.split-type-btn')
    .forEach((b) => b.classList.toggle('active', b.dataset.type === 'EQUAL'));
  document.getElementById('percentageInputs').style.display = 'none';
  document.getElementById('exactInputs').style.display = 'none';

  // Populate paidBy dropdown
  const sel = document.getElementById('expPaidBy');
  sel.innerHTML = '';
  currentGroupData.members.forEach((m) => {
    const opt = document.createElement('option');
    opt.value = m.user_id;
    opt.textContent = m.nickname || `User ${m.user_id}`;
    if (m.user_id === currentUserId) opt.selected = true;
    sel.appendChild(opt);
  });

  openModal('addExpenseModal');
}

function showAddMemberModal() {
  document.getElementById('memberUserId').value = '';
  document.getElementById('memberNickname').value = '';
  openModal('addMemberModal');
}

function showSettleModal() {
  const sel = document.getElementById('settleTo');
  sel.innerHTML = '';
  currentGroupData.members.forEach((m) => {
    if (m.user_id === currentUserId) return;
    const opt = document.createElement('option');
    opt.value = m.user_id;
    opt.textContent = m.nickname || `User ${m.user_id}`;
    sel.appendChild(opt);
  });
  document.getElementById('settleAmount').value = '';
  document.getElementById('settleNote').value = '';
  openModal('settleModal');
}

// ── Split type toggle ──
function selectSplitType(type) {
  currentSplitType = type;
  document
    .querySelectorAll('.split-type-btn')
    .forEach((b) => b.classList.toggle('active', b.dataset.type === type));
  document.getElementById('percentageInputs').style.display =
    type === 'PERCENTAGE' ? 'block' : 'none';
  document.getElementById('exactInputs').style.display =
    type === 'EXACT' ? 'block' : 'none';

  if (type === 'PERCENTAGE') renderSplitInputs('percentageInputs', '%');
  if (type === 'EXACT') renderSplitInputs('exactInputs', '₹');
}

function renderSplitInputs(containerId, suffix) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';
  if (!currentGroupData) return;
  currentGroupData.members.forEach((m) => {
    const name = m.nickname || `User ${m.user_id}`;
    const row = document.createElement('div');
    row.style.cssText =
      'display:flex;align-items:center;gap:8px;margin-bottom:6px;';
    row.innerHTML = `
      <span style="flex:1;font-size:13px;">${name}</span>
      <input type="number" min="0" step="${suffix === '%' ? '1' : '0.01'}" value="${suffix === '%' ? Math.floor(100 / currentGroupData.members.length) : ''}"
        data-user="${m.user_id}" class="split-input" placeholder="0"
        style="width:80px;padding:6px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);text-align:right;">
      <span style="font-size:12px;color:var(--muted);">${suffix}</span>
    `;
    container.appendChild(row);
  });
}

// ── API calls ──
async function api(url, opts = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// ── Load groups ──
async function loadGroups() {
  try {
    const data = await api('/api/groups');
    renderGroups(data.groups);
  } catch (e) {
    showToast('Failed to load groups');
  }
}

function renderGroups(groups) {
  const grid = document.getElementById('groupsGrid');
  const noGroups = document.getElementById('noGroups');
  if (!groups.length) {
    grid.innerHTML = '';
    noGroups.style.display = 'block';
    return;
  }
  noGroups.style.display = 'none';
  grid.innerHTML = groups
    .map(
      (g) => `
    <div class="card" style="cursor:pointer;transition:transform 0.15s;" onmouseenter="this.style.transform='translateY(-2px)'" onmouseleave="this.style.transform='none'" onclick="openGroup(${g.id})">
      <div style="display:flex;justify-content:space-between;align-items:start;">
        <div>
          <div style="font-size:16px;font-weight:700;">${esc(g.name)}</div>
          <div style="font-size:13px;color:var(--muted);">${esc(g.description || 'No description')}</div>
        </div>
        <div style="font-size:20px;">👥</div>
      </div>
      <div style="display:flex;gap:16px;margin-top:12px;font-size:13px;color:var(--muted);">
        <span>${g.member_count} member${g.member_count !== 1 ? 's' : ''}</span>
        <span>${g.currency}</span>
      </div>
    </div>
  `,
    )
    .join('');
}

// ── Open group detail ──
async function openGroup(groupId) {
  currentGroupId = groupId;
  try {
    const data = await api(`/api/groups/${groupId}`);
    currentGroupData = data;
    renderGroupDetail(data);
    document.getElementById('groupListView').style.display = 'none';
    document.getElementById('groupDetailView').style.display = 'block';
  } catch (e) {
    showToast('Failed to load group');
  }
}

function showGroupList() {
  document.getElementById('groupListView').style.display = 'block';
  document.getElementById('groupDetailView').style.display = 'none';
  currentGroupId = null;
  currentGroupData = null;
  loadGroups();
}

function renderGroupDetail(data) {
  document.getElementById('groupDetailName').textContent = data.group.name;
  document.getElementById('groupDetailDesc').textContent =
    data.group.description || '';
  renderBalances();
  renderExpenses();
}

// ── Balance display ──
async function renderBalances() {
  if (!currentGroupId) return;
  try {
    const data = await api(`/api/groups/${currentGroupId}/balance`);
    const container = document.getElementById('balanceSummary');
    const transfersDiv = document.getElementById('transfersSummary');

    const entries = Object.entries(data.balances);
    if (!entries.length) {
      container.innerHTML =
        '<div style="color:var(--muted);font-size:13px;">No balances yet</div>';
      transfersDiv.innerHTML = '';
      return;
    }

    container.innerHTML = entries
      .map(([name, bal]) => {
        const color =
          bal > 0.01
            ? 'var(--green, #4caf50)'
            : bal < -0.01
              ? 'var(--red, #f44336)'
              : 'var(--muted)';
        const label =
          bal > 0.01 ? 'gets back' : bal < -0.01 ? 'owes' : 'settled';
        return `
        <div style="padding:10px 16px;background:var(--bg);border:1px solid var(--border);border-radius:8px;min-width:140px;">
          <div style="font-size:13px;font-weight:600;">${esc(name)}</div>
          <div style="font-size:15px;font-weight:700;color:${color};">${Math.abs(bal).toFixed(2)}</div>
          <div style="font-size:11px;color:var(--muted);">${label}</div>
        </div>
      `;
      })
      .join('');

    if (data.transfers.length) {
      transfersDiv.innerHTML = `
        <div style="font-size:13px;font-weight:600;margin-bottom:8px;">Suggested Settlements</div>
        ${data.transfers
          .map(
            (t) => `
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:13px;">
            <span style="color:var(--red, #f44336);">${esc(t.from)}</span>
            <span>→</span>
            <span style="color:var(--green, #4caf50);">${esc(t.to)}</span>
            <span style="font-weight:700;margin-left:auto;">${t.amount.toFixed(2)}</span>
          </div>
        `,
          )
          .join('')}
        <button class="btn btn-ghost" onclick="showSettleModal()" style="margin-top:10px;font-size:13px;">Record Settlement</button>
      `;
    } else {
      transfersDiv.innerHTML =
        '<div style="font-size:13px;color:var(--green, #4caf50);margin-top:8px;">All settled!</div>';
    }
  } catch (e) {
    console.error(e);
  }
}

// ── Expense list ──
function renderExpenses() {
  const list = document.getElementById('groupExpensesList');
  const noExp = document.getElementById('noExpenses');
  if (!currentGroupData.expenses.length) {
    list.innerHTML = '';
    noExp.style.display = 'block';
    return;
  }
  noExp.style.display = 'none';

  const memberMap = {};
  currentGroupData.members.forEach((m) => {
    memberMap[m.user_id] = m.nickname || `User ${m.user_id}`;
  });

  list.innerHTML = currentGroupData.expenses
    .map(
      (e) => `
    <div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--border);">
      <div style="font-size:24px;">${categoryIcon(e.category)}</div>
      <div style="flex:1;">
        <div style="font-size:14px;font-weight:600;">${esc(e.description)}</div>
        <div style="font-size:12px;color:var(--muted);">
          Paid by ${esc(memberMap[e.paid_by] || 'Unknown')} · ${e.expense_date} · ${e.split_type}
        </div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:15px;font-weight:700;">${e.amount.toFixed(2)}</div>
        <div style="font-size:11px;color:var(--muted);">${esc(e.category)}</div>
      </div>
    </div>
  `,
    )
    .join('');
}

function categoryIcon(cat) {
  const icons = {
    Food: '🍔',
    Rent: '🏠',
    Travel: '✈️',
    Utilities: '⚡',
    Entertainment: '🎬',
    Shopping: '🛍️',
    Other: '📦',
  };
  return icons[cat] || '📦';
}

// ── Create group ──
document
  .getElementById('createGroupForm')
  .addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/groups', {
        method: 'POST',
        body: JSON.stringify({
          name: document.getElementById('groupName').value,
          description: document.getElementById('groupDesc').value,
          currency: document.getElementById('groupCurrency').value,
        }),
      });
      closeModal('createGroupModal');
      showToast('Group created!');
      loadGroups();
    } catch (err) {
      showToast(err.message);
    }
  });

// ── Add expense ──
document
  .getElementById('addExpenseForm')
  .addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentGroupId) return;

    const body = {
      description: document.getElementById('expDescription').value,
      amount: parseFloat(document.getElementById('expAmount').value),
      category: document.getElementById('expCategory').value,
      paid_by: parseInt(document.getElementById('expPaidBy').value),
      split_type: currentSplitType,
      expense_date: document.getElementById('expDate').value,
      notes: document.getElementById('expNotes').value,
    };

    if (currentSplitType === 'PERCENTAGE') {
      const pcts = {};
      document
        .querySelectorAll('#percentageInputs .split-input')
        .forEach((inp) => {
          pcts[inp.dataset.user] = parseFloat(inp.value) || 0;
        });
      body.percentages = pcts;
    } else if (currentSplitType === 'EXACT') {
      const amounts = {};
      document.querySelectorAll('#exactInputs .split-input').forEach((inp) => {
        amounts[inp.dataset.user] = parseFloat(inp.value) || 0;
      });
      body.exact_amounts = amounts;
    }

    try {
      await api(`/api/groups/${currentGroupId}/expenses`, {
        method: 'POST',
        body: JSON.stringify(body),
      });
      closeModal('addExpenseModal');
      showToast('Expense added!');
      openGroup(currentGroupId);
    } catch (err) {
      showToast(err.message);
    }
  });

// ── Add member ──
document
  .getElementById('addMemberForm')
  .addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!currentGroupId) return;
    try {
      await api(`/api/groups/${currentGroupId}/members`, {
        method: 'POST',
        body: JSON.stringify({
          user_id: parseInt(document.getElementById('memberUserId').value),
          nickname:
            document.getElementById('memberNickname').value || undefined,
        }),
      });
      closeModal('addMemberModal');
      showToast('Member added!');
      openGroup(currentGroupId);
    } catch (err) {
      showToast(err.message);
    }
  });

// ── Settle debt ──
document.getElementById('settleForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!currentGroupId) return;
  try {
    await api(`/api/groups/${currentGroupId}/settle`, {
      method: 'POST',
      body: JSON.stringify({
        to_user_id: parseInt(document.getElementById('settleTo').value),
        amount: parseFloat(document.getElementById('settleAmount').value),
        note: document.getElementById('settleNote').value,
      }),
    });
    closeModal('settleModal');
    showToast('Settlement recorded!');
    openGroup(currentGroupId);
  } catch (err) {
    showToast(err.message);
  }
});

// ── Escape HTML ──
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
