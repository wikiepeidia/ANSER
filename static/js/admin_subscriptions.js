async function loadSubscriptions() {
    try {
        const response = await fetch('/api/admin/subscriptions', { credentials: 'same-origin' });
        // 401/403 handled globally
        if (!response.ok) return;

        const data = await response.json();
        renderSubscriptionsTable(data.subscriptions || []);
        } catch (error) {
        if (!error.message.includes('JSON')) {
            showAlert('error', 'Error loading list: ' + error.message);
        }
    }
}

async function loadPaymentHistory() {
    try {
        const response = await fetch('/api/admin/subscription-history', { credentials: 'same-origin' });
        // 401/403 handled globally
        if (!response.ok) return;

        const data = await response.json();
        renderPaymentHistory(data.history || []);
    } catch (error) {
        if (!error.message.includes('JSON')) {
            console.error('Error loading payment history:', error);
        }
    }
}

function renderSubscriptionsTable(subscriptions) {
    const tbody = document.getElementById('subscriptionsTable');

    if (subscriptions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No managers found</td></tr>';
        return;
    }

    tbody.innerHTML = subscriptions
        .map((sub) => {
            const endDate = new Date(sub.end_date);
            const now = new Date();
            const daysLeft = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));

            let statusBadge = '';
            if (sub.status === 'expired') {
                statusBadge = '<span class="badge badge-expired">Expired</span>';
            } else if (daysLeft <= 7) {
                statusBadge = `<span class="badge badge-expiring">Expires in ${daysLeft} days</span>`;
            } else {
                statusBadge = `<span class="badge bg-success">Active (${daysLeft} days)</span>`;
            }

            const planNames = {
                trial: 'Trial',
                monthly: 'Monthly',
                quarterly: 'Quarterly',
                yearly: 'Yearly',
            };
            
            // Auto-renew toggle
            const autoRenew = sub.auto_renew || false;
            const toggleChecked = autoRenew ? 'checked' : '';
            const toggleClass = autoRenew ? 'bg-success' : 'bg-secondary';

            return `
            <tr>
                <td><strong>${sub.user_name}</strong></td>
                <td>${sub.user_email}</td>
                <td><span class="badge bg-primary">${planNames[sub.subscription_type] || sub.subscription_type}</span></td>
                <td>${new Date(sub.start_date).toLocaleDateString('en-US')}</td>
                <td>${endDate.toLocaleDateString('en-US')}</td>
                <td>${statusBadge}</td>
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" id="autoRenew${sub.user_id}" ${toggleChecked} 
                               onchange="toggleAutoRenew(${sub.user_id}, this.checked)">
                        <label class="form-check-label" for="autoRenew${sub.user_id}">
                            <span class="badge ${toggleClass}">${autoRenew ? 'ON' : 'OFF'}</span>
                        </label>
                    </div>
                </td>
                <td>
                    <button class="btn btn-sm btn-success" onclick="openExtendModal(${sub.user_id}, '${sub.user_name.replace(/'/g, "&apos;")}')">
                        <i class="fas fa-plus"></i> Extend
                    </button>
                </td>
            </tr>
        `;
        })
        .join('');
}

function renderPaymentHistory(history) {
    const tbody = document.getElementById('paymentHistoryTable');

    if (history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No payment history</td></tr>';
        return;
    }

    tbody.innerHTML = history
        .slice(0, 10)
        .map((payment) => {
            const planNames = {
                trial: 'Trial',
                monthly: 'Monthly',
                quarterly: 'Quarterly',
                yearly: 'Yearly',
            };

            return `
            <tr>
                <td>${new Date(payment.payment_date).toLocaleDateString('en-US')}</td>
                <td>${payment.user_name}</td>
                <td>${planNames[payment.subscription_type] || payment.subscription_type}</td>
                <td><strong>${payment.amount.toLocaleString('en-US')} VND</strong></td>
                <td>${payment.payment_method || 'N/A'}</td>
                <td><span class="badge ${localizeStatus(payment.status).cls}">${localizeStatus(payment.status).label}</span></td>
            </tr>
        `;
        })
        .join('');
}

function openExtendModal(userId, userName) {
    document.getElementById('extendUserId').value = userId;
    document.getElementById('extendUserName').value = userName;
    new bootstrap.Modal(document.getElementById('extendModal')).show();
}

async function processExtension() {
    const userId = document.getElementById('extendUserId').value;
    const plan = document.getElementById('extendPlan').value;
    const paymentMethod = document.getElementById('paymentMethod').value;
    const transactionId = document.getElementById('transactionId').value;

    try {
        const response = await fetch('/api/admin/extend-subscription', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: parseInt(userId, 10),
                subscription_type: plan,
                payment_method: paymentMethod,
                transaction_id: transactionId,
            }),
        });

        // 401/403 handled globally
        if (!response.ok) return;

        const data = await response.json();

            if (data.success) {
            showAlert('success', '✅ Extension successful!');
            bootstrap.Modal.getInstance(document.getElementById('extendModal')).hide();
            loadSubscriptions();
            loadPaymentHistory();
        } else {
            showAlert('error', data.message || 'Unable to extend subscription');
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
    }
}

async function checkExpiredSubscriptions() {
    if (!confirm('Are you sure you want to check and demote expired Managers?')) return;

    try {
        const response = await fetch('/api/admin/check-expired-subscriptions', {
            method: 'POST',
        });
        // 401/403 handled globally
        if (!response.ok) return;

        const data = await response.json();

        if (data.success) {
            showAlert('success', `✅ Demoted ${data.demoted_count} expired Manager(s)!`);
            loadSubscriptions();
        } else {
            showAlert('error', data.message || 'Failed to check expirations');
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
    }
}

// Use global showNotification if available (from static/script.js), otherwise fallback to element creation
function showAlert(type, message) {
    if (typeof showNotification === 'function') {
        const t = (type === 'success') ? 'success' : (type === 'warning' ? 'warning' : (type === 'info' ? 'info' : 'error'));
        showNotification(message, t);
        return;
    }
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
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

document.addEventListener('DOMContentLoaded', () => {
    loadSubscriptions();
    loadPaymentHistory();
    // Load pending wallet transactions for admin review (if table exists on this page)
    if (document.getElementById('pendingPaymentsTable')) {
        loadPendingPayments();
    }
});

const automationSettings = { autoUpgrade: true, autoNotify: true, bankLinked: false };
let pendingPayments = [];

function initAutomationUI() {
    const autoToggle = document.getElementById('autoUpgradeToggle');
    const notifyToggle = document.getElementById('autoNotifyToggle');
    const statusLabel = document.getElementById('autoUpgradeStatus');
    const ownerLabel = document.getElementById('ownerAlertStatus');
    if (!autoToggle || !notifyToggle || !statusLabel || !ownerLabel) return;
    autoToggle.checked = automationSettings.autoUpgrade;
    notifyToggle.checked = automationSettings.autoNotify;
    statusLabel.textContent = automationSettings.autoUpgrade ? 'Enabled' : 'Disabled';
    ownerLabel.textContent = automationSettings.autoNotify ? 'Enabled' : 'Disabled';
    updateBankStatus();
}

function updateBankStatus() {
    const bankLabel = document.getElementById('bankLinkStatus');
    const receiptInfo = document.getElementById('receiptInfo');
    if (bankLabel) bankLabel.textContent = automationSettings.bankLinked ? 'Bank linked' : 'Not connected';
    if (receiptInfo) receiptInfo.textContent = automationSettings.bankLinked ? 'Automatically attach statements' : 'Waiting for bank connection';
}

function linkBankAccount() {
    automationSettings.bankLinked = true;
    updateBankStatus();
    showAlert('success', 'Bank linked successfully');
}

function toggleAutoUpgrade(isOn) {
    automationSettings.autoUpgrade = isOn;
    const statusLabel = document.getElementById('autoUpgradeStatus');
    if (statusLabel) statusLabel.textContent = isOn ? 'Enabled' : 'Disabled';
    const healthBadge = document.getElementById('automationHealth');
    if (healthBadge) {
        healthBadge.textContent = isOn ? 'ON' : 'PAUSED';
        healthBadge.classList.toggle('bg-danger', !isOn);
        healthBadge.classList.toggle('bg-success', isOn);
    }
    showAlert('success', isOn ? 'Auto-upgrade enabled' : 'Auto-upgrade disabled');
}

function toggleOwnerNotify(isOn) {
    automationSettings.autoNotify = isOn;
    const ownerLabel = document.getElementById('ownerAlertStatus');
    if (ownerLabel) ownerLabel.textContent = isOn ? 'Enabled' : 'Disabled';
    showAlert('success', isOn ? 'Owner notifications enabled' : 'Owner notifications disabled');
}

function refreshPaymentQueue() { loadPendingPayments(true); }

function triggerManualPayout() { showAlert('success', 'Reconciliation request sent to bank'); }

document.addEventListener('DOMContentLoaded', () => { initAutomationUI(); });

async function loadPendingPayments(showToastMessage = false) {
    const tbody = document.querySelector('#pendingPaymentsTable tbody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div></td></tr>';
    }
    try {
        const response = await fetch('/api/admin/wallet/pending', { credentials: 'same-origin' });
        if (!response.ok) {
            if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Access denied</td></tr>';
            return;
        }
        const data = await response.json();
        if (!data.success) throw new Error(data.message || 'Failed to load pending payments');
        const transactions = data.history || []; // Fixed: API returns 'history' not 'transactions'
        if (!tbody) return;
            if (!transactions.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No pending transactions</td></tr>';
            return;
        }
        tbody.innerHTML = transactions.map(payment => {
            const planLabel = payment.plan_label ? String(payment.plan_label).toUpperCase() : (payment.type === 'topup' ? 'TOPUP' : (payment.type || '—'));
            const methodLabel = payment.method || '—';
            const createdAt = payment.created_at ? `<br><small class="text-muted">${payment.created_at}</small>` : '';
            const reference = payment.reference ? `<br><small class="text-muted">Ref: ${payment.reference}</small>` : '';
            const statusObj = localizeStatus(payment.status);
            return `
                <tr>
                    <td><span class="badge bg-dark">TX-${payment.id}</span>${createdAt}</td>
                    <td><strong>${payment.user_name}</strong><br><small>${payment.user_email}</small></td>
                    <td><span class="badge bg-primary">${planLabel}</span></td>
                    <td>${(payment.amount || 0).toLocaleString('en-US')} VND</td>
                    <td>${methodLabel}${reference}</td>
                    <td class="text-end">
                        <span class="me-2"><span class="badge ${statusObj.cls}">${statusObj.label}</span></span>
                        <button class="btn btn-sm btn-success me-2" onclick="processQueuedPayment(${payment.id}, 'approve')"><i class="fas fa-check"></i></button>
                        <button class="btn btn-sm btn-outline-danger" onclick="processQueuedPayment(${payment.id}, 'reject')"><i class="fas fa-times"></i></button>
                    </td>
                </tr>
            `;
        }).join('');
        if (showToastMessage) showAlert('success', 'Loaded pending transactions.');
    } catch (error) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Unable to load transactions</td></tr>';
        if (!error.message.includes('JSON')) {
            showAlert('error', 'Error: ' + error.message);
        }
    }
}

async function processQueuedPayment(paymentId, action) {
    try {
        const response = await fetch(`/api/admin/wallet/pending/${paymentId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ action })
        });
        // 401/403 handled globally
        if (!response.ok) return;

        const data = await response.json();
        if (data.success) {
            showAlert('success', data.message || 'Transaction processed');
            await loadPendingPayments();
            // Update subscription/account summaries
            loadSubscriptions();
            loadPaymentHistory();
        } else {
            showAlert('error', data.message || 'Unable to process transaction');
        }
    } catch (error) {
            showAlert('error', 'Error: ' + error.message);
    }
}

// Toggle auto-renew subscription
async function toggleAutoRenew(userId, enabled) {
    try {
        const response = await fetch('/api/admin/subscription/auto-renew', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, auto_renew: enabled }),
            credentials: 'same-origin'
        });

        if (response.status === 401 || response.status === 403) {
            showAlert('error', 'Session expired. Please log in again.');
            return;
        }
        
        if (!response.ok) {
            document.getElementById(`autoRenew${userId}`).checked = !enabled;
            return;
        }

        const data = await response.json();
        if (data.success) {
            showAlert('success', enabled ? 'Auto renew enabled' : 'Auto renew disabled');
            // Reload to update badge
            loadSubscriptions();
        } else {
            showAlert('error', data.message || 'Unable to update');
            // Revert checkbox
            document.getElementById(`autoRenew${userId}`).checked = !enabled;
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
        // Revert checkbox
        document.getElementById(`autoRenew${userId}`).checked = !enabled;
    }
}
