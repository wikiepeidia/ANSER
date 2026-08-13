let customersData = [];
let editingId = null;

async function loadCustomers() {
    try {
        const response = await fetch('/api/customers');
        const data = await response.json();

        if (data.success) {
            customersData = data.customers;
            renderCustomersTable();
        } else {
            banleUI.showAlert('error', 'Không tải được dữ liệu');
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

function renderCustomersTable() {
    const tbody = document.getElementById('customersTableBody');

    if (customersData.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="7">
                <div class="empty-state empty-state--compact">
                    <div class="empty-state__icon"><i class="fa-solid fa-users"></i></div>
                    <p class="empty-state__title">Chưa có khách hàng</p>
                    <p class="empty-state__description">Nhấn "Thêm khách hàng" ở góc trên để bắt đầu.</p>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = customersData.map(customer => {
        const actions = [
            { label: 'Sửa', icon: 'fa-solid fa-pen', action: 'editCustomer' },
            { divider: true },
            { label: 'Xóa', icon: 'fa-solid fa-trash', action: 'deleteCustomer', danger: true },
        ];
        return `
        <tr>
            <td><strong>${banleUI.escapeHtml(customer.code)}</strong></td>
            <td>${banleUI.escapeHtml(customer.name)}</td>
            <td>${banleUI.escapeHtml(customer.phone || '—')}</td>
            <td>${banleUI.escapeHtml(customer.email || '—')}</td>
            <td>${banleUI.escapeHtml(customer.address || '—')}</td>
            <td>${banleUI.escapeHtml(customer.notes || '—')}</td>
            <td class="table__actions">${banleUI.renderRowActions(customer.id, actions)}</td>
        </tr>
    `;
    }).join('');

    if (window.banleUI && window.banleUI.bindRowActions) {
        window.banleUI.bindRowActions(tbody);
    }
}

function openAddCustomerModal() {
    editingId = null;
    document.getElementById('customerModalTitle').textContent = 'Thêm khách hàng';
    document.getElementById('customerId').value = '';
    document.getElementById('customerCode').value = '';
    document.getElementById('customerCode').disabled = false;
    document.getElementById('customerName').value = '';
    document.getElementById('customerPhone').value = '';
    document.getElementById('customerEmail').value = '';
    document.getElementById('customerAddress').value = '';
    document.getElementById('customerNotes').value = '';
    openModal('customerModal');
}

function editCustomer(id) {
    const customer = customersData.find(c => c.id === id);
    if (!customer) return;

    editingId = id;
    document.getElementById('customerModalTitle').textContent = 'Sửa khách hàng';
    document.getElementById('customerId').value = customer.id;
    document.getElementById('customerCode').value = customer.code;
    document.getElementById('customerCode').disabled = true;
    document.getElementById('customerName').value = customer.name;
    document.getElementById('customerPhone').value = customer.phone || '';
    document.getElementById('customerEmail').value = customer.email || '';
    document.getElementById('customerAddress').value = customer.address || '';
    document.getElementById('customerNotes').value = customer.notes || '';
    openModal('customerModal');
}

async function saveCustomer() {
    const code = document.getElementById('customerCode').value.trim();
    const name = document.getElementById('customerName').value.trim();
    const phone = document.getElementById('customerPhone').value.trim();
    const email = document.getElementById('customerEmail').value.trim();
    const address = document.getElementById('customerAddress').value.trim();
    const notes = document.getElementById('customerNotes').value.trim();

    if (!code || !name) {
        banleUI.showAlert('error', 'Vui lòng điền các trường bắt buộc');
        return;
    }

    const payload = { code, name, phone, email, address, notes };

    try {
        let response;
        if (editingId) {
            response = await fetch(`/api/customers/${editingId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            response = await fetch('/api/customers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        const data = await response.json();

        if (data.success) {
            banleUI.showAlert('success', editingId ? 'Cập nhật thành công!' : 'Thêm khách hàng thành công!');
            closeModal('customerModal');
            loadCustomers();
        } else {
            banleUI.showAlert('error', data.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function deleteCustomer(id, code) {
    if (!confirm(`Bạn có chắc chắn muốn xóa khách hàng "${code}"?`)) return;

    try {
        const response = await fetch(`/api/customers/${id}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            banleUI.showAlert('success', 'Xóa thành công!');
            loadCustomers();
        } else {
            banleUI.showAlert('error', data.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}


document.addEventListener('DOMContentLoaded', loadCustomers);
