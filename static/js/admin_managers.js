let managersData = [];

async function loadManagers() {
    try {
        const response = await fetch('/api/admin/users');
        const data = await response.json();
        const users = data.users || [];
        managersData = users.filter((u) => u.role === 'manager' || u.role === 'admin');
        renderManagersTable();
    } catch (error) {
        banleUI.showAlert('error', 'Không tải được danh sách: ' + error.message);
    }
}

function renderManagersTable() {
    const tbody = document.getElementById('managersTableBody');

    if (managersData.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="6">
                <div class="empty-state empty-state--compact">
                    <div class="empty-state__icon"><i class="fa-solid fa-users-gear"></i></div>
                    <p class="empty-state__title">Chưa có Manager nào</p>
                    <p class="empty-state__description">Nhấn "Thêm Manager" ở góc trên để tạo tài khoản quản lý mới.</p>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = managersData
        .map(
            (manager) => {
                const isAdmin = manager.role === 'admin';
                const actions = [];
                if (!isAdmin) {
                    actions.push({ label: 'Sửa', icon: 'fa-solid fa-pen', action: 'editManager' });
                    actions.push({ divider: true });
                    actions.push({ label: 'Xóa', icon: 'fa-solid fa-trash', action: 'removeManager', danger: true });
                } else {
                    actions.push({ label: 'Xem chi tiết', icon: 'fa-solid fa-eye', action: 'viewAdmin' });
                }
                return `
        <tr>
            <td>${manager.id}</td>
            <td>${banleUI.escapeHtml(manager.name || '—')}</td>
            <td>${banleUI.escapeHtml(manager.email)}</td>
            <td>${banleUI.statusPill(manager.role.toUpperCase(), isAdmin ? 'red' : 'orange')}</td>
            <td>${banleUI.formatDateVN(manager.created_at)}</td>
            <td class="table__actions">${banleUI.renderRowActions(manager.id, actions)}</td>
        </tr>
    `;
            }
        )
        .join('');

    banleUI.bindRowActions(tbody);
}

function openAddManagerModal() {
    document.getElementById('managerModalTitle').textContent = 'Thêm quản lý';
    document.getElementById('managerId').value = '';
    document.getElementById('managerEmail').value = '';
    document.getElementById('managerName').value = '';
    document.getElementById('managerPassword').value = '';
    document.getElementById('passwordGroup').style.display = 'block';
    openModal('managerModal');
}

async function saveManager() {
    const email = document.getElementById('managerEmail').value.trim();
    const name = document.getElementById('managerName').value.trim();
    const password = document.getElementById('managerPassword').value;

    if (!email || !name) {
        banleUI.showAlert('error', 'Vui lòng điền tất cả các trường bắt buộc');
        return;
    }

    if (!password) {
        banleUI.showAlert('error', 'Vui lòng nhập mật khẩu');
        return;
    }

    try {
        const response = await fetch('/api/admin/create-manager', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, name, password }),
        });

        const data = await response.json();

        if (data.success) {
            banleUI.showAlert('success', 'Tạo quản lý thành công!');
            closeModal('managerModal');
            loadManagers();
        } else {
            banleUI.showAlert('error', data.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function removeManager(managerId) {
    const manager = managersData.find((m) => String(m.id) === String(managerId));
    const email = manager ? manager.email : `#${managerId}`;
    if (!confirm(`Bạn có chắc chắn muốn xóa quản lý "${email}"?`)) return;

    try {
        const response = await fetch(`/api/admin/users/${managerId}`, {
            method: 'DELETE',
        });

        const data = await response.json();

        if (data.success) {
            banleUI.showAlert('success', 'Xóa quản lý thành công!');
            loadManagers();
        } else {
            banleUI.showAlert('error', data.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

function editManager(managerId) {
    const manager = managersData.find((m) => String(m.id) === String(managerId));
    if (!manager) return;
    document.getElementById('managerModalTitle').textContent = 'Sửa thông tin Manager';
    document.getElementById('managerId').value = manager.id;
    document.getElementById('managerEmail').value = manager.email;
    document.getElementById('managerName').value = manager.name || '';
    document.getElementById('managerPassword').value = '';
    document.getElementById('passwordGroup').style.display = 'none';
    openModal('managerModal');
}

function viewAdmin(managerId) {
    const manager = managersData.find((m) => String(m.id) === String(managerId));
    if (manager) {
        banleUI.showAlert('info', `Admin: ${manager.name} (${manager.email})`);
    }
}

document.addEventListener('DOMContentLoaded', loadManagers);
