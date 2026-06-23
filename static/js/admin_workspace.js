// Global variables
let currentWorkspaceId = 1; // Default to first workspace
let currentEditingItem = null;
let workspaces = [];
let workspaceItems = {};

// Initialize workspace
document.addEventListener('DOMContentLoaded', function () {
    loadWorkspaces();
});

// API Functions
async function loadWorkspaces() {
    try {
        const response = await fetch('/api/workspaces');
        workspaces = await response.json();
        updateWorkspaceTree();

        if (workspaces.length > 0) {
            loadWorkspaceItems(workspaces[0].id);
        }
    } catch (error) {
        console.error('Error loading workspaces:', error);
        showNotification('Lỗi khi tải không gian làm việc', 'error');
    }
}

async function loadWorkspaceItems(workspaceId) {
    try {
        currentWorkspaceId = workspaceId;
        const response = await fetch(`/api/workspace/${workspaceId}/items`);
        const items = await response.json();
        workspaceItems[workspaceId] = items;
        updateWorkspaceItemsDisplay(items);
    } catch (error) {
        console.error('Error loading workspace items:', error);
        showNotification('Lỗi khi tải mục', 'error');
    }
}

function updateWorkspaceTree() {
    // This would update the tree structure in the sidebar
    // For now, we'll keep the static structure
}

function updateWorkspaceItemsDisplay(items) {
    // Update the workspace tree to show actual items
    const personalWorkspace = document.querySelector('[data-type="workspace"]');
    if (personalWorkspace) {
        const badge = personalWorkspace.querySelector('.tree-badge');
        if (badge) {
            badge.textContent = items.length;
        }
    }
}

// Modal Functions
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    resetForm(modalId);
}

function resetForm(modalId) {
    const form = document.querySelector(`#${modalId} form`);
    if (form) {
        form.reset();
    }
    currentEditingItem = null;
}

// Item Management
async function saveItem() {
    const form = document.getElementById('itemForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);

    if (!data.title.trim()) {
        showNotification('Vui lòng nhập tiêu đề', 'error');
        return;
    }

    try {
        let response;
        if (currentEditingItem) {
            // Update existing item
            response = await fetch(`/api/items/${currentEditingItem.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
        } else {
            // Create new item
            response = await fetch(`/api/workspace/${currentWorkspaceId}/items`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
        }

        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('createItemModal');
            loadWorkspaceItems(currentWorkspaceId); // Refresh items
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('Error saving item:', error);
        showNotification('Lỗi khi lưu mục', 'error');
    }
}

async function deleteItem(itemId) {
    if (!confirm('Bạn có chắc chắn muốn xóa mục này?')) {
        return;
    }

    try {
        const response = await fetch(`/api/items/${itemId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
            loadWorkspaceItems(currentWorkspaceId); // Refresh items
            closeItemDetail();
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('Error deleting item:', error);
        showNotification('Lỗi khi xóa mục', 'error');
    }
}

// Workspace Management
async function saveWorkspace() {
    const form = document.getElementById('workspaceForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);

    if (!data.name.trim()) {
        showNotification('Vui lòng nhập tên không gian làm việc', 'error');
        return;
    }

    try {
        const response = await fetch('/api/workspace', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('createWorkspaceModal');
            loadWorkspaces(); // Refresh workspaces
        } else {
            showNotification(result.message, 'error');
        }
    } catch (error) {
        console.error('Error creating workspace:', error);
        showNotification('Lỗi khi tạo không gian làm việc', 'error');
    }
}

// Item Detail Panel
function showItemDetail(item) {
    currentEditingItem = item;

    document.getElementById('itemDetailTitle').textContent = item.title;
    document.getElementById('itemDetailType').textContent = item.type;
    document.getElementById('itemDetailPriority').textContent = item.priority;
    document.getElementById('itemDetailStatus').textContent = item.status;
    document.getElementById('itemDetailDescription').textContent = item.description || 'Chưa có mô tả';

    const panel = document.getElementById('itemDetailPanel');
    panel.style.display = 'flex';
    panel.classList.add('open');
}

function closeItemDetail() {
    const panel = document.getElementById('itemDetailPanel');
    panel.classList.remove('open');
    setTimeout(() => {
        panel.style.display = 'none';
    }, 300);
    currentEditingItem = null;
}

function editCurrentItem() {
    if (currentEditingItem) {
        // Populate form with current item data
        document.getElementById('itemTitle').value = currentEditingItem.title;
        document.getElementById('itemDescription').value = currentEditingItem.description || '';
        document.getElementById('itemType').value = currentEditingItem.type;
        document.getElementById('itemPriority').value = currentEditingItem.priority;
        document.getElementById('itemStatus').value = currentEditingItem.status;

        document.getElementById('modalTitle').textContent = 'Sửa mục';
        openModal('createItemModal');
        closeItemDetail();
    }
}

function deleteCurrentItem() {
    if (currentEditingItem) {
        deleteItem(currentEditingItem.id);
    }
}

// Tree navigation
document.querySelectorAll('.tree-item').forEach(item => {
    const content = item.querySelector('.tree-item-content');
    const expand = item.querySelector('.tree-expand');

    if (expand && content) {
        content.addEventListener('click', (e) => {
            e.stopPropagation();
            item.classList.toggle('expanded');
        });
    }

    // Right-click context menu
    content.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showContextMenu(e.pageX, e.pageY);
    });

    // Selection
    content.addEventListener('click', (e) => {
        if (!expand || !expand.contains(e.target)) {
            document.querySelectorAll('.tree-item').forEach(i => i.classList.remove('selected'));
            item.classList.add('selected');
        }
    });
});

// Activity bar switching
document.querySelectorAll('.activity-item[data-view]').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.activity-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');

        const view = item.dataset.view;
        switchSidebarView(view);
    });
});

function switchSidebarView(view) {
    const sidebarTitle = document.querySelector('.sidebar-title');
    const sidebarContent = document.querySelector('.sidebar-content');

    switch (view) {
        case 'explorer':
            sidebarTitle.textContent = 'KHÁM PHÁ';
            break;
        case 'search':
            sidebarTitle.textContent = 'TÌM KIẾM';
            break;
        case 'git':
            sidebarTitle.textContent = 'QUẢN LÝ MÃ NGUỒN';
            break;
        case 'debug':
            sidebarTitle.textContent = 'CHẠY VÀ GỠ LỖI';
            break;
        case 'extensions':
            sidebarTitle.textContent = 'TIỆN ÍCH MỞ RỘNG';
            break;
        case 'scenarios':
            sidebarTitle.textContent = 'KỊCH BẢN';
            break;
    }
}

// Context menu
function showContextMenu(x, y) {
    const contextMenu = document.getElementById('contextMenu');
    contextMenu.style.display = 'block';
    contextMenu.style.left = x + 'px';
    contextMenu.style.top = y + 'px';
}

function hideContextMenu() {
    document.getElementById('contextMenu').style.display = 'none';
}

document.addEventListener('click', hideContextMenu);

function contextAction(action) {
    hideContextMenu();

    switch (action) {
        case 'new-file':
            document.getElementById('itemType').value = 'task';
            document.getElementById('modalTitle').textContent = 'Tạo việc cần làm mới';
            openModal('createItemModal');
            break;
        case 'new-folder':
            document.getElementById('itemType').value = 'note';
            document.getElementById('modalTitle').textContent = 'Tạo ghi chú mới';
            openModal('createItemModal');
            break;
        case 'rename':
            if (currentEditingItem) {
                editCurrentItem();
            }
            break;
        case 'delete':
            if (currentEditingItem) {
                deleteCurrentItem();
            }
            break;
    }
}

// Welcome screen actions
function createNewItem(type) {
    document.getElementById('itemType').value = type;
    document.getElementById('modalTitle').textContent = `Tạo mới ${type.charAt(0).toUpperCase() + type.slice(1)}`;
    openModal('createItemModal');
}

function createWorkspace() {
    openModal('createWorkspaceModal');
}

function openScenarios() {
    // Switch to scenarios view
    document.querySelector('[data-view="scenarios"]').click();
}

// Tab management
document.querySelectorAll('.tab-close').forEach(close => {
    close.addEventListener('click', (e) => {
        e.stopPropagation();
        e.target.closest('.tab').remove();
    });
});

// Notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.classList.add('notification', `notification-${type}`);
    notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 14px 20px;
    border-radius: 8px;
    color: white;
    font-size: 14px;
    font-weight: 500;
    z-index: 3000;
    max-width: 350px;
    word-wrap: break-word;
    background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#007acc'};
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    transform: translateX(500px);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    opacity: 1;
    animation: notificationSlide 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
`;

    notification.textContent = message;
    document.body.appendChild(notification);

    // Show notification
    setTimeout(() => {
        notification.style.animation = 'notificationSlide 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards';
        notification.style.transform = 'translateX(0)';
    }, 50);

    // Hide and remove notification
    const timeoutId = setTimeout(() => {
        notification.style.transform = 'translateX(500px)';
        notification.style.opacity = '0';

        const removeTimeoutId = setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);

        // Store timeout for cleanup
        notification.removeTimeoutId = removeTimeoutId;
    }, 4000);

    // Store timeout for potential manual cleanup
    notification.timeoutId = timeoutId;
}

// Add keyframe animation to document if not exists
if (!document.getElementById('notification-keyframes')) {
    const style = document.createElement('style');
    style.id = 'notification-keyframes';
    style.textContent = `
    @keyframes notificationSlide {
        from {
            transform: translateX(500px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
    document.head.appendChild(style);
}

// Sidebar toggle
let sidebarCollapsed = false;
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'b') {
        e.preventDefault();
        sidebarCollapsed = !sidebarCollapsed;
        document.getElementById('sidebar').classList.toggle('collapsed', sidebarCollapsed);
    }
});

// Close modals on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal[style*="flex"]');
        modals.forEach(modal => {
            modal.style.display = 'none';
        });
        closeItemDetail();
    }
});
