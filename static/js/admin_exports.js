let exportsData = [];
let products = [];
let customers = [];

async function loadExports() {
    try {
        const response = await fetch('/api/exports');
        const data = await response.json();

        if (data.success) {
            exportsData = data.exports;
            renderExportsTable();
            updateStats();
        } else {
            showAlert('error', 'Error loading data');
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
    }
}

async function loadProducts() {
    try {
        const response = await fetch('/api/products');
        const data = await response.json();
        if (data.success) {
            products = data.products;
        }
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

async function loadCustomers() {
    try {
        const response = await fetch('/api/customers');
        const data = await response.json();
        if (data.success) {
            customers = data.customers;
            const select = document.getElementById('customerSelect');
            if (select) {
                select.innerHTML = '<option value="">Select Customer</option>' + 
                    customers.map(c => `<option value="${c.id}">${c.name} (${c.phone || '-'})</option>`).join('');
            }
        }
    } catch (error) {
        console.error('Error loading customers:', error);
    }
}

function renderExportsTable() {
    const tbody = document.getElementById('exportsTableBody');

    if (exportsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No export orders found</td></tr>';
        return;
    }

    tbody.innerHTML = exportsData.map(exp => `
        <tr>
            <td><strong>${exp.code}</strong></td>
            <td>${exp.customer_name || 'Retail customer'}</td>
            <td class="text-end"><strong>${Number(exp.total_amount).toLocaleString('en-US')} VND</strong></td>
            <td><span class="badge bg-${exp.status === 'completed' ? 'success' : 'warning'}">${exp.status === 'completed' ? 'Completed' : 'Processing'}</span></td>
            <td>${new Date(exp.created_at).toLocaleDateString('en-US')}</td>
            <td>${exp.notes || '-'}</td>
            <td>
                <button class="btn btn-sm btn-info" onclick="viewExport(${exp.id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function updateStats() {
    document.getElementById('totalExports').textContent = exportsData.length;
    const completed = exportsData.filter(e => e.status === 'completed').length;
    document.getElementById('completedExports').textContent = completed;

    const total = exportsData.reduce((sum, e) => sum + Number(e.total_amount), 0);
    document.getElementById('totalRevenue').textContent = total.toLocaleString('en-US') + ' VND';
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

// Create Export Logic
function addExportItemRow() {
    const tbody = document.getElementById('exportItemsBody');
    const row = document.createElement('tr');
    
    const productOptions = products.map(p => `<option value="${p.id}" data-price="${p.price}">${p.code} - ${p.name} (Stock: ${p.stock_quantity})</option>`).join('');
    
    row.innerHTML = `
        <td>
            <select class="form-select product-select" name="product_id" required onchange="updatePrice(this)">
                <option value="">Select Product</option>
                ${productOptions}
            </select>
        </td>
        <td>
            <input type="number" class="form-control" name="quantity" value="1" min="1" required>
        </td>
        <td>
            <input type="number" class="form-control" name="unit_price" value="0" min="0" required>
        </td>
        <td>
            <button type="button" class="btn btn-danger btn-sm" onclick="this.closest('tr').remove()">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    tbody.appendChild(row);
}

function updatePrice(select) {
    const price = select.options[select.selectedIndex].dataset.price;
    const row = select.closest('tr');
    if (price) {
        row.querySelector('[name="unit_price"]').value = price;
    }
}

async function submitExport() {
    const form = document.getElementById('createExportForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const customer_id = form.querySelector('[name="customer_id"]').value;
    const notes = form.querySelector('[name="notes"]').value;
    
    const items = [];
    form.querySelectorAll('#exportItemsBody tr').forEach(row => {
        items.push({
            product_id: row.querySelector('[name="product_id"]').value,
            quantity: row.querySelector('[name="quantity"]').value,
            unit_price: row.querySelector('[name="unit_price"]').value
        });
    });

    if (items.length === 0) {
        alert('Please add at least one item');
        return;
    }

    try {
        const response = await fetch('/api/exports', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ customer_id, notes, items })
        });
        
        const data = await response.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('createExportModal')).hide();
            form.reset();
            document.getElementById('exportItemsBody').innerHTML = '';
            loadExports();
            showAlert('success', 'Export created successfully');
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function viewExport(id) {
    try {
        const response = await fetch(`/api/exports/${id}`);
        const data = await response.json();
        
        if (data.success) {
            const t = data.transaction;
            document.getElementById('viewExportCode').textContent = t.code;
            document.getElementById('viewExportCustomer').textContent = t.customer_name;
            document.getElementById('viewExportDate').textContent = new Date(t.created_at).toLocaleString();
            document.getElementById('viewExportStatus').textContent = t.status;
            document.getElementById('viewExportTotal').textContent = Number(t.total_amount).toLocaleString('en-US') + ' VND';
            document.getElementById('viewExportNotes').textContent = t.notes || '-';
            
            const tbody = document.getElementById('viewExportItemsBody');
            tbody.innerHTML = data.details.map(d => `
                <tr>
                    <td>${d.product_code}</td>
                    <td>${d.product_name}</td>
                    <td class="text-end">${d.quantity}</td>
                    <td class="text-end">${Number(d.unit_price).toLocaleString('en-US')}</td>
                    <td class="text-end">${Number(d.total_price).toLocaleString('en-US')}</td>
                </tr>
            `).join('');
            
            new bootstrap.Modal(document.getElementById('viewExportModal')).show();
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadExports();
    loadProducts();
    loadCustomers();
});
