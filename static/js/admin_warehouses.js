let warehousesData = [];

function _csrfHeaders() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    return { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken };
}

async function loadWarehouses() {
    try {
        const response = await fetch('/api/admin/warehouses');
        const data = await response.json();
        warehousesData = data.warehouses || [];
        renderWarehousesTable();
    } catch (error) {
        showAlert('error', 'Không tải được danh sách kho: ' + error.message);
    }
}

function renderWarehousesTable() {
    const tbody = document.getElementById('warehousesTableBody');

    if (warehousesData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Chưa có kho nào</td></tr>';
        return;
    }

    tbody.innerHTML = warehousesData
        .map(
            (w) => `
        <tr>
            <td>${w.id}</td>
            <td>${w.name}</td>
            <td>${w.low_stock_threshold}</td>
            <td>${w.notification_email ? w.notification_email : '<span class="text-muted">Chưa cấu hình</span>'}</td>
            <td><span class="badge bg-${w.is_active ? 'success' : 'secondary'}">${w.is_active ? 'Đang bật' : 'Đã tắt'}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="openEditWarehouseModal(${w.id})">
                    <i class="fas fa-edit"></i> Sửa
                </button>
                <button class="btn btn-sm btn-danger" onclick="removeWarehouse(${w.id}, '${w.name}')">
                    <i class="fas fa-trash"></i> Xóa
                </button>
            </td>
        </tr>
    `
        )
        .join('');
}

function openAddWarehouseModal() {
    document.getElementById('warehouseModalTitle').textContent = 'Thêm Kho';
    document.getElementById('warehouseId').value = '';
    document.getElementById('warehouseName').value = '';
    document.getElementById('warehouseThreshold').value = '10';
    document.getElementById('warehouseNotificationEmail').value = '';
    document.getElementById('warehouseDiscordUrl').value = '';
    document.getElementById('warehouseActive').checked = true;
    new bootstrap.Modal(document.getElementById('warehouseModal')).show();
}

function openEditWarehouseModal(id) {
    const w = warehousesData.find((x) => x.id === id);
    if (!w) return;
    document.getElementById('warehouseModalTitle').textContent = 'Sửa Kho';
    document.getElementById('warehouseId').value = w.id;
    document.getElementById('warehouseName').value = w.name;
    document.getElementById('warehouseThreshold').value = w.low_stock_threshold;
    document.getElementById('warehouseNotificationEmail').value = w.notification_email || '';
    document.getElementById('warehouseDiscordUrl').value = w.discord_webhook_url || '';
    document.getElementById('warehouseActive').checked = w.is_active;
    new bootstrap.Modal(document.getElementById('warehouseModal')).show();
}

async function saveWarehouse() {
    const id = document.getElementById('warehouseId').value;
    const name = document.getElementById('warehouseName').value.trim();
    const low_stock_threshold = parseInt(document.getElementById('warehouseThreshold').value, 10) || 0;
    const notification_email = document.getElementById('warehouseNotificationEmail').value.trim();
    const discord_webhook_url = document.getElementById('warehouseDiscordUrl').value.trim();
    const is_active = document.getElementById('warehouseActive').checked;

    if (!name) {
        showAlert('error', 'Vui lòng nhập tên kho');
        return;
    }

    const url = id ? `/api/admin/warehouses/${id}/update` : '/api/admin/warehouses';

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: _csrfHeaders(),
            body: JSON.stringify({ name, low_stock_threshold, notification_email, discord_webhook_url, is_active }),
        });
        const data = await response.json();

        if (data.success) {
            showAlert('success', data.message || 'Lưu kho thành công!');
            bootstrap.Modal.getInstance(document.getElementById('warehouseModal')).hide();
            loadWarehouses();
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function removeWarehouse(id, name) {
    if (!confirm(`Bạn có chắc chắn muốn xóa kho "${name}"?`)) return;

    try {
        const response = await fetch(`/api/admin/warehouses/${id}/delete`, {
            method: 'POST',
            headers: _csrfHeaders(),
        });
        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Xóa kho thành công!');
            loadWarehouses();
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('main').insertBefore(alertDiv, document.querySelector('main').firstChild);
    setTimeout(() => alertDiv.remove(), 5000);
}

document.addEventListener('DOMContentLoaded', loadWarehouses);
