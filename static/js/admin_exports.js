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
            showAlert('error', 'Lỗi khi tải dữ liệu');
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
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
                select.innerHTML = '<option value="">Chọn khách hàng</option>' + 
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
        tbody.innerHTML = `
            <tr><td colspan="7">
                <div class="empty-state empty-state--compact">
                    <div class="empty-state__icon"><i class="fa-solid fa-truck-ramp-box"></i></div>
                    <p class="empty-state__title">Chưa có đơn xuất hàng</p>
                    <p class="empty-state__description">Các đơn xuất hàng sẽ hiển thị tại đây sau khi được tạo.</p>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = exportsData.map(exp => {
        const isCompleted = exp.status === 'completed';
        const actions = [
            { label: 'Xem chi tiết', icon: 'fa-solid fa-eye', action: 'viewExport' },
        ];
        return `
        <tr>
            <td><strong>${banleUI.escapeHtml(exp.code)}</strong></td>
            <td>${banleUI.escapeHtml(exp.customer_name || 'Khách lẻ')}</td>
            <td class="text-end"><strong>${banleUI.formatVND(exp.total_amount)}</strong></td>
            <td>${banleUI.statusPill(isCompleted ? 'Hoàn thành' : 'Đang xử lý', isCompleted ? 'green' : 'orange')}</td>
            <td>${banleUI.formatDateVN(exp.created_at)}</td>
            <td>${banleUI.escapeHtml(exp.notes || '—')}</td>
            <td class="table__actions">${banleUI.renderRowActions(exp.id, actions)}</td>
        </tr>
    `;
    }).join('');

    banleUI.bindRowActions(tbody);
}

function updateStats() {
    document.getElementById('totalExports').textContent = exportsData.length;
    const completed = exportsData.filter(e => e.status === 'completed').length;
    document.getElementById('completedExports').textContent = completed;

    const total = exportsData.reduce((sum, e) => sum + Number(e.total_amount), 0);
    document.getElementById('totalRevenue').textContent = banleUI.formatVND(total);
}

function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    const alertClass = type === 'success' ? 'success' : (type === 'warning' ? 'warning' : 'danger');
    alertDiv.className = `alert alert-${alertClass}`;
    alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 320px; max-width: 480px; padding: 12px 16px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    alertDiv.innerHTML = `
        <strong>${type === 'success' ? '✅ ' : type === 'warning' ? '⚠️ ' : '❌ '}</strong>
        <span>${escapeHtml(message)}</span>
        <button type="button" style="float: right; background: none; border: none; font-size: 18px; cursor: pointer; line-height: 1;" onclick="this.parentElement.remove()" aria-label="Đóng">&times;</button>
    `;
    document.body.appendChild(alertDiv);
    setTimeout(() => { alertDiv.style.opacity = '0'; setTimeout(() => alertDiv.remove(), 300); }, 5000);
}

function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function formatDateTime(iso) {
    if (!iso) return '—';
    return banleUI.formatDateTimeVN(iso);
}

// Create Export Logic
function addExportItem() {
    const list = document.getElementById('exportItemsList');
    if (!list) return;

    // Clear placeholder if present
    const placeholder = list.querySelector('p[style*="text-muted"]');
    if (placeholder) placeholder.remove();

    const productOptions = products.map(p => `<option value="${p.id}" data-price="${p.price}">${p.code} - ${p.name} (Tồn: ${p.stock_quantity})</option>`).join('');

    const row = document.createElement('div');
    row.className = 'export-item-row';
    row.style.cssText = 'display: grid; grid-template-columns: 2fr 100px 120px 40px; gap: 8px; margin-bottom: 8px; align-items: center;';
    row.innerHTML = `
        <select class="form-select form-select-sm" name="product_id" required onchange="updatePrice(this)">
            <option value="">Chọn sản phẩm</option>
            ${productOptions}
        </select>
        <input type="number" class="form-control form-control-sm" name="quantity" value="1" min="1" required>
        <input type="number" class="form-control form-control-sm" name="unit_price" value="0" min="0" required>
        <button type="button" class="btn btn--danger btn--sm" onclick="this.closest('.export-item-row').remove()" aria-label="Xóa">
            <i class="fa-solid fa-times"></i>
        </button>
    `;
    list.appendChild(row);
}

function updatePrice(select) {
    const price = select.options[select.selectedIndex].dataset.price;
    if (!price) return;
    const row = select.closest('.export-item-row');
    if (row) {
        const priceInput = row.querySelector('[name="unit_price"]');
        if (priceInput && (!priceInput.value || priceInput.value === '0')) {
            priceInput.value = price;
        }
    }
}

async function saveExport() {
    const form = document.getElementById('createExportForm');
    if (!form) return;
    if (!form.checkValidity()) { form.reportValidity(); return; }

    const customer_id = form.querySelector('[name="customer_id"]')?.value;
    const notes = form.querySelector('[name="notes"]')?.value?.trim() || '';

    const items = [];
    document.querySelectorAll('#exportItemsList .export-item-row').forEach(row => {
        const productId = row.querySelector('[name="product_id"]')?.value;
        const quantity = row.querySelector('[name="quantity"]')?.value;
        const unitPrice = row.querySelector('[name="unit_price"]')?.value;
        if (productId && quantity && unitPrice !== '') {
            items.push({
                product_id: parseInt(productId, 10),
                quantity: parseFloat(quantity),
                unit_price: parseFloat(unitPrice)
            });
        }
    });

    if (items.length === 0) {
        showAlert('error', 'Vui lòng thêm ít nhất một sản phẩm');
        return;
    }

    const submitBtn = form.closest('.modal')?.querySelector('.btn--primary');
    const originalText = submitBtn?.innerHTML;
    if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...'; }

    try {
        const response = await fetch('/api/exports', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
            },
            credentials: 'same-origin',
            body: JSON.stringify({ customer_id, notes, items })
        });
        const data = await response.json();

        if (data.success) {
            closeModal('createExportModal');
            form.reset();
            const list = document.getElementById('exportItemsList');
            if (list) list.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 16px;">Chưa có sản phẩm nào.</p>';
            loadExports();
            showAlert('success', 'Tạo đơn xuất hàng thành công');
        } else {
            showAlert('error', data.message || 'Lỗi tạo đơn xuất');
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    } finally {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = originalText; }
    }
}

async function viewExport(id) {
    try {
        const response = await fetch(`/api/exports/${id}`, { credentials: 'same-origin' });
        const data = await response.json();

        if (!data.success) { showAlert('error', data.message); return; }

        const t = data.transaction;
        setText('viewExportCode', t?.code || '-');
        setText('viewExportCustomer', t?.customer_name || '-');
        setText('viewExportDate', formatDateTime(t?.created_at));
        setText('viewExportStatus', t?.status || '-');
        setText('viewExportTotal', Number(t?.total_amount || 0).toLocaleString('en-US') + ' VND');
        setText('viewExportNotes', t?.notes || '-');

        const itemsContainer = document.getElementById('viewExportItems');
        if (itemsContainer) {
            const details = data.details || [];
            if (details.length === 0) {
                itemsContainer.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 16px;">Không có sản phẩm</p>';
            } else {
                itemsContainer.innerHTML = `
                    <table class="table" style="margin: 0;">
                        <thead>
                            <tr>
                                <th>Mã SP</th>
                                <th>Tên SP</th>
                                <th style="text-align: right;">SL</th>
                                <th style="text-align: right;">Đơn giá</th>
                                <th style="text-align: right;">Thành tiền</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${details.map(d => `
                                <tr>
                                    <td>${escapeHtml(d.product_code)}</td>
                                    <td>${escapeHtml(d.product_name)}</td>
                                    <td style="text-align: right;">${d.quantity}</td>
                                    <td style="text-align: right;">${Number(d.unit_price).toLocaleString('en-US')}</td>
                                    <td style="text-align: right;"><strong>${Number(d.total_price).toLocaleString('en-US')}</strong></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }
        }

        openModal('viewExportModal');
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadExports();
    loadProducts();
    loadCustomers();
});
