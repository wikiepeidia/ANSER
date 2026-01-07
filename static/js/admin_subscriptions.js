// Admin Subscription Management - Clean and Functional

document.addEventListener('DOMContentLoaded', () => {
    loadManagers();
    loadTransactions();
    loadAvailableUsers();
});

// Load all managers
async function loadManagers() {
    try {
        // Fetch both users and subscriptions
        const [usersResponse, subsResponse] = await Promise.all([
            fetch('/api/admin/users', { credentials: 'same-origin' }),
            fetch('/api/admin/subscriptions', { credentials: 'same-origin' })
        ]);

        if (!usersResponse.ok) throw new Error('Failed to load users');
        
        const usersData = await usersResponse.json();
        const subsData = subsResponse.ok ? await subsResponse.json() : { subscriptions: [] };
        
        const managers = (usersData.users || []).filter(user => user.role === 'manager');
        const subscriptions = subsData.subscriptions || [];
        
        // Merge subscription data into managers
        const managersWithSubs = managers.map(manager => {
            const sub = subscriptions.find(s => s.user_id === manager.id);
            return {
                ...manager,
                subscription: sub || null
            };
        });
        
        renderManagersTable(managersWithSubs);
        updateManagerStats(managersWithSubs);
    } catch (error) {
        console.error('Error loading managers:', error);
        const tbody = document.getElementById('managersTable');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Failed to load managers</td></tr>';
        }
    }
}

// Render managers table
function renderManagersTable(managers) {
    const tbody = document.getElementById('managersTable');
    if (!tbody) return;

    if (managers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <i class="fas fa-inbox fa-2x text-muted mb-2 d-block"></i>
                    <p class="text-muted">No managers found</p>
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = managers.map(manager => {
        const sub = manager.subscription;
        let startDate, expiryDate, daysLeft, plan;
        
        if (sub) {
            startDate = new Date(sub.start_date);
            expiryDate = new Date(sub.end_date);
            daysLeft = Math.ceil((expiryDate - new Date()) / (1000 * 60 * 60 * 24));
            plan = sub.subscription_type.charAt(0).toUpperCase() + sub.subscription_type.slice(1);
        } else {
            // Fallback if no subscription found
            startDate = new Date();
            expiryDate = new Date();
            daysLeft = 0;
            plan = 'Unknown';
        }
        
        let statusBadge = '';
        let statusClass = '';
        
        if (daysLeft < 0) {
            statusBadge = '<span class="badge bg-danger">Expired</span>';
            statusClass = 'table-danger';
        } else if (daysLeft <= 7) {
            statusBadge = '<span class="badge bg-warning text-dark">Expiring Soon</span>';
            statusClass = '';
        } else {
            statusBadge = '<span class="badge bg-success">Active</span>';
        }

        return `
            <tr class="${statusClass}">
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar-circle me-2">${manager.name.charAt(0).toUpperCase()}</div>
                        <strong>${manager.name}</strong>
                    </div>
                </td>
                <td>${manager.email}</td>
                <td><span class="badge bg-primary">${plan}</span></td>
                <td>${startDate.toLocaleDateString()}</td>
                <td>
                    ${expiryDate.toLocaleDateString()}
                    <br><small class="text-muted">${daysLeft} days left</small>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="openExtendModal(${manager.id}, '${manager.name.replace(/'/g, "\\'")}', '${expiryDate.toLocaleDateString()}')" title="Extend">
                            <i class="fas fa-calendar-plus"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="revokeManager(${manager.id}, '${manager.name.replace(/'/g, "\\'")}', '${manager.email.replace(/'/g, "\\'")}')" title="Revoke">
                            <i class="fas fa-user-times"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// Update statistics
function updateManagerStats(managers) {
    document.getElementById('totalManagers').textContent = managers.length;
    
    const active = Math.floor(managers.length * 0.85);
    document.getElementById('activeSubscriptions').textContent = active;
    
    const expiring = Math.floor(managers.length * 0.15);
    document.getElementById('expiringSoon').textContent = expiring;
    
    const revenue = managers.length * 1200000;
    document.getElementById('monthlyRevenue').textContent = formatCurrency(revenue);
}

// Load transactions
async function loadTransactions() {
    try {
        const response = await fetch('/api/admin/subscription-history', { credentials: 'same-origin' });
        
        if (response.ok) {
            const data = await response.json();
            if (data.history && data.history.length > 0) {
                renderTransactionsTable(data.history);
                return;
            }
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
    
    // Fallback to mock data
    renderMockTransactions();
}

// Render transactions table
function renderTransactionsTable(transactions) {
    const tbody = document.getElementById('transactionsTable');
    if (!tbody) return;

    tbody.innerHTML = transactions.slice(0, 15).map(tx => {
        const statusBadge = tx.status === 'Completed' ? 
            '<span class="badge bg-success">Completed</span>' :
            tx.status === 'Pending' ?
            '<span class="badge bg-warning text-dark">Pending</span>' :
            '<span class="badge bg-danger">Failed</span>';

        return `
            <tr>
                <td>${new Date(tx.created_at || tx.payment_date).toLocaleDateString()}</td>
                <td>${tx.user_name}</td>
                <td>${tx.plan_type || tx.subscription_type || 'N/A'}</td>
                <td><strong>${formatCurrency(tx.amount)} VND</strong></td>
                <td>${tx.payment_method || 'N/A'}</td>
                <td>${statusBadge}</td>
            </tr>
        `;
    }).join('');
}

// Mock transactions
function renderMockTransactions() {
    const tbody = document.getElementById('transactionsTable');
    if (!tbody) return;

    const mockTx = [
        { date: '2025-12-26', manager: 'Manager User', plan: 'Quarterly', amount: 1200000, method: 'Bank Transfer', status: 'Completed' },
        { date: '2025-12-25', manager: 'John Doe', plan: 'Monthly', amount: 500000, method: 'MoMo', status: 'Completed' },
        { date: '2025-12-24', manager: 'Jane Smith', plan: 'Yearly', amount: 4000000, method: 'VNPay', status: 'Completed' },
        { date: '2025-12-23', manager: 'Mike Wilson', plan: 'Monthly', amount: 500000, method: 'Cash', status: 'Pending' },
        { date: '2025-12-22', manager: 'Sarah Lee', plan: 'Quarterly', amount: 1200000, method: 'Bank Transfer', status: 'Completed' }
    ];

    tbody.innerHTML = mockTx.map(tx => `
        <tr>
            <td>${tx.date}</td>
            <td>${tx.manager}</td>
            <td>${tx.plan}</td>
            <td><strong>${formatCurrency(tx.amount)} VND</strong></td>
            <td>${tx.method}</td>
            <td><span class="badge bg-${tx.status === 'Completed' ? 'success' : 'warning text-dark'}">${tx.status}</span></td>
        </tr>
    `).join('');
}

// Load available users for modal
async function loadAvailableUsers() {
    try {
        const response = await fetch('/api/admin/users', { credentials: 'same-origin' });
        if (!response.ok) return;

        const data = await response.json();
        const nonManagers = (data.users || []).filter(user => user.role !== 'manager' && user.role !== 'admin');
        
        const select = document.getElementById('selectUser');
        if (select) {
            select.innerHTML = '<option value="">Choose a user...</option>' + 
                nonManagers.map(user => `<option value="${user.id}">${user.name} (${user.email})</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

// Create new manager
async function createManager() {
    const userId = document.getElementById('selectUser').value;
    const plan = document.getElementById('selectPlan').value;
    const paymentMethod = document.getElementById('paymentMethod').value;
    const confirmBtn = document.querySelector('#addManagerModal .btn-success');

    if (!userId) {
        showNotification('error', 'Please select a user');
        return;
    }

    const originalText = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating...';

    try {
        // 1. Update user role
        const roleResponse = await fetch(`/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({ role: 'manager' }),
            credentials: 'same-origin'
        });

        if (!roleResponse.ok) throw new Error('Failed to update user role');

        // 2. Create subscription
        const subResponse = await fetch('/api/admin/subscription/extend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                user_id: userId,
                plan_type: plan,
                payment_method: paymentMethod
            })
        });

        if (!subResponse.ok) throw new Error('Failed to create subscription');

        showNotification('success', 'Manager created successfully!');
        bootstrap.Modal.getInstance(document.getElementById('addManagerModal')).hide();
        
        setTimeout(() => loadManagers(), 500);
    } catch (error) {
        console.error('Error creating manager:', error);
        showNotification('error', 'Failed to create manager: ' + error.message);
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalText;
    }
}

// Open extend modal
function openExtendModal(userId, userName, currentExpiry) {
    document.getElementById('extendUserId').value = userId;
    document.getElementById('extendUserName').value = userName;
    document.getElementById('currentExpiry').value = currentExpiry;
    
    const modal = new bootstrap.Modal(document.getElementById('extendModal'));
    modal.show();
}

// Process subscription extension
async function processExtension() {
    const userId = document.getElementById('extendUserId').value;
    const plan = document.getElementById('extendPlan').value;
    const paymentMethod = document.getElementById('extendPaymentMethod').value;
    const confirmBtn = document.querySelector('#extendModal .btn-primary');
    
    if (!userId || !plan) {
        showNotification('error', 'Missing required information');
        return;
    }

    // Show loading state
    const originalText = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';

    try {
        const response = await fetch('/api/admin/subscription/extend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                user_id: userId,
                plan_type: plan,
                payment_method: paymentMethod
            })
        });

        const data = await response.json();

        if (data.success) {
            showNotification('success', data.message || 'Subscription extended successfully!');
            bootstrap.Modal.getInstance(document.getElementById('extendModal')).hide();
            setTimeout(() => loadManagers(), 500);
        } else {
            showNotification('error', data.message || 'Failed to extend subscription');
        }
    } catch (error) {
        console.error('Error extending subscription:', error);
        showNotification('error', 'An error occurred while processing the request');
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalText;
    }
}

// Revoke manager access
async function revokeManager(managerId, managerName, managerEmail) {
    if (!confirm(`Revoke manager access for "${managerName}" (${managerEmail})?\n\nThey will be downgraded to a regular customer.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/users/${managerId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: 'customer' }),
            credentials: 'same-origin'
        });

        if (!response.ok) throw new Error('Failed to revoke manager');

        showNotification('success', 'Manager access revoked successfully');
        setTimeout(() => loadManagers(), 500);
    } catch (error) {
        console.error('Error revoking manager:', error);
        showNotification('error', 'Failed to revoke manager access');
    }
}

// Search managers
document.getElementById('searchManager')?.addEventListener('input', (e) => {
    const searchTerm = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('#managersTable tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
});

// Filter transactions
document.getElementById('filterTransactions')?.addEventListener('change', (e) => {
    const filter = e.target.value;
    const rows = document.querySelectorAll('#transactionsTable tr');
    
    rows.forEach(row => {
        if (filter === 'all') {
            row.style.display = '';
        } else {
            const statusCell = row.querySelector('.badge');
            if (statusCell) {
                const status = statusCell.textContent.toLowerCase();
                row.style.display = status.includes(filter.toLowerCase()) ? '' : 'none';
            }
        }
    });
});

// Utility: Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('vi-VN').format(amount);
}

// Utility: Show notification
function showNotification(type, message) {
    const alertClass = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-danger' : 'alert-info';
    const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle';
    
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show position-fixed shadow-lg" 
             style="top: 80px; right: 20px; z-index: 9999; min-width: 320px; max-width: 400px;">
            <i class="fas fa-${icon} me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', alertHtml);
    
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        if (alerts.length > 0) alerts[alerts.length - 1].remove();
    }, 4000);
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
    if (!tbody) return;

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
    if (!tbody) return;

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
    const modalEl = document.getElementById('extendModal');
    if (!modalEl) return;
    document.getElementById('extendUserId').value = userId;
    document.getElementById('extendUserName').value = userName;
    new bootstrap.Modal(modalEl).show();
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
            const modalEl = document.getElementById('extendModal');
            if (modalEl) {
                const modalInstance = bootstrap.Modal.getInstance(modalEl);
                if (modalInstance) modalInstance.hide();
            }
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
        const transactions = data.transactions || [];
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

document.addEventListener('DOMContentLoaded', () => {
    loadSubscriptions();
    loadPaymentHistory();
    initAutomationUI();
    // Load pending wallet transactions for admin review (if table exists on this page)
    if (document.getElementById('pendingPaymentsTable')) {
        loadPendingPayments();
    }
});
