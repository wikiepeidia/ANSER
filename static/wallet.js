/* Wallet Page JavaScript (extracted from wallet.html) */

let walletState = {
    wallet: null,
    subscription: null,
    plans: {}
};

async function loadWalletDashboard() {
    try {
        const response = await fetch('/api/user/wallet', { credentials: 'same-origin' });
            // If not authenticated, server will return 401/403 with JSON; handle proactively
            if (response.status === 401 || response.status === 403) {
                showNotification('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error');
                return;
            }
        const data = await response.json();
        if (!data.success) {
            showNotification(data.message || 'Không thể tải dữ liệu ví', 'error');
            return;
        }
        walletState.wallet = data.wallet;
        walletState.subscription = data.subscription;
        walletState.plans = data.plans || {};
        walletState.transactions = data.transactions || [];
        renderWalletDashboard();
    } catch (error) {
        if (error.message.includes('JSON')) {
            showNotification('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error');
        } else {
            showNotification('Lỗi tải dữ liệu: ' + error.message, 'error');
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

    balanceEl.textContent = formatCurrency(walletState.wallet?.balance || 0);
    updatedEl.textContent = walletState.wallet?.updated_at ? `Cập nhật ${walletState.wallet.updated_at}` : '';

    if (walletState.subscription) {
        subStatusEl.textContent = `${walletState.subscription.subscription_type?.toUpperCase()} · ${formatCurrency(walletState.subscription.amount)}`;
        subExpiryEl.textContent = `Hết hạn: ${walletState.subscription.end_date || '-'}`;
        autoToggle.disabled = false;
        autoToggle.checked = walletState.subscription.auto_renew === 1;
        autoStatus.textContent = walletState.subscription.auto_renew ? 'Bật' : 'Tắt';
    } else {
        subStatusEl.textContent = 'Chưa đăng ký';
        subExpiryEl.textContent = '—';
        autoToggle.checked = false;
        autoToggle.disabled = true;
        autoStatus.textContent = 'Tắt';
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
                <span class="badge bg-light text-dark">${plan.days} ngày</span>
            </div>
            <div class="plan-price">${formatCurrency(plan.amount)}</div>
            <div class="plan-duration">${plan.description}</div>
            <div class="plan-actions">
                <button class="btn btn-sm btn-primary" onclick="upgradePlan('${key}')">
                    <i class="fas fa-level-up-alt"></i> Nâng cấp
                </button>
            </div>
        </div>
    `).join('');
}

function localizeStatus(status) {
    const s = String(status || '').toLowerCase();
    switch (s) {
        case 'pending':
            return { label: 'Đang chờ', cls: 'bg-warning text-dark' };
        case 'completed':
            return { label: 'Hoàn thành', cls: 'bg-success' };
        case 'rejected':
            return { label: 'Đã từ chối', cls: 'bg-danger' };
        case 'expired':
            return { label: 'Hết hạn', cls: 'bg-secondary' };
        default:
            return { label: status || '—', cls: 'bg-light text-dark' };
    }
}

function renderTransactions() {
    const tbody = document.getElementById('txnTableBody');
    const countEl = document.getElementById('txnCount');
    if (!walletState.transactions || !walletState.transactions.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Chưa có giao dịch</td></tr>';
        countEl.textContent = '0 giao dịch';
        return;
    }
    countEl.textContent = `${walletState.transactions.length} giao dịch`;
    tbody.innerHTML = walletState.transactions.map(txn => {
        const st = localizeStatus(txn.status);
        const typeLabel = (txn.type || '').toLowerCase() === 'topup' ? 'Nạp ví' : (txn.type || '—');
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
    const amount = parseFloat(document.getElementById('topupAmount').value || '0');
    const method = document.getElementById('topupMethod').value;
    const reference = document.getElementById('topupReference').value.trim();

    if (amount < 50000) {
        showNotification('Vui lòng nhập số tiền tối thiểu 50.000đ', 'error');
        return;
    }

    try {
        const response = await fetch('/api/user/wallet/topup', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ amount, method, reference }),
            credentials: 'same-origin'
        });
        if (response.status === 401 || response.status === 403) {
            showNotification('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error');
            setTimeout(() => { window.location.href = '/auth/signin'; }, 3000);
            return;
        }
        const data = await response.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('topupModal')).hide();
            showNotification(data.message || 'Đã gửi yêu cầu nạp tiền. Admin sẽ xác nhận sớm nhất.', 'success');
            loadWalletDashboard();
        } else {
            showNotification(data.message || 'Không thể gửi yêu cầu', 'error');
        }
    } catch (error) {
        showNotification('Lỗi: ' + error.message, 'error');
    }
}

async function upgradePlan(planKey) {
    const plan = walletState.plans[planKey];
    if (!plan) {
        showNotification('Gói không hợp lệ', 'error');
        return;
    }
    if (!confirm(`Xác nhận trừ ${formatCurrency(plan.amount)} để nâng cấp gói ${plan.name}?`)) return;
    try {
        const response = await fetch('/api/user/subscription/upgrade', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ plan: planKey }),
            credentials: 'same-origin'
        });
        if (response.status === 401 || response.status === 403) {
            showNotification('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error');
            setTimeout(() => { window.location.href = '/auth/signin'; }, 3000);
            return;
        }
        const data = await response.json();
        if (data.success) {
            showNotification(data.message || 'Nâng cấp thành công!', 'success');
            loadWalletDashboard();
        } else {
            showNotification(data.message || 'Không thể nâng cấp', 'error');
        }
    } catch (error) {
        showNotification('Lỗi nâng cấp: ' + error.message, 'error');
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
        if (response.status === 401 || response.status === 403) {
            showNotification('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error');
            document.getElementById('autoRenewToggle').checked = !isEnabled;
            setTimeout(() => { window.location.href = '/auth/signin'; }, 3000);
            return;
        }
        const data = await response.json();
        if (data.success) {
            showNotification(data.message || 'Đã cập nhật tự động gia hạn', 'success');
            loadWalletDashboard();
        } else {
            showNotification(data.message || 'Không thể cập nhật', 'error');
            document.getElementById('autoRenewToggle').checked = !isEnabled;
        }
    } catch (error) {
        document.getElementById('autoRenewToggle').checked = !isEnabled;
        showNotification('Lỗi: ' + error.message, 'error');
    }
}

function formatCurrency(amount) {
    return (amount || 0).toLocaleString('vi-VN', { style: 'currency', currency: 'VND' });
}

// Polling to refresh
window.addEventListener('DOMContentLoaded', () => {
    loadWalletDashboard();
    setInterval(loadWalletDashboard, 15000);
    // If workspace contains a glance widget, initialize it too
    if (document.getElementById('walletGlanceSection')) {
        initWalletGlance();
        setInterval(initWalletGlance, 15000);
    }
});

async function initWalletGlance() {
    try {
        const resp = await fetch('/api/user/wallet', { credentials: 'same-origin' });
        if (resp.status === 401 || resp.status === 403) return;
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
        if (planEl) planEl.textContent = s ? s.subscription_type : 'Chưa nâng cấp';
        if (expiryEl) expiryEl.textContent = s ? (s.end_date || '—') : '—';
        if (updatedEl) updatedEl.textContent = w.updated_at ? `Cập nhật ${w.updated_at}` : '';
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

