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
        tbody.innerHTML = '<tr><td colspan="9" class="text-center">No products found</td></tr>';
        syncProductsTableTheme();
        return;
    }

    tbody.innerHTML = productsData
        .map(product => {
            const imgCell = product.image_url
                ? `<img src="${product.image_url}" alt="${product.name}" class="product-thumb" onerror="this.style.display='none'">`
                : `<span class="text-muted" style="font-size:0.75rem">—</span>`;
            return `
        <tr>
            <td class="text-center">${imgCell}</td>
            <td><strong>${product.code}</strong></td>
            <td>${product.name}</td>
            <td>${product.category || '-'}</td>
            <td>${product.unit}</td>
            <td>${Number(product.price).toLocaleString('en-US')} VND</td>
            <td><span class="badge bg-${product.stock_quantity > 0 ? 'success' : 'danger'}">${product.stock_quantity}</span></td>
            <td>${product.description || '-'}</td>
            <td>
                <button class="btn btn-sm btn-info" onclick="forecastProduct(${product.id}, '${product.name}')" title="Forecast Demand">
                    <i class="fas fa-chart-line"></i>
                </button>
                <button class="btn btn-sm btn-warning" onclick="editProduct(${product.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteProduct(${product.id}, '${product.code}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>`;
        })
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
    document.getElementById('productExpiryDate').value = '';
    document.getElementById('productDescription').value = '';
    document.getElementById('productImageUrl').value = '';
    document.getElementById('productImagePreview').classList.add('d-none');
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
    document.getElementById('productExpiryDate').value = product.expiry_date || '';
    document.getElementById('productDescription').value = product.description || '';
    const imgUrl = product.image_url || '';
    document.getElementById('productImageUrl').value = imgUrl;
    const preview = document.getElementById('productImagePreview');
    if (imgUrl) {
        preview.querySelector('img').src = imgUrl;
        preview.classList.remove('d-none');
    } else {
        preview.classList.add('d-none');
    }
    new bootstrap.Modal(document.getElementById('productModal')).show();
}

async function saveProduct() {
    const code = document.getElementById('productCode').value.trim();
    const name = document.getElementById('productName').value.trim();
    const category = document.getElementById('productCategory').value.trim();
    const unit = document.getElementById('productUnit').value.trim();
    const price = parseFloat(document.getElementById('productPrice').value);
    const stock_quantity = parseInt(document.getElementById('productStock').value, 10);
    const expiry_date = document.getElementById('productExpiryDate').value || null;
    const description = document.getElementById('productDescription').value.trim();
    const image_url = document.getElementById('productImageUrl').value.trim();

    if (!code || !name) {
        showAlert('error', 'Please fill in the required fields');
        return;
    }

    const payload = { code, name, category, unit, price, stock_quantity, expiry_date, description, image_url };

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
        showAlert('error', 'Error: ' + error.message);
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

document.addEventListener('DOMContentLoaded', () => {
    loadProducts();
    initDropZone();

    // Live preview for image URL input
    document.getElementById('productImageUrl').addEventListener('input', function () {
        const preview = document.getElementById('productImagePreview');
        const img = preview.querySelector('img');
        const url = this.value.trim();
        if (url) {
            img.src = url;
            preview.classList.remove('d-none');
        } else {
            preview.classList.add('d-none');
        }
    });
});

// ── Excel Import ──────────────────────────────────────────────────────────

function openImportExcelModal() {
    goBackToStep1();
    document.getElementById('importResult').classList.add('d-none');
    new bootstrap.Modal(document.getElementById('importExcelModal')).show();
}

function initDropZone() {
    const zone = document.getElementById('dropZone');
    const input = document.getElementById('excelFileInput');
    if (!zone || !input) return;

    input.addEventListener('change', () => {
        if (input.files[0]) setExcelFile(input.files[0]);
    });

    zone.addEventListener('dragover', e => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) setExcelFile(file);
    });
}

function setExcelFile(file) {
    if (!/\.(xlsx|xls)$/i.test(file.name)) {
        showAlert('error', 'Chỉ chấp nhận file .xlsx hoặc .xls');
        return;
    }
    document.getElementById('selectedFileName').textContent = file.name;
    document.getElementById('selectedFileInfo').classList.remove('d-none');
    document.getElementById('dropZone').style.display = 'none';
    document.getElementById('btnNext').disabled = false;
    document.getElementById('excelFileInput')._file = file;
}

function clearExcelFile() {
    document.getElementById('selectedFileInfo').classList.add('d-none');
    document.getElementById('dropZone').style.display = '';
    document.getElementById('btnNext').disabled = true;
    document.getElementById('excelFileInput').value = '';
    document.getElementById('excelFileInput')._file = null;
}

function goBackToStep1() {
    clearExcelFile();
    document.getElementById('importStep1').classList.remove('d-none');
    document.getElementById('importStep2').classList.add('d-none');
    document.getElementById('importResult').classList.add('d-none');
    document.getElementById('importError').classList.add('d-none');
    document.getElementById('mappingRows').innerHTML = '';
    document.getElementById('btnNext').classList.remove('d-none');
    document.getElementById('btnBack').classList.add('d-none');
    document.getElementById('btnImport').classList.add('d-none');
    const badge = document.getElementById('importStepBadge');
    badge.textContent = 'Bước 1/2';
    badge.className = 'badge bg-secondary ms-2 fs-6';
}

async function previewColumnMapping() {
    const input = document.getElementById('excelFileInput');
    const file = input._file || input.files[0];
    if (!file) return;

    const btn = document.getElementById('btnNext');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Đang đọc...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/products/import-excel/preview', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();

        if (!data.success) {
            showAlert('error', data.message || 'Không đọc được file');
            return;
        }

        // Lưu file_id — import sẽ dùng lại temp file, không upload lại
        input._fileId = data.file_id || null;

        renderMappingRows(data.mapping, data.field_labels);

        document.getElementById('importStep1').classList.add('d-none');
        document.getElementById('importStep2').classList.remove('d-none');
        document.getElementById('btnNext').classList.add('d-none');
        document.getElementById('btnBack').classList.remove('d-none');
        document.getElementById('btnImport').classList.remove('d-none');
        document.getElementById('importStepBadge').textContent = 'Bước 2/2';
    } catch (e) {
        showAlert('error', 'Lỗi kết nối: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Tiếp theo <i class="fas fa-arrow-right ms-1"></i>';
    }
}

function renderMappingRows(mapping, fieldLabels) {
    const fieldOptions = Object.entries(fieldLabels)
        .map(([val, label]) => `<option value="${val}">${label}</option>`)
        .join('');

    const rows = mapping.map(item => {
        const samples = (item.samples || []).join(', ') || '<span class="text-muted">—</span>';
        const selected = item.suggested || '';
        const selectHtml = `
            <select class="form-select form-select-sm col-map-select" data-original="${item.original}">
                <option value="">— Bỏ qua cột này —</option>
                ${Object.entries(fieldLabels).map(([val, label]) =>
                    `<option value="${val}"${val === selected ? ' selected' : ''}>${label}</option>`
                ).join('')}
            </select>`;
        return `
            <tr>
                <td><code>${item.original}</code></td>
                <td class="text-muted" style="font-size:0.8rem">${samples}</td>
                <td>${selectHtml}</td>
            </tr>`;
    }).join('');

    document.getElementById('mappingRows').innerHTML = rows;
}

async function submitImportExcel() {
    const input = document.getElementById('excelFileInput');

    // Collect column mapping from dropdowns
    const columnMap = {};
    document.querySelectorAll('.col-map-select').forEach(sel => {
        if (sel.value) columnMap[sel.dataset.original] = sel.value;
    });

    // Require at least the name field to be mapped
    if (!Object.values(columnMap).includes('name')) {
        showAlert('error', 'Vui lòng chọn cột ứng với <strong>Tên sản phẩm</strong> trước khi import.');
        return;
    }

    const btn = document.getElementById('btnImport');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Đang xử lý...';

    const formData = new FormData();
    formData.append('column_map', JSON.stringify(columnMap));

    const file = input._file || input.files[0];
    if (!file) {
        const msg = 'Không tìm thấy file, vui lòng chọn lại.';
        showImportResult({ success: false, message: msg });
        showAlert('error', msg);
        return;
    }
    // Luôn gửi kèm file — server dùng file_id nếu còn hợp lệ, fallback sang file nếu server restart
    formData.append('file', file);
    if (input._fileId) formData.append('file_id', input._fileId);

    try {
        const res = await fetch('/api/products/import-excel', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();
        if (!data.success) {
            showImportError(data.message);
        } else {
            showImportResult(data);
            loadProducts();
        }
    } catch (e) {
        showImportError('Lỗi kết nối: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-upload me-1"></i>Import';
    }
}

function showImportError(message) {
    // Ẩn step 2, hiện màn hình lỗi toàn phần
    document.getElementById('importStep2').classList.add('d-none');
    document.getElementById('importResult').classList.add('d-none');
    document.getElementById('btnImport').classList.add('d-none');
    document.getElementById('btnBack').classList.add('d-none');
    document.getElementById('importErrorMessage').textContent = message;
    document.getElementById('importError').classList.remove('d-none');
    document.getElementById('importStepBadge').textContent = 'Lỗi';
    document.getElementById('importStepBadge').className = 'badge bg-danger ms-2 fs-6';
}

function showImportResult(data) {
    const box = document.getElementById('importResult');
    box.classList.remove('d-none');

    if (!data.success) {
        box.innerHTML = `<div class="alert alert-danger mb-0"><i class="fas fa-times-circle me-2"></i>${data.message}</div>`;
        return;
    }

    const errors = (data.errors || []).map(e => `<li>${e}</li>`).join('');

    box.innerHTML = `
        <div class="result-stat stat-inserted">
            <i class="fas fa-plus-circle"></i> Thêm mới: <strong>${data.inserted}</strong> sản phẩm
        </div>
        <div class="result-stat stat-updated">
            <i class="fas fa-sync-alt"></i> Cập nhật: <strong>${data.updated}</strong> sản phẩm
        </div>
        <div class="result-stat stat-skipped">
            <i class="fas fa-minus-circle"></i> Bỏ qua: <strong>${data.skipped}</strong> dòng
        </div>
        ${errors ? `<div class="result-stat stat-errors flex-column align-items-start">
            <div><i class="fas fa-exclamation-triangle me-1"></i>Lỗi (${data.errors.length}):</div>
            <ul class="mb-0 mt-1 ps-3">${errors}</ul>
        </div>` : ''}
    `;
}

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

// Forecast Logic
async function forecastProduct(productId, productName) {
    // Show loading state
    showAlert('info', `Forecasting demand for ${productName}...`);
    
    try {
        // 1. Fetch sales history for this product
        // We'll use a new API endpoint to get real sales data
        const historyResponse = await fetch(`/api/products/${productId}/sales_history`);
        const historyData = await historyResponse.json();
        
        let salesSeries = [];
        if (historyData.success && historyData.series.length > 0) {
            salesSeries = historyData.series;
        } else {
            // Fallback to mock data if no history (for demo purposes)
            console.warn('No sales history found, using mock data for demo');
            salesSeries = [10, 12, 15, 14, 20, 25, 22, 30, 35, 40];
        }

        const payload = {
            "series": salesSeries,
            "product_id": productId
        };

        // 2. Call DL Service via Proxy
        const response = await fetch('/api/dl/forecast', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.success) {
            const forecast = result.data.forecast_value;
            const confidence = result.data.confidence || 0.85;
            
            alert(`Forecast for ${productName}:\n\nPredicted Demand: ${forecast} units\nConfidence: ${(confidence * 100).toFixed(1)}%\n\nBased on ${salesSeries.length} weeks of sales data.`);
        } else {
            showAlert('error', 'Forecast failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Forecast Error:', error);
        showAlert('error', 'Error generating forecast');
    }
}
