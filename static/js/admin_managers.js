let managersData = [];

async function loadManagers() {
    try {
        const response = await fetch('/api/admin/users');
        const data = await response.json();
        const users = data.users || [];
        managersData = users.filter((u) => u.role === 'manager' || u.role === 'admin');
        renderManagersTable();
    } catch (error) {
        showAlert('error', 'Không tải được danh sách: ' + error.message);
    }
}

function renderManagersTable() {
    const tbody = document.getElementById('managersTableBody');

    if (managersData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Không tìm thấy quản lý</td></tr>';
        return;
    }

    tbody.innerHTML = managersData
        .map(
            (manager) => `
        <tr>
            <td>${manager.id}</td>
            <td>${manager.name}</td>
            <td>${manager.email}</td>
            <td><span class="badge bg-${manager.role === 'admin' ? 'danger' : 'warning'}">${manager.role.toUpperCase()}</span></td>
            <td>${new Date(manager.created_at).toLocaleDateString('en-US')}</td>
            <td>
                ${
                    manager.role !== 'admin'
                        ? `
                    <button class="btn btn-sm btn-danger" onclick="removeManager(${manager.id}, '${manager.email}')">
                        <i class="fas fa-trash"></i> Xóa
                    </button>
                `
                        : '<span class="text-muted">Quản trị gốc</span>'
                }
            </td>
        </tr>
    `
        )
        .join('');
}

function openAddManagerModal() {
    document.getElementById('managerModalTitle').textContent = 'Thêm quản lý';
    document.getElementById('managerId').value = '';
    document.getElementById('managerEmail').value = '';
    document.getElementById('managerName').value = '';
    document.getElementById('managerPassword').value = '';
    document.getElementById('passwordGroup').style.display = 'block';
    new bootstrap.Modal(document.getElementById('managerModal')).show();
}

async function saveManager() {
    const email = document.getElementById('managerEmail').value.trim();
    const name = document.getElementById('managerName').value.trim();
    const password = document.getElementById('managerPassword').value;

    if (!email || !name) {
        showAlert('error', 'Vui lòng điền tất cả các trường bắt buộc');
        return;
    }

    if (!password) {
        showAlert('error', 'Vui lòng nhập mật khẩu');
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
            showAlert('success', 'Tạo quản lý thành công!');
            bootstrap.Modal.getInstance(document.getElementById('managerModal')).hide();
            loadManagers();
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function removeManager(managerId, email) {
    if (!confirm(`Bạn có chắc chắn muốn xóa quản lý "${email}"?`)) return;

    try {
        const response = await fetch(`/api/admin/users/${managerId}`, {
            method: 'DELETE',
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Xóa quản lý thành công!');
            loadManagers();
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

document.addEventListener('DOMContentLoaded', loadManagers);
