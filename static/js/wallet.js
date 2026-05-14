/* Wallet Page JavaScript (extracted from wallet.html) */

var walletState = {
    wallet: null,
    subscription: null,
    plans: {}
};

async function loadWalletDashboard() {
    try {
        const response = await fetch('/api/user/wallet', { credentials: 'same-origin' });
        // 401/403 handled globally by base_theme.js
        if (!response.ok) return;

        const data = await response.json();
        if (!data.success) {
            showNotification(data.message || 'Could not load wallet data', 'error');
            return;
        }
        walletState.wallet = data.wallet;
        walletState.subscription = data.subscription;
        walletState.plans = data.plans || {};
        walletState.transactions = data.transactions || [];
        renderWalletDashboard();
    } catch (error) {
        if (!error.message.includes('JSON')) {
            showNotification('Error loading data: ' + error.message, 'error');
        }
    }
}

function renderWalletDashboard() {
    const balanceEl = document.getElementById('walletBalance');
    const updatedEl = document.getElementById('walletUpdatedAt');
    const subStatusEl = document.getElementById('subscriptionStatus');
    const subExpiryEl = document.getElementById('subscriptionExpiry');
    const autoToggle = document.getElementById('autoRenewToggle');
    const autoStatus = document.getElementById('autoRenewStatus');

    if (!balanceEl || !updatedEl || !subStatusEl || !subExpiryEl || !autoToggle || !autoStatus) {
        return; // workspace page does not host full wallet controls
    }

    balanceEl.textContent = formatCurrency(walletState.wallet?.balance || 0);
    updatedEl.textContent = walletState.wallet?.updated_at ? `Updated ${walletState.wallet.updated_at}` : '';

    if (walletState.subscription) {
        subStatusEl.textContent = `${walletState.subscription.subscription_type?.toUpperCase()} · ${formatCurrency(walletState.subscription.amount)}`;
        subExpiryEl.textContent = `Expires: ${walletState.subscription.end_date || '-'}`;
        autoToggle.disabled = false;
        autoToggle.checked = walletState.subscription.auto_renew === 1;
        autoStatus.textContent = walletState.subscription.auto_renew ? 'On' : 'Off';
    } else {
        subStatusEl.textContent = 'Not subscribed';
        subExpiryEl.textContent = '—';
        autoToggle.checked = false;
        autoToggle.disabled = true;
        autoStatus.textContent = 'Off';
    }

    renderPlanCards();
    renderTransactions();
}

function renderPlanCards() {
    const grid = document.getElementById('planGrid');
    const activePlan = walletState.subscription?.subscription_type;
    grid.innerHTML = Object.entries(walletState.plans).map(([key, plan]) => `
        <div class="plan-tile ${activePlan === key ? 'active' : ''}">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <strong>${plan.name}</strong>
                <span class="badge bg-light text-dark">${plan.days} days</span>
            </div>
            <div class="plan-price">${formatCurrency(plan.amount)}</div>
            <div class="plan-duration">${plan.description}</div>
            <div class="plan-actions">
                <button class="btn btn-sm btn-primary" onclick="upgradePlan('${key}')">
                    <i class="fas fa-level-up-alt"></i> Upgrade
                </button>
            </div>
        </div>
    `).join('');
}

function localizeStatus(status) {
    const s = String(status || '').toLowerCase();
    switch (s) {
        case 'pending':
            return { label: 'Pending', cls: 'bg-warning text-dark' };
        case 'completed':
            return { label: 'Completed', cls: 'bg-success' };
        case 'rejected':
            return { label: 'Rejected', cls: 'bg-danger' };
        case 'expired':
            return { label: 'Expired', cls: 'bg-secondary' };
        default:
            return { label: status || '—', cls: 'bg-light text-dark' };
    }
}

function renderTransactions() {
    const tbody = document.getElementById('txnTableBody');
    const countEl = document.getElementById('txnCount');
    if (!walletState.transactions || !walletState.transactions.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No transactions</td></tr>';
        countEl.textContent = '0 transactions';
        return;
    }
    countEl.textContent = `${walletState.transactions.length} transactions`;
    tbody.innerHTML = walletState.transactions.map(txn => {
        const st = localizeStatus(txn.status);
        const typeLabel = (txn.type || '').toLowerCase() === 'topup' ? 'Top up' : (txn.type || '—');
        return `
        <tr>
            <td><span class="badge bg-dark">TX-${txn.id}</span><br><small>${txn.created_at}</small></td>
            <td>${formatCurrency(txn.amount)}</td>
            <td>${typeLabel}</td>
            <td><span class="badge ${st.cls}">${st.label}</span></td>
        </tr>
    `}).join('');
}

function openTopupModal() {
    new bootstrap.Modal(document.getElementById('topupModal')).show();
}

async function submitTopup() {
    const amount = parseInt(document.getElementById('topupAmount').value || '0');
    const method = document.getElementById('topupMethod').value;
    const reference = document.getElementById('topupReference').value.trim();

    if (amount < 50000) {
        showNotification('Please enter a minimum amount of 50,000 VND', 'error');
        return;
    }

    try {
        const response = await fetch('/api/user/wallet/topup', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ amount, method, reference }),
            credentials: 'same-origin'
        });
        // 401/403 handled globally
        if (!response.ok) return;

        const data = await response.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('topupModal')).hide();
            showNotification(data.message || 'Top-up request submitted. Admin will confirm shortly.', 'success');
            loadWalletDashboard();
        } else {
            showNotification(data.message || 'Unable to submit request', 'error');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

async function upgradePlan(planKey) {
    const plan = walletState.plans[planKey];
    if (!plan) {
        showNotification('Invalid plan', 'error');
        return;
    }
    if (!confirm(`Confirm charge of ${formatCurrency(plan.amount)} to upgrade to ${plan.name}?`)) return;
    try {
        const response = await fetch('/api/user/subscription/upgrade', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ plan: planKey }),
            credentials: 'same-origin'
        });
        // 401/403 handled globally
        if (!response.ok) return;

        const data = await response.json();
        if (data.success) {
            showNotification(data.message || 'Upgrade successful!', 'success');
            loadWalletDashboard();
        } else {
            showNotification(data.message || 'Unable to upgrade', 'error');
        }
    } catch (error) {
        showNotification('Upgrade error: ' + error.message, 'error');
    }
}

async function toggleAutoRenew(isEnabled) {
    if (!walletState.subscription) return;
    try {
        const response = await fetch('/api/user/subscription/auto-renew', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ enabled: isEnabled }),
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            document.getElementById('autoRenewToggle').checked = !isEnabled;
            return;
        }

        const data = await response.json();
        if (data.success) {
            showNotification(data.message || 'Auto-renew updated', 'success');
            loadWalletDashboard();
        } else {
            showNotification(data.message || 'Unable to update', 'error');
            document.getElementById('autoRenewToggle').checked = !isEnabled;
        }
    } catch (error) {
        document.getElementById('autoRenewToggle').checked = !isEnabled;
        showNotification('Error: ' + error.message, 'error');
    }
}

function formatCurrency(amount) {
    return (amount || 0).toLocaleString('en-US', { style: 'currency', currency: 'VND' });
}

// Polling to refresh
window.addEventListener('DOMContentLoaded', () => {
    const hasWalletDashboard = document.getElementById('walletBalance');
    if (hasWalletDashboard) {
        loadWalletDashboard();
        setInterval(loadWalletDashboard, 15000);
    }
    // If workspace contains a glance widget, initialize it too
    if (document.getElementById('walletGlanceSection')) {
        initWalletGlance();
        setInterval(initWalletGlance, 15000);
    }
});

async function initWalletGlance() {
    try {
        const resp = await fetch('/api/user/wallet', { credentials: 'same-origin' });
        // 401/403 handled globally
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;
        const w = data.wallet || {};
        const s = data.subscription || null;
        const balanceEl = document.getElementById('glanceBalance');
        const planEl = document.getElementById('glancePlan');
        const expiryEl = document.getElementById('glanceExpiry');
        const updatedEl = document.getElementById('glanceUpdatedAt');
        const renewEl = document.getElementById('glanceRenew');
        const statusEl = document.getElementById('glanceStatus');
        if (balanceEl) balanceEl.textContent = formatCurrency(w.balance || 0);
        if (planEl) planEl.textContent = s ? s.subscription_type : 'Not upgraded';
        if (expiryEl) expiryEl.textContent = s ? (s.end_date || '—') : '—';
        if (updatedEl) updatedEl.textContent = w.updated_at ? `Updated ${w.updated_at}` : '';
        if (renewEl) renewEl.textContent = s ? (s.auto_renew ? 'Auto renew: On' : 'Auto renew: Off') : 'Auto renew: —';
        if (statusEl && s) statusEl.textContent = s.status || '—';
    } catch (e) {
        // ignore; optional
    }
}

// Expose some helper functions on window for event handlers
window.openTopupModal = openTopupModal;
window.submitTopup = submitTopup;
window.upgradePlan = upgradePlan;
window.toggleAutoRenew = toggleAutoRenew;
window.loadWalletDashboard = loadWalletDashboard;

// Admin withdraw functions
function openWithdrawModal() {
    const modal = new bootstrap.Modal(document.getElementById('withdrawModal'));
    const balance = walletState.wallet?.balance || 0;
    document.getElementById('withdrawAvailableBalance').textContent = formatCurrency(balance);
    modal.show();
}

async function submitWithdraw() {
    const amount = parseInt(document.getElementById('withdrawAmount').value);
    const bankName = document.getElementById('withdrawBankName').value.trim();
    const accountNumber = document.getElementById('withdrawAccountNumber').value.trim();
    const accountName = document.getElementById('withdrawAccountName').value.trim();
    const note = document.getElementById('withdrawNote').value.trim();

    if (!amount || amount < 100000) {
        showNotification('Minimum withdrawal amount is 100,000 VND', 'error');
        return;
    }

    if (!bankName || !accountNumber || !accountName) {
        showNotification('Please provide complete bank information', 'error');
        return;
    }

    const balance = walletState.wallet?.balance || 0;
    if (amount > balance) {
        showNotification('Insufficient balance for withdrawal', 'error');
        return;
    }

    try {
        const response = await fetch('/api/admin/wallet/withdraw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({
                amount,
                bank_name: bankName,
                account_number: accountNumber,
                account_name: accountName,
                note
            })
        });

        const data = await response.json();
        if (data.success) {
            showNotification('Withdrawal request submitted successfully! Funds will be transferred in 1-2 business days.', 'success');
            bootstrap.Modal.getInstance(document.getElementById('withdrawModal')).hide();
            loadWalletDashboard();
        } else {
            showNotification(data.message || 'Unable to withdraw funds', 'error');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

window.openWithdrawModal = openWithdrawModal;
window.submitWithdraw = submitWithdraw;
