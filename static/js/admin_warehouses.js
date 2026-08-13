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
        banleUI.showAlert('error', 'Không tải được danh sách kho: ' + error.message);
    }
}

function renderWarehousesTable() {
    const tbody = document.getElementById('warehousesTableBody');

    if (warehousesData.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="6">
                <div class="empty-state empty-state--compact">
                    <div class="empty-state__icon"><i class="fa-solid fa-warehouse"></i></div>
                    <p class="empty-state__title">Chưa có kho nào</p>
                    <p class="empty-state__description">Nhấn "Thêm Kho" ở góc trên để tạo kho đầu tiên.</p>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = warehousesData
        .map(
            (w) => {
                const actions = [
                    { label: 'Sửa', icon: 'fa-solid fa-pen', action: 'openEditWarehouseModal' },
                    { divider: true },
                    { label: 'Xóa', icon: 'fa-solid fa-trash', action: 'removeWarehouse', danger: true },
                ];
                return `
        <tr>
            <td>${w.id}</td>
            <td>${banleUI.escapeHtml(w.name)}</td>
            <td>${w.low_stock_threshold}</td>
            <td>${w.notification_email ? banleUI.escapeHtml(w.notification_email) : '<span class="text-muted">Chưa cấu hình</span>'}</td>
            <td>${banleUI.statusPill(w.is_active ? 'Đang bật' : 'Đã tắt', w.is_active ? 'green' : 'gray')}</td>
            <td class="table__actions">${banleUI.renderRowActions(w.id, actions)}</td>
        </tr>
    `;
            }
        )
        .join('');

    banleUI.bindRowActions(tbody);
}

function openAddWarehouseModal() {
    document.getElementById('warehouseModalTitle').textContent = 'Thêm Kho';
    document.getElementById('warehouseId').value = '';
    document.getElementById('warehouseName').value = '';
    document.getElementById('warehouseThreshold').value = '10';
    document.getElementById('warehouseNotificationEmail').value = '';
    document.getElementById('warehouseDiscordUrl').value = '';
    document.getElementById('warehouseActive').checked = true;
    openModal('warehouseModal');
}

function openEditWarehouseModal(id) {
    const w = warehousesData.find((x) => String(x.id) === String(id));
    if (!w) return;
    document.getElementById('warehouseModalTitle').textContent = 'Sửa Kho';
    document.getElementById('warehouseId').value = w.id;
    document.getElementById('warehouseName').value = w.name;
    document.getElementById('warehouseThreshold').value = w.low_stock_threshold;
    document.getElementById('warehouseNotificationEmail').value = w.notification_email || '';
    document.getElementById('warehouseDiscordUrl').value = w.discord_webhook_url || '';
    document.getElementById('warehouseActive').checked = w.is_active;
    openModal('warehouseModal');
}

async function saveWarehouse() {
    const id = document.getElementById('warehouseId').value;
    const name = document.getElementById('warehouseName').value.trim();
    const low_stock_threshold = parseInt(document.getElementById('warehouseThreshold').value, 10) || 0;
    const notification_email = document.getElementById('warehouseNotificationEmail').value.trim();
    const discord_webhook_url = document.getElementById('warehouseDiscordUrl').value.trim();
    const is_active = document.getElementById('warehouseActive').checked;

    if (!name) {
        banleUI.showAlert('error', 'Vui lòng nhập tên kho');
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
            banleUI.showAlert('success', data.message || 'Lưu kho thành công!');
            closeModal('warehouseModal');
            loadWarehouses();
        } else {
            banleUI.showAlert('error', data.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function removeWarehouse(id) {
    const w = warehousesData.find((x) => String(x.id) === String(id));
    const name = w ? w.name : `#${id}`;
    if (!confirm(`Bạn có chắc chắn muốn xóa kho "${name}"?`)) return;

    try {
        const response = await fetch(`/api/admin/warehouses/${id}/delete`, {
            method: 'POST',
            headers: _csrfHeaders(),
        });
        const data = await response.json();

        if (data.success) {
            banleUI.showAlert('success', 'Xóa kho thành công!');
            loadWarehouses();
        } else {
            banleUI.showAlert('error', data.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

document.addEventListener('DOMContentLoaded', loadWarehouses);
