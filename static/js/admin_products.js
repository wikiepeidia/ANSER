let productsData = [];
let editingId = null;

async function loadProducts() {
    try {
        const response = await fetch('/api/products');
        const data = await response.json();

        if (data.success) {
            productsData = data.products;
            renderProductsTable();
        } else {
            showAlert('error', 'Failed to load data');
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
    }
}

function renderProductsTable() {
    const tbody = document.getElementById('productsTableBody');

    if (productsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No products found</td></tr>';
        syncProductsTableTheme();
        return;
    }

    tbody.innerHTML = productsData
        .map(
            product => `
        <tr>
            <td><strong>${product.code}</strong></td>
            <td>${product.name}</td>
            <td>${product.category || '-'}</td>
            <td>${product.unit}</td>
            <td>${Number(product.price).toLocaleString('en-US')} VND</td>
            <td><span class="badge bg-${product.stock_quantity > 0 ? 'success' : 'danger'}">${product.stock_quantity}</span></td>
            <td>${product.description || '-'}</td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="editProduct(${product.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteProduct(${product.id}, '${product.code}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `
        )
        .join('');
    // Re-apply inline row backgrounds to the new table rows
    syncProductsTableTheme();
}

function openAddProductModal() {
    editingId = null;
    document.getElementById('productModalTitle').textContent = 'Add Product';
    document.getElementById('productId').value = '';
    document.getElementById('productCode').value = '';
    document.getElementById('productCode').disabled = false;
    document.getElementById('productName').value = '';
    document.getElementById('productCategory').value = '';
    document.getElementById('productUnit').value = 'pcs';
    document.getElementById('productPrice').value = '0';
    document.getElementById('productStock').value = '0';
    document.getElementById('productDescription').value = '';
    new bootstrap.Modal(document.getElementById('productModal')).show();
}

function editProduct(id) {
    const product = productsData.find(p => p.id === id);
    if (!product) return;

    editingId = id;
    document.getElementById('productModalTitle').textContent = 'Edit Product';
    document.getElementById('productId').value = product.id;
    document.getElementById('productCode').value = product.code;
    document.getElementById('productCode').disabled = true;
    document.getElementById('productName').value = product.name;
    document.getElementById('productCategory').value = product.category || '';
    document.getElementById('productUnit').value = product.unit;
    document.getElementById('productPrice').value = product.price;
    document.getElementById('productStock').value = product.stock_quantity;
    document.getElementById('productDescription').value = product.description || '';
    new bootstrap.Modal(document.getElementById('productModal')).show();
}

async function saveProduct() {
    const code = document.getElementById('productCode').value.trim();
    const name = document.getElementById('productName').value.trim();
    const category = document.getElementById('productCategory').value.trim();
    const unit = document.getElementById('productUnit').value.trim();
    const price = parseFloat(document.getElementById('productPrice').value);
    const stock_quantity = parseInt(document.getElementById('productStock').value, 10);
    const description = document.getElementById('productDescription').value.trim();

    if (!code || !name) {
           showAlert('error', 'Please fill in the required fields');
        return;
    }

    const payload = { code, name, category, unit, price, stock_quantity, description };

    try {
        let response;
        if (editingId) {
            response = await fetch(`/api/products/${editingId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            response = await fetch('/api/products', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        const data = await response.json();

            if (data.success) {
                showAlert('success', editingId ? 'Update successful!' : 'Product added successfully!');
            bootstrap.Modal.getInstance(document.getElementById('productModal')).hide();
            loadProducts();
        } else {
            showAlert('error', data.message);
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function deleteProduct(id, code) {
    if (!confirm(`Are you sure you want to delete product "${code}"?`)) return;

    try {
        const response = await fetch(`/api/products/${id}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', 'Deleted successfully!');
            loadProducts();
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

document.addEventListener('DOMContentLoaded', loadProducts);

// Fallback: apply inline table row backgrounds in case style overrides still force light backgrounds
function syncProductsTableTheme() {
    const table = document.querySelector('.products-page .table');
    if (!table) return;
    const styles = getComputedStyle(document.documentElement);
    const bg = styles.getPropertyValue('--surface-100') || '#ffffff';
    const altBg = styles.getPropertyValue('--surface-200') || '#f8fafc';
    table.style.setProperty('background', bg.trim(), 'important');
    [...table.querySelectorAll('tbody tr')].forEach((row, idx) => {
        const color = (idx % 2 === 0) ? bg.trim() : altBg.trim();
        row.style.setProperty('background', color, 'important');
    });
}

const _prodThemeObserver = new MutationObserver((mutations) => {
    const html = document.documentElement;
    const changed = mutations.some(m => m.attributeName === 'data-theme');
    if (changed) syncProductsTableTheme();
});
_prodThemeObserver.observe(document.documentElement, { attributes: true });
document.addEventListener('DOMContentLoaded', syncProductsTableTheme);

// Observe the tbody content so when rows are replaced dynamically we re-apply the inline theme styles
const _productsTbodyObserver = new MutationObserver((mutations) => {
    const changed = mutations.some(m => (m.addedNodes && m.addedNodes.length) || (m.removedNodes && m.removedNodes.length));
    if (changed) syncProductsTableTheme();
});

document.addEventListener('DOMContentLoaded', () => {
    const tbody = document.querySelector('.products-page .table tbody');
    if (tbody) _productsTbodyObserver.observe(tbody, { childList: true, subtree: false });
});
