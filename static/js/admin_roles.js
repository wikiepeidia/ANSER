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
        showAlert('error', 'Failed to load users: ' + error.message);
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

    document.querySelectorAll('#roleTabs .nav-link').forEach((link) => {
        link.classList.remove('active');
    });
    document.querySelector(`#roleTabs .nav-link[data-role="${role}"]`).classList.add('active');

    renderUsersTable();
}

function renderUsersTable() {
    const tbody = document.getElementById('usersTableBody');

    let filteredUsers = allUsers;
    if (currentFilter !== 'all') {
        filteredUsers = allUsers.filter((u) => u.role === currentFilter);
    }

    if (filteredUsers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No accounts found</td></tr>';
        return;
    }

    tbody.innerHTML = filteredUsers
        .map((user) => {
            const badgeClass =
                user.role === 'admin' ? 'bg-danger' : user.role === 'manager' ? 'bg-warning' : 'bg-primary';
            const roleText = user.role.toUpperCase();

            let actionButtons = '';

            if (user.role === 'user') {
                actionButtons = `
                <button class="btn btn-action btn-success btn-sm" onclick="promoteToManager(${user.id}, '${user.email}')">
                    <i class="fas fa-arrow-up"></i> Promote to Manager
                </button>
            `;
            } else if (user.role === 'manager') {
                actionButtons = `
                <button class="btn btn-action btn-warning btn-sm" onclick="demoteToUser(${user.id}, '${user.email}')">
                    <i class="fas fa-arrow-down"></i> Demote to User
                </button>
            `;
            } else {
                actionButtons = '<span class="text-muted"><i class="fas fa-lock"></i> Cannot change</span>';
            }

            return `
            <tr>
                <td>${user.id}</td>
                <td>${user.name}</td>
                <td>${user.email}</td>
                <td><span class="badge ${badgeClass}">${roleText}</span></td>
                <td>${new Date(user.created_at).toLocaleDateString('en-US')}</td>
                <td>${actionButtons}</td>
            </tr>
        `;
        })
        .join('');
}

async function promoteToManager(userId, email) {
    if (!confirm(`Are you sure you want to promote "${email}" to Manager?\n\nManagers will be able to grant permissions to other users.`)) {
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
            showAlert('success', `✅ Promoted "${email}" to Manager successfully!`);
            loadUsers();
        } else {
            showAlert('error', data.message || 'Upgrade failed');
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
    }
}

async function demoteToUser(userId, email) {
    if (!confirm(`Are you sure you want to demote "${email}" to User?\n\nManagers will lose permission to grant permissions to other users.`)) {
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
            showAlert('success', `✅ Demoted "${email}" to User successfully!`);
            loadUsers();
        } else {
            showAlert('error', data.message || 'Demotion failed');
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
    }
}

function showAlert(type, message) {
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

document.addEventListener('DOMContentLoaded', loadUsers);
