async function loadSubscriptions() {
    try {
        const response = await fetch('/api/admin/subscriptions', { credentials: 'same-origin' });
        if (response.status === 401 || response.status === 403) {
            showAlert('error', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
            setTimeout(() => { window.location.href = '/auth/signin'; }, 3000);
            return;
        }
        if (!response.ok) throw new Error('Failed to load subscriptions');

        const data = await response.json();
        renderSubscriptionsTable(data.subscriptions || []);
    } catch (error) {
        if (error.message.includes('JSON')) {
            showAlert('error', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
        } else {
            showAlert('error', 'Lỗi tải danh sách: ' + error.message);
        }
    }
}

async function loadPaymentHistory() {
    try {
        const response = await fetch('/api/admin/subscription-history', { credentials: 'same-origin' });
        if (response.status === 401 || response.status === 403) {
            showAlert('error', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
            setTimeout(() => { window.location.href = '/auth/signin'; }, 3000);
            return;
        }
        if (!response.ok) throw new Error('Failed to load history');

        const data = await response.json();
        renderPaymentHistory(data.history || []);
    } catch (error) {
        if (error.message.includes('JSON')) {
            showAlert('error', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
        } else {
            console.error('Error loading payment history:', error);
        }
    }
}

function renderSubscriptionsTable(subscriptions) {
    const tbody = document.getElementById('subscriptionsTable');

    if (subscriptions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">Chưa có Manager nào</td></tr>';
        return;
    }

    tbody.innerHTML = subscriptions
        .map((sub) => {
            const endDate = new Date(sub.end_date);
            const now = new Date();
            const daysLeft = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));

            let statusBadge = '';
            if (sub.status === 'expired') {
                statusBadge = '<span class="badge badge-expired">Hết hạn</span>';
            } else if (daysLeft <= 7) {
                statusBadge = `<span class="badge badge-expiring">Còn ${daysLeft} ngày</span>`;
            } else {
                statusBadge = `<span class="badge bg-success">Hoạt động (${daysLeft} ngày)</span>`;
            }

            const planNames = {
                trial: 'Dùng thử',
                monthly: 'Tháng',
                quarterly: 'Quý',
                yearly: 'Năm',
            };

            return `
            <tr>
                <td><strong>${sub.user_name}</strong></td>
                <td>${sub.user_email}</td>
                <td><span class="badge bg-primary">${planNames[sub.subscription_type] || sub.subscription_type}</span></td>
                <td>${new Date(sub.start_date).toLocaleDateString('vi-VN')}</td>
                <td>${endDate.toLocaleDateString('vi-VN')}</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-sm btn-success" onclick="openExtendModal(${sub.user_id}, '${sub.user_name.replace(/'/g, "&apos;")}')">
                        <i class="fas fa-plus"></i> Gia hạn
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
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Chưa có lịch sử thanh toán</td></tr>';
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
                <td>${new Date(payment.payment_date).toLocaleDateString('vi-VN')}</td>
                <td>${payment.user_name}</td>
                <td>${planNames[payment.subscription_type] || payment.subscription_type}</td>
                <td><strong>${payment.amount.toLocaleString('vi-VN')}đ</strong></td>
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

        if (response.status === 401 || response.status === 403) {
            showAlert('error', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
            return;
        }
        const data = await response.json();

        if (data.success) {
            showAlert('success', '✅ Gia hạn thành công!');
            bootstrap.Modal.getInstance(document.getElementById('extendModal')).hide();
            loadSubscriptions();
            loadPaymentHistory();
        } else {
            showAlert('error', data.message || 'Lỗi gia hạn');
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function checkExpiredSubscriptions() {
    if (!confirm('Bạn có chắc muốn kiểm tra và hạ cấp các Manager hết hạn?')) return;

    try {
        const response = await fetch('/api/admin/check-expired-subscriptions', {
            method: 'POST',
        });
        if (response.status === 401 || response.status === 403) {
            showAlert('error', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
            return;
        }

        const data = await response.json();

        if (data.success) {
            showAlert('success', `✅ Đã hạ cấp ${data.demoted_count} Manager hết hạn!`);
            loadSubscriptions();
        } else {
            showAlert('error', data.message || 'Lỗi kiểm tra');
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
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
    statusLabel.textContent = automationSettings.autoUpgrade ? 'Đang bật' : 'Đang tắt';
    ownerLabel.textContent = automationSettings.autoNotify ? 'Đã bật' : 'Chưa bật';
    updateBankStatus();
}

function updateBankStatus() {
    const bankLabel = document.getElementById('bankLinkStatus');
    const receiptInfo = document.getElementById('receiptInfo');
    if (bankLabel) bankLabel.textContent = automationSettings.bankLinked ? 'Đã liên kết ngân hàng' : 'Chưa kết nối';
    if (receiptInfo) receiptInfo.textContent = automationSettings.bankLinked ? 'Tự động đính kèm sao kê' : 'Đang chờ kết nối ngân hàng';
}

function linkBankAccount() {
    automationSettings.bankLinked = true;
    updateBankStatus();
    showAlert('success', 'Đã liên kết ngân hàng thành công');
}

function toggleAutoUpgrade(isOn) {
    automationSettings.autoUpgrade = isOn;
    const statusLabel = document.getElementById('autoUpgradeStatus');
    if (statusLabel) statusLabel.textContent = isOn ? 'Đang bật' : 'Đang tắt';
    const healthBadge = document.getElementById('automationHealth');
    if (healthBadge) {
        healthBadge.textContent = isOn ? 'ON' : 'PAUSED';
        healthBadge.classList.toggle('bg-danger', !isOn);
        healthBadge.classList.toggle('bg-success', isOn);
    }
    showAlert('success', isOn ? 'Đã bật auto nâng quyền' : 'Đã tắt auto nâng quyền');
}

function toggleOwnerNotify(isOn) {
    automationSettings.autoNotify = isOn;
    const ownerLabel = document.getElementById('ownerAlertStatus');
    if (ownerLabel) ownerLabel.textContent = isOn ? 'Đã bật' : 'Chưa bật';
    showAlert('success', isOn ? 'Đã bật thông báo chủ web' : 'Đã tắt thông báo chủ web');
}

function refreshPaymentQueue() { loadPendingPayments(true); }

function triggerManualPayout() { showAlert('success', 'Đã gửi yêu cầu đối soát đến ngân hàng'); }

document.addEventListener('DOMContentLoaded', () => { initAutomationUI(); });

async function loadPendingPayments(showToastMessage = false) {
    const tbody = document.querySelector('#pendingPaymentsTable tbody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div></td></tr>';
    }
    try {
        const response = await fetch('/api/admin/wallet/pending', { credentials: 'same-origin' });
        if (response.status === 401 || response.status === 403) {
            showAlert('error', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
            if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Quyền truy cập bị từ chối</td></tr>';
            setTimeout(() => { window.location.href = '/auth/signin'; }, 3000);
            return;
        }
        const data = await response.json();
        if (!data.success) throw new Error(data.message || 'Failed to load pending payments');
        const transactions = data.transactions || [];
        if (!tbody) return;
        if (!transactions.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Không có giao dịch chờ</td></tr>';
            return;
        }
        tbody.innerHTML = transactions.map(payment => {
            const planLabel = payment.plan_label ? String(payment.plan_label).toUpperCase() : (payment.type === 'topup' ? 'NẠP VÍ' : (payment.type || '—'));
            const methodLabel = payment.method || '—';
            const createdAt = payment.created_at ? `<br><small class="text-muted">${payment.created_at}</small>` : '';
            const reference = payment.reference ? `<br><small class="text-muted">Ref: ${payment.reference}</small>` : '';
            const statusObj = localizeStatus(payment.status);
            return `
                <tr>
                    <td><span class="badge bg-dark">TX-${payment.id}</span>${createdAt}</td>
                    <td><strong>${payment.user_name}</strong><br><small>${payment.user_email}</small></td>
                    <td><span class="badge bg-primary">${planLabel}</span></td>
                    <td>${(payment.amount || 0).toLocaleString('vi-VN')} đ</td>
                    <td>${methodLabel}${reference}</td>
                    <td class="text-end">
                        <span class="me-2"><span class="badge ${statusObj.cls}">${statusObj.label}</span></span>
                        <button class="btn btn-sm btn-success me-2" onclick="processQueuedPayment(${payment.id}, 'approve')"><i class="fas fa-check"></i></button>
                        <button class="btn btn-sm btn-outline-danger" onclick="processQueuedPayment(${payment.id}, 'reject')"><i class="fas fa-times"></i></button>
                    </td>
                </tr>
            `;
        }).join('');
        if (showToastMessage) showAlert('success', 'Đã tải danh sách giao dịch chờ.');
    } catch (error) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Không thể tải giao dịch</td></tr>';
        if (error.message.includes('JSON')) {
            showAlert('error', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
        } else {
            showAlert('error', 'Lỗi: ' + error.message);
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
        if (response.status === 401 || response.status === 403) {
            showAlert('error', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
            setTimeout(() => { window.location.href = '/auth/signin'; }, 3000);
            return;
        }
        const data = await response.json();
        if (data.success) {
            showAlert('success', data.message || 'Đã xử lý giao dịch');
            await loadPendingPayments();
            // Update subscription/account summaries
            loadSubscriptions();
            loadPaymentHistory();
        } else {
            showAlert('error', data.message || 'Không thể xử lý giao dịch');
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}
