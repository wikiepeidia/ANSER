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
            showAlert('error', 'Failed to load data');
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
    }
}

function renderCustomersTable() {
    const tbody = document.getElementById('customersTableBody');

    if (customersData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No customers found</td></tr>';
        return;
    }

    tbody.innerHTML = customersData.map(customer => `
        <tr>
            <td><strong>${customer.code}</strong></td>
            <td>${customer.name}</td>
            <td>${customer.phone || '-'}</td>
            <td>${customer.email || '-'}</td>
            <td>${customer.address || '-'}</td>
            <td>${customer.notes || '-'}</td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="editCustomer(${customer.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteCustomer(${customer.id}, '${customer.code}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function openAddCustomerModal() {
    editingId = null;
    document.getElementById('customerModalTitle').textContent = 'Add Customer';
    document.getElementById('customerId').value = '';
    document.getElementById('customerCode').value = '';
    document.getElementById('customerCode').disabled = false;
    document.getElementById('customerName').value = '';
    document.getElementById('customerPhone').value = '';
    document.getElementById('customerEmail').value = '';
    document.getElementById('customerAddress').value = '';
    document.getElementById('customerNotes').value = '';
    new bootstrap.Modal(document.getElementById('customerModal')).show();
}

function editCustomer(id) {
    const customer = customersData.find(c => c.id === id);
    if (!customer) return;

    editingId = id;
    document.getElementById('customerModalTitle').textContent = 'Edit Customer';
    document.getElementById('customerId').value = customer.id;
    document.getElementById('customerCode').value = customer.code;
    document.getElementById('customerCode').disabled = true;
    document.getElementById('customerName').value = customer.name;
    document.getElementById('customerPhone').value = customer.phone || '';
    document.getElementById('customerEmail').value = customer.email || '';
    document.getElementById('customerAddress').value = customer.address || '';
    document.getElementById('customerNotes').value = customer.notes || '';
    new bootstrap.Modal(document.getElementById('customerModal')).show();
}

async function saveCustomer() {
    const code = document.getElementById('customerCode').value.trim();
    const name = document.getElementById('customerName').value.trim();
    const phone = document.getElementById('customerPhone').value.trim();
    const email = document.getElementById('customerEmail').value.trim();
    const address = document.getElementById('customerAddress').value.trim();
    const notes = document.getElementById('customerNotes').value.trim();

    if (!code || !name) {
        showAlert('error', 'Please fill in the required fields');
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
            showAlert('success', editingId ? 'Update successful!' : 'Customer added successfully!');
            bootstrap.Modal.getInstance(document.getElementById('customerModal')).hide();
            loadCustomers();
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function deleteCustomer(id, code) {
    if (!confirm(`Are you sure you want to delete customer "${code}"?`)) return;

    try {
        const response = await fetch(`/api/customers/${id}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Deleted successfully!');
            loadCustomers();
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
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

document.addEventListener('DOMContentLoaded', loadCustomers);
