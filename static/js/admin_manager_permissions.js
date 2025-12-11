let usersData = [];
let visibleUsers = [];

async function loadUsers() {
    try {
        const response = await fetch('/api/manager/users-permissions');
        const data = await response.json();

        if (data.success) {
            usersData = data.users;
            updateStats();
            filterUsers();
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Lỗi tải danh sách user: ' + error.message);
    }
}

function renderUsersTable(data = []) {
    const tbody = document.getElementById('usersTableBody');

    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-row">Không có user nào phù hợp bộ lọc</td></tr>';
        return;
    }

    const roleBadge = (role) => {
        if (role === 'admin') return 'badge-role badge-role--admin';
        if (role === 'manager') return 'badge-role badge-role--manager';
        return 'badge-role badge-role--user';
    };

    tbody.innerHTML = data
        .map((user) => {
            const permissions = Array.isArray(user.permissions) ? user.permissions : [];
            return `
        <tr>
            <td>${user.id}</td>
            <td>
                <div class="user-cell">
                    <div class="avatar">${(user.name || user.email || '?').charAt(0).toUpperCase()}</div>
                    <div>
                        <div class="user-name">${user.name || 'Không rõ'}</div>
                        <div class="user-email">${user.email || '-'}</div>
                    </div>
                </div>
            </td>
            <td>${user.email || '-'}</td>
            <td><span class="${roleBadge(user.role)}">${user.role}</span></td>
            <td>
                ${
                    permissions.filter(Boolean).length
                        ? permissions
                              .filter(Boolean)
                              .map(
                                  (p) => `
                        <span class="badge-permission">
                            ${p}
                            <button class="badge-action" onclick="revokePermission(${user.id}, '${p}')" title="Thu hồi">
                                <i class="fas fa-times"></i>
                            </button>
                        </span>
                    `
                              )
                              .join('')
                        : '<span class="no-permission">No permission</span>'
                }
            </td>
            <td>
                ${
                    user.role === 'user'
                        ? `
                    <button class="btn btn-sm btn-primary" onclick="openGrantModal(${user.id}, '${user.name || user.email || ''}')">
                        <i class="fas fa-plus"></i> Cấp quyền
                    </button>
                `
                        : '<span class="text-muted">N/A</span>'
                }
            </td>
        </tr>
    `;
        })
        .join('');
}

function updateStats() {
    const trackedNode = document.getElementById('trackedUsers');
    const grantedNode = document.getElementById('grantedPermissions');
    const updatedNode = document.getElementById('lastUpdate');
    const totalPerms = usersData.reduce((sum, user) => {
        const permissions = Array.isArray(user.permissions) ? user.permissions : [];
        return sum + permissions.filter(Boolean).length;
    }, 0);

    if (trackedNode) trackedNode.textContent = usersData.length;
    if (grantedNode) grantedNode.textContent = totalPerms;
    if (updatedNode) updatedNode.textContent = new Date().toLocaleString();
}

function filterUsers() {
    const searchValue = document.getElementById('userSearch')?.value.toLowerCase().trim() || '';
    const roleFilter = document.getElementById('roleFilter')?.value || 'all';

    visibleUsers = usersData.filter((user) => {
        const matchRole = roleFilter === 'all' || user.role === roleFilter;
        const target = `${user.name || ''} ${user.email || ''}`.toLowerCase();
        const matchSearch = !searchValue || target.includes(searchValue);
        return matchRole && matchSearch;
    });

    renderUsersTable(visibleUsers);
}

function openGrantModal(userId, userName) {
    document.getElementById('grantUserId').value = userId;
    document.getElementById('grantUserName').textContent = userName;
    new bootstrap.Modal(document.getElementById('grantPermissionModal')).show();
}

async function grantPermission() {
    const userId = parseInt(document.getElementById('grantUserId').value, 10);
    const permissionType = document.getElementById('permissionTypeSelect').value;

    try {
        const response = await fetch('/api/manager/permissions/grant', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, permission_type: permissionType })
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Cấp quyền thành công!');
            bootstrap.Modal.getInstance(document.getElementById('grantPermissionModal')).hide();
            loadUsers();
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function revokePermission(userId, permissionType) {
    if (!confirm(`Bạn chắc chắn muốn thu hồi quyền "${permissionType}"?`)) return;

    try {
        const response = await fetch('/api/manager/permissions/revoke', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, permission_type: permissionType })
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Thu hồi quyền thành công!');
            loadUsers();
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
    const container = document.querySelector('.permissions-main') || document.querySelector('main');
    container.insertBefore(alertDiv, container.firstChild);

    setTimeout(() => alertDiv.remove(), 5000);
}

document.addEventListener('DOMContentLoaded', loadUsers);
// Fallback: Force reload button color if anything overrides CSS
function syncReloadButtonTheme() {
    const btn = document.querySelector('.permissions-header .header-actions button[onclick="loadUsers()"]');
    if (!btn) return;
    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue('--gray-900') || '#0f172a';
    const borderColor = styles.getPropertyValue('--border-soft') || 'rgba(15,23,42,0.12)';
    btn.style.setProperty('color', textColor.trim(), 'important');
    btn.style.setProperty('border-color', borderColor.trim(), 'important');
    btn.style.setProperty('background', 'transparent', 'important');
    btn.style.setProperty('box-shadow', 'none', 'important');
}

// Re-apply on theme change
const _themeObserver = new MutationObserver((mutations) => {
    const html = document.documentElement;
    const changed = mutations.some(m => m.attributeName === 'data-theme');
    if (changed) syncReloadButtonTheme();
});
_themeObserver.observe(document.documentElement, { attributes: true });

document.addEventListener('DOMContentLoaded', () => syncReloadButtonTheme());

window.filterUsers = filterUsers;
