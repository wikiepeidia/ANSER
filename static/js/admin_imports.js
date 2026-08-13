// Global state
let importsData = [];
let products = [];

// ===== Data loading =====
async function loadImports() {
    try {
        const response = await fetch('/api/imports', { credentials: 'same-origin' });
        const data = await response.json();
        if (data.success) {
            importsData = data.imports || [];
            renderImportsTable();
            updateStats();
        } else {
            showAlert('error', data.message || 'Lỗi tải dữ liệu');
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function loadProducts() {
    try {
        const response = await fetch('/api/products', { credentials: 'same-origin' });
        const data = await response.json();
        if (data.success) {
            products = data.products || [];
        }
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

// ===== Rendering =====
function renderImportsTable() {
    const tbody = document.getElementById('importsTableBody');
    if (!tbody) return;

    if (importsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-secondary);">Chưa có phiếu nhập nào</td></tr>';
        return;
    }

    tbody.innerHTML = importsData.map(imp => {
        const isCompleted = imp.status === 'completed';
        const actions = [
            { label: 'Xem chi tiết', icon: 'fa-solid fa-eye', action: 'viewImport' },
        ];
        return `
        <tr>
            <td><strong>${banleUI.escapeHtml(imp.code)}</strong></td>
            <td>${banleUI.escapeHtml(imp.supplier_name || '—')}</td>
            <td class="text-end"><strong>${banleUI.formatVND(imp.total_amount)}</strong></td>
            <td>${banleUI.statusPill(isCompleted ? 'Hoàn thành' : 'Đang xử lý', isCompleted ? 'green' : 'orange')}</td>
            <td>${banleUI.formatDateVN(imp.created_at)}</td>
            <td>${banleUI.escapeHtml(imp.notes || '—')}</td>
            <td class="table__actions">${banleUI.renderRowActions(imp.id, actions)}</td>
        </tr>
    `;
    }).join('');

    if (window.banleUI && window.banleUI.bindRowActions) {
        banleUI.bindRowActions(tbody);
    }
}

function updateStats() {
    const totalEl = document.getElementById('totalImports');
    const completedEl = document.getElementById('completedImports');
    const amountEl = document.getElementById('totalAmount');
    if (totalEl) totalEl.textContent = importsData.length;
    if (completedEl) completedEl.textContent = importsData.filter(i => i.status === 'completed').length;
    if (amountEl) {
        const total = importsData.reduce((sum, i) => sum + Number(i.total_amount || 0), 0);
        amountEl.textContent = total.toLocaleString('en-US') + ' VND';
    }
}

// ===== Create import (modal) =====
function addImportItem() {
    const list = document.getElementById('importItemsList');
    if (!list) return;

    // Clear placeholder if present
    const placeholder = list.querySelector('p.placeholder, p[style*="text-muted"]');
    if (placeholder) placeholder.remove();

    const productOptions = (products || []).map(p =>
        `<option value="${p.id}" data-price="${p.price || 0}">${escapeHtml(p.code)} - ${escapeHtml(p.name)}</option>`
    ).join('');

    const row = document.createElement('div');
    row.className = 'import-item-row';
    row.style.cssText = 'display: grid; grid-template-columns: 2fr 100px 120px 40px; gap: 8px; margin-bottom: 8px; align-items: center;';
    row.innerHTML = `
        <select class="form-select form-select-sm" name="product_id" required onchange="updatePrice(this)">
            <option value="">Chọn sản phẩm</option>
            ${productOptions}
        </select>
        <input type="number" class="form-control form-control-sm" name="quantity" value="1" min="1" required>
        <input type="number" class="form-control form-control-sm" name="unit_price" value="0" min="0" required>
        <button type="button" class="btn btn--danger btn--sm" onclick="this.closest('.import-item-row').remove()" aria-label="Xóa">
            <i class="fa-solid fa-times"></i>
        </button>
    `;
    list.appendChild(row);
}

function updatePrice(select) {
    const opt = select.options[select.selectedIndex];
    const price = opt?.dataset?.price;
    if (!price) return;
    const row = select.closest('.import-item-row');
    const priceInput = row?.querySelector('[name="unit_price"]');
    if (priceInput && (!priceInput.value || priceInput.value === '0')) {
        priceInput.value = price;
    }
}

async function saveImport() {
    const form = document.getElementById('createImportForm');
    if (!form) return;
    if (!form.checkValidity()) { form.reportValidity(); return; }

    const supplier_name = form.querySelector('[name="supplier_name"]')?.value?.trim() || '';
    const notes = form.querySelector('[name="notes"]')?.value?.trim() || '';

    const items = [];
    document.querySelectorAll('#importItemsList .import-item-row').forEach(row => {
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
        showAlert('warning', 'Vui lòng thêm ít nhất một sản phẩm');
        return;
    }

    const submitBtn = form.closest('.modal')?.querySelector('.btn--primary');
    const originalText = submitBtn?.innerHTML;
    if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...'; }

    try {
        const response = await fetch('/api/imports', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
            },
            credentials: 'same-origin',
            body: JSON.stringify({ supplier_name, notes, items })
        });
        const data = await response.json();

        if (data.success) {
            closeModal('createImportModal');
            form.reset();
            const list = document.getElementById('importItemsList');
            if (list) list.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 16px;">Chưa có sản phẩm nào. Click "Thêm sản phẩm" để bắt đầu.</p>';
            await loadImports();

            const successMessage = document.getElementById('successMessage');
            if (successMessage) successMessage.textContent = buildImportSuccessMessage(data, items.length, supplier_name, null);
            openModal('successModal');
        } else {
            showAlert('error', data.message || 'Lỗi tạo phiếu nhập');
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    } finally {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = originalText; }
    }
}

// ===== View import =====
async function viewImport(id) {
    try {
        const response = await fetch(`/api/imports/${id}`, { credentials: 'same-origin' });
        const data = await response.json();
        if (!data.success) { showAlert('error', data.message); return; }

        const t = data.transaction;
        setText('viewImportCode', t?.code || '-');
        setText('viewImportSupplier', t?.supplier_name || '-');
        setText('viewImportDate', formatDateTime(t?.created_at));
        setText('viewImportStatus', t?.status || '-');
        setText('viewImportTotal', Number(t?.total_amount || 0).toLocaleString('en-US') + ' VND');

        // Render items into the existing wrapper (HTML uses #viewImportItems)
        const itemsContainer = document.getElementById('viewImportItems');
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

        openModal('viewImportModal');
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
    }
}

// ===== OCR import =====
function processOCR() {
    const fileInput = document.getElementById('ocrFileInput');
    const file = fileInput?.files?.[0];
    if (!file) { showAlert('warning', 'Vui lòng chọn file hóa đơn trước'); return; }

    const btn = document.getElementById('ocrProcessBtn');
    const originalText = btn?.innerHTML;
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xử lý...'; }

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/brain/ocr', {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '' },
        credentials: 'same-origin'
    })
    .then(r => r.json())
    .then(ocrResult => {
        if (!ocrResult.success) throw new Error(ocrResult.error || 'OCR thất bại');
        const items = extractOcrItems(ocrResult.data || {});
        if (items.length === 0) { showAlert('warning', 'Không nhận diện được sản phẩm nào từ hóa đơn'); return; }

        const payload = {
            supplier_name: ocrResult.data?.invoice?.vendor_name || ocrResult.data?.vendor_name || 'OCR Import',
            notes: 'Nhập tự động qua OCR',
            items
        };
        return fetch('/api/imports', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '' },
            credentials: 'same-origin',
            body: JSON.stringify(payload)
        });
    })
    .then(r => r?.json())
    .then(importData => {
        if (!importData) return;
        if (importData.success) {
            closeModal('ocrImportModal');
            if (fileInput) fileInput.value = '';
            loadImports();
            const successMessage = document.getElementById('successMessage');
            if (successMessage) successMessage.textContent = buildImportSuccessMessage(importData, 0, 'OCR Import', 'OCR');
            openModal('successModal');
        } else {
            showAlert('error', importData.message || 'Lỗi tạo phiếu nhập');
        }
    })
    .catch(error => showAlert('error', 'Lỗi OCR: ' + error.message))
    .finally(() => {
        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    });
}

function extractOcrItems(data) {
    const raw = data?.products || data?.items || data?.invoice?.items || data?.invoice?.products || data?.data?.products || [];
    return raw.map(item => ({
        product_id: null,
        product_name: item.product_name || item.name || item.product || '',
        quantity: parseFloat(item.quantity || item.qty || item.count || 1),
        unit_price: parseFloat(item.unit_price || item.unit || item.price || 0)
    })).filter(i => i.product_name);
}

// ===== Excel import =====
function processExcelImport() {
    const fileInput = document.getElementById('importExcelInput');
    const file = fileInput?.files?.[0];
    if (!file) { showAlert('warning', 'Vui lòng chọn file Excel trước'); return; }

    const btn = document.querySelector('button[onclick="processExcelImport()"]');
    const originalText = btn?.innerHTML;
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xử lý...'; }

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/imports/upload/excel', {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '' },
        credentials: 'same-origin'
    })
    .then(r => r.json())
    .then(parseData => {
        if (!parseData.success) throw new Error(parseData.error || 'Lỗi đọc file Excel');
        const items = (parseData.items || [])
            .map(i => ({
                product_code: (i.product_code || '').toString().trim(),
                product_name: (i.product_name || '').toString().trim(),
                quantity: parseFloat(i.quantity || 0),
                unit_price: parseFloat(i.unit_price || 0)
            }))
            .filter(i => i.product_code && i.quantity > 0 && i.unit_price > 0);

        if (items.length === 0) { showAlert('warning', 'File không có dòng sản phẩm hợp lệ (cần mã, số lượng > 0, đơn giá > 0)'); return null; }

        return fetch('/api/imports', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '' },
            credentials: 'same-origin',
            body: JSON.stringify({
                supplier_name: 'Excel Import',
                notes: 'Nhập từ file Excel',
                items
            })
        });
    })
    .then(r => r?.json())
    .then(importData => {
        if (!importData) return;
        if (importData.success) {
            closeModal('excelImportModal');
            if (fileInput) fileInput.value = '';
            loadImports();
            const successMessage = document.getElementById('successMessage');
            if (successMessage) successMessage.textContent = buildImportSuccessMessage(importData, 0, 'Excel Import', 'Excel');
            openModal('successModal');
        } else {
            showAlert('error', importData.message || 'Lỗi tạo phiếu nhập');
        }
    })
    .catch(error => showAlert('error', 'Lỗi: ' + error.message))
    .finally(() => {
        if (btn) { btn.disabled = false; btn.innerHTML = originalText; }
    });
}

function downloadExcelTemplate() {
    window.location.href = '/api/imports/download/template';
}

// ===== Helpers =====
function buildImportSuccessMessage(data, itemCount, supplierName, source) {
    const updated = data.products_updated || 0;
    const created = data.products_created || 0;
    const parts = [];
    if (updated > 0) parts.push(`${updated} sản phẩm cập nhật tồn kho`);
    if (created > 0) parts.push(`${created} sản phẩm mới được thêm`);
    const summary = parts.length > 0 ? parts.join(', ') : (itemCount > 0 ? `${itemCount} sản phẩm đã xử lý` : 'Phiếu nhập đã được tạo');
    return `${summary}${source ? ` (${source})` : ''}. Nhà cung cấp: ${supplierName || '-'}`;
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

function formatDate(iso) {
    if (!iso) return '—';
    return banleUI.formatDateVN(iso);
}

function formatDateTime(iso) {
    if (!iso) return '—';
    return banleUI.formatDateTimeVN(iso);
}

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    // Enable process buttons when files are selected
    const ocrInput = document.getElementById('ocrFileInput');
    if (ocrInput) {
        ocrInput.addEventListener('change', () => {
            const btn = document.getElementById('ocrProcessBtn');
            if (btn) btn.disabled = !ocrInput.files?.[0];
        });
    }
    const excelInput = document.getElementById('importExcelInput');
    if (excelInput) {
        excelInput.addEventListener('change', () => {
            const btn = document.querySelector('button[onclick="processExcelImport()"]');
            if (btn) btn.disabled = !excelInput.files?.[0];
        });
    }

    loadImports();
    loadProducts();
});
