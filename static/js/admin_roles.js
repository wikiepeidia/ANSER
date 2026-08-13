let allUsers = [];
let currentFilter = 'all';

async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users');
        if (!response.ok) throw new Error('Failed to load users');

        const data = await response.json();
        allUsers = data.users || [];

        updateStatistics();
        renderUsersTable();
    } catch (error) {
        banleUI.showAlert('error', 'Không tải được danh sách: ' + error.message);
    }
}

function updateStatistics() {
    const adminCount = allUsers.filter((u) => u.role === 'admin').length;
    const managerCount = allUsers.filter((u) => u.role === 'manager').length;
    const userCount = allUsers.filter((u) => u.role === 'user').length;

    document.getElementById('adminCount').textContent = adminCount;
    document.getElementById('managerCount').textContent = managerCount;
    document.getElementById('userCount').textContent = userCount;
}

function filterByRole(role) {
    currentFilter = role;

    document.querySelectorAll('#roleTabs .tabs__item').forEach((tab) => {
        tab.classList.remove('active');
    });
    const activeTab = document.querySelector(`#roleTabs .tabs__item[data-role="${role}"]`);
    if (activeTab) activeTab.classList.add('active');

    renderUsersTable();
}

function roleTone(role) {
    if (role === 'admin') return 'red';
    if (role === 'manager') return 'orange';
    return 'blue';
}

function renderUsersTable() {
    const tbody = document.getElementById('usersTableBody');

    let filteredUsers = allUsers;
    if (currentFilter !== 'all') {
        filteredUsers = allUsers.filter((u) => u.role === currentFilter);
    }

    if (filteredUsers.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="6">
                <div class="empty-state empty-state--compact">
                    <div class="empty-state__icon"><i class="fa-solid fa-users"></i></div>
                    <p class="empty-state__title">Không có tài khoản</p>
                    <p class="empty-state__description">Chưa có tài khoản nào thuộc vai trò này.</p>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = filteredUsers
        .map((user) => {
            const actions = [];
            if (user.role === 'user') {
                actions.push({ label: 'Nâng cấp lên Manager', icon: 'fa-solid fa-arrow-up', action: 'promoteToManager' });
            } else if (user.role === 'manager') {
                actions.push({ label: 'Hạ cấp xuống User', icon: 'fa-solid fa-arrow-down', action: 'demoteToUser' });
            } else {
                actions.push({ label: 'Quản trị viên gốc', icon: 'fa-solid fa-lock', action: '__noop' });
            }

            return `
            <tr>
                <td>${user.id}</td>
                <td>${banleUI.escapeHtml(user.name || '—')}</td>
                <td>${banleUI.escapeHtml(user.email)}</td>
                <td>${banleUI.statusPill(user.role.toUpperCase(), roleTone(user.role))}</td>
                <td>${banleUI.formatDateVN(user.created_at)}</td>
                <td class="table__actions">${banleUI.renderRowActions(user.id, actions)}</td>
            </tr>
        `;
        })
        .join('');

    banleUI.bindRowActions(tbody);
}

async function promoteToManager(userId) {
    const user = allUsers.find((u) => String(u.id) === String(userId));
    const email = user ? user.email : `#${userId}`;
    if (!confirm(`Bạn có chắc muốn nâng cấp "${email}" lên Manager?\n\nManager sẽ có quyền cấp quyền cho người khác.`)) {
        return;
    }

    try {
        const response = await fetch('/api/admin/users/promote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, role: 'manager' }),
        });

        const data = await response.json();

        if (data.success) {
            banleUI.showAlert('success', `Đã nâng cấp "${email}" lên Manager.`);
            loadUsers();
        } else {
            banleUI.showAlert('error', data.message || 'Nâng cấp thất bại');
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function demoteToUser(userId) {
    const user = allUsers.find((u) => String(u.id) === String(userId));
    const email = user ? user.email : `#${userId}`;
    if (!confirm(`Bạn có chắc muốn hạ cấp "${email}" xuống User?\n\nManager sẽ mất quyền cấp quyền cho người khác.`)) {
        return;
    }

    try {
        const response = await fetch('/api/admin/users/demote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, role: 'user' }),
        });

        const data = await response.json();

        if (data.success) {
            banleUI.showAlert('success', `Đã hạ cấp "${email}" xuống User.`);
            loadUsers();
        } else {
            banleUI.showAlert('error', data.message || 'Hạ cấp thất bại');
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

function __noop() { /* locked role — no action */ }

document.addEventListener('DOMContentLoaded', loadUsers);
