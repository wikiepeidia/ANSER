document.addEventListener('DOMContentLoaded', () => {
    console.log('Trang cài đặt đã tải');
    
    // Handle "Open editor" buttons
    document.querySelectorAll('.btn-outline-primary:not(.theme-option)').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const cardBody = e.target.closest('.card-body');
            const titleEl = cardBody.querySelector('strong');
            if (!titleEl) return;
            
            const title = titleEl.textContent;
            const sectionTitle = document.querySelector('h3.mb-0')?.textContent;

            if (title === 'Edit Configuration') {
                if (sectionTitle === 'Profile') {
                    showProfileModal();
                } else if (sectionTitle === 'Security') {
                    showSecurityModal();
                } else {
                    showNotification(`Trình chỉnh cấu hình cho ${sectionTitle} đã sẵn sàng.`, 'info');
                }
            } else if (title === 'Sync Data') {
                syncData(sectionTitle);
            } else if (title === 'Workflow Guide') {
                window.open('https://docs.auto-flowai.com', '_blank');
            }
        });
    });
    
    // Handle switches
    document.querySelectorAll('.form-check-input').forEach(input => {
        input.addEventListener('change', async (e) => {
            const label = e.target.closest('.d-flex').querySelector('span').textContent;
            const isChecked = e.target.checked;
            
            try {
                const response = await fetch('/api/settings/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                    },
                    body: JSON.stringify({ setting: label, value: isChecked })
                });
                
                const data = await response.json();
                if (data.success) {
                    showNotification(`${label} ${isChecked ? 'đã bật' : 'đã tắt'}`, 'success');
                } else {
                    throw new Error(data.message);
                }
            } catch (error) {
                showNotification(`Không cập nhật được ${label}`, 'error');
                e.target.checked = !isChecked; // Revert
            }
        });
    });
});

function showProfileModal() {
    // Create and show a modal dynamically
    const modalHtml = `
    <div class="modal fade" id="profileModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Sửa hồ sơ</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="profileForm">
                        <div class="mb-3">
                            <label class="form-label">Họ và tên</label>
                            <input type="text" class="form-control" name="name" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-control" name="email" readonly>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Đóng</button>
                    <button type="button" class="btn btn-primary" onclick="saveProfile()">Lưu thay đổi</button>
                </div>
            </div>
        </div>
    </div>`;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('profileModal'));
    modal.show();
    
    // Fetch current user data to populate form
    fetch('/api/session')
        .then(res => res.json())
        .then(data => {
            if (data.user) {
                document.querySelector('#profileForm [name="name"]').value = data.user.name || '';
                document.querySelector('#profileForm [name="email"]').value = data.user.email || '';
            }
        });
        
    document.getElementById('profileModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

async function saveProfile() {
    const name = document.querySelector('#profileForm [name="name"]').value;
    try {
        const response = await fetch('/api/user/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        if (response.ok) {
            showNotification('Cập nhật hồ sơ thành công', 'success');
            bootstrap.Modal.getInstance(document.getElementById('profileModal')).hide();
            setTimeout(() => location.reload(), 1000);
        }
    } catch (e) {
        showNotification('Lỗi cập nhật hồ sơ', 'error');
    }
}

function showSecurityModal() {
    showNotification('Cài đặt bảo mật được quản lý qua nhà cung cấp danh tính của bạn.', 'info');
}

async function syncData(section) {
    showNotification(`Đang đồng bộ dữ liệu cho ${section}...`, 'info');
    setTimeout(() => {
        showNotification('Đồng bộ hoàn tất.', 'success');
    }, 2000);
}
