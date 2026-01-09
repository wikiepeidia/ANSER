let importsData = [];
let products = [];

async function loadImports() {
    try {
        const response = await fetch('/api/imports');
        const data = await response.json();

        if (data.success) {
            importsData = data.imports;
            renderImportsTable();
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

function renderImportsTable() {
    const tbody = document.getElementById('importsTableBody');

    if (importsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No import orders found</td></tr>';
        return;
    }

    tbody.innerHTML = importsData.map(imp => `
        <tr>
            <td><strong>${imp.code}</strong></td>
            <td>${imp.supplier_name || '-'}</td>
            <td class="text-end"><strong>${Number(imp.total_amount).toLocaleString('en-US')} VND</strong></td>
            <td><span class="badge bg-${imp.status === 'completed' ? 'success' : 'warning'}">${imp.status === 'completed' ? 'Completed' : 'Processing'}</span></td>
            <td>${new Date(imp.created_at).toLocaleDateString('en-US')}</td>
            <td>${imp.notes || '-'}</td>
            <td>
                <button class="btn btn-sm btn-info" onclick="viewImport(${imp.id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function updateStats() {
    document.getElementById('totalImports').textContent = importsData.length;
    const completed = importsData.filter(i => i.status === 'completed').length;
    document.getElementById('completedImports').textContent = completed;

    const total = importsData.reduce((sum, i) => sum + Number(i.total_amount), 0);
    document.getElementById('totalAmount').textContent = total.toLocaleString('en-US') + ' VND';
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

// Create Import Logic
function addImportItemRow() {
    const tbody = document.getElementById('importItemsBody');
    const row = document.createElement('tr');
    
    const productOptions = products.map(p => `<option value="${p.id}" data-price="${p.price}">${p.code} - ${p.name}</option>`).join('');
    
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
    // Optional: Auto-fill price if needed, but for imports usually user enters cost price
    // const price = select.options[select.selectedIndex].dataset.price;
    // const row = select.closest('tr');
    // row.querySelector('[name="unit_price"]').value = price;
}

async function submitImport() {
    const form = document.getElementById('createImportForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const supplier_name = form.querySelector('[name="supplier_name"]').value;
    const notes = form.querySelector('[name="notes"]').value;
    
    const items = [];
    form.querySelectorAll('#importItemsBody tr').forEach(row => {
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
        const response = await fetch('/api/imports', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ supplier_name, notes, items })
        });
        
        const data = await response.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('createImportModal')).hide();
            form.reset();
            document.getElementById('importItemsBody').innerHTML = '';
            loadImports();
            showAlert('success', 'Import created successfully');
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function viewImport(id) {
    try {
        const response = await fetch(`/api/imports/${id}`);
        const data = await response.json();
        
        if (data.success) {
            const t = data.transaction;
            document.getElementById('viewImportCode').textContent = t.code;
            document.getElementById('viewImportSupplier').textContent = t.supplier_name;
            document.getElementById('viewImportDate').textContent = new Date(t.created_at).toLocaleString();
            document.getElementById('viewImportStatus').textContent = t.status;
            document.getElementById('viewImportTotal').textContent = Number(t.total_amount).toLocaleString('en-US') + ' VND';
            document.getElementById('viewImportNotes').textContent = t.notes || '-';
            
            const tbody = document.getElementById('viewImportItemsBody');
            tbody.innerHTML = data.details.map(d => `
                <tr>
                    <td>${d.product_code}</td>
                    <td>${d.product_name}</td>
                    <td class="text-end">${d.quantity}</td>
                    <td class="text-end">${Number(d.unit_price).toLocaleString('en-US')}</td>
                    <td class="text-end">${Number(d.total_price).toLocaleString('en-US')}</td>
                </tr>
            `).join('');
            
            new bootstrap.Modal(document.getElementById('viewImportModal')).show();
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadImports();
    loadProducts();
});

// OCR Import Logic
document.addEventListener('DOMContentLoaded', function() {
    const ocrFile = document.getElementById('ocrFile');
    const ocrLoading = document.getElementById('ocrLoading');
    const ocrResult = document.getElementById('ocrResult');
    const ocrItemsBody = document.getElementById('ocrItemsBody');
    const btnSaveOcrImport = document.getElementById('btnSaveOcrImport');
    const ocrProgressBar = document.getElementById('ocrProgressBar');
    const ocrStatusText = document.getElementById('ocrStatusText');
    
    let extractedData = null;

    if (ocrFile) {
        ocrFile.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;

            // Reset UI
            ocrLoading.style.display = 'block';
            ocrResult.style.display = 'none';
            btnSaveOcrImport.disabled = true;
            ocrItemsBody.innerHTML = '';

            // Progress Bar Init
            let progress = 0;
            if (ocrProgressBar) {
                ocrProgressBar.style.width = '0%';
                ocrProgressBar.textContent = '0%';
                ocrProgressBar.classList.remove('bg-success', 'bg-danger');
                ocrProgressBar.classList.add('progress-bar-striped', 'progress-bar-animated');
            }
            if (ocrStatusText) ocrStatusText.textContent = 'Starting upload...';

            // Simulation
            const steps = [
                { pct: 15, msg: 'Uploading invoice image...' },
                { pct: 35, msg: 'Analyzing document layout...' },
                { pct: 55, msg: 'Detecting tables and regions...' },
                { pct: 75, msg: 'Running OCR text extraction...' },
                { pct: 90, msg: 'Parsing product data...' }
            ];
            
            let stepIndex = 0;
            const progressInterval = setInterval(() => {
                if (stepIndex < steps.length) {
                    if (progress < steps[stepIndex].pct) {
                        progress += Math.random() * 2;
                    } else {
                        stepIndex++;
                    }
                } else {
                    if (progress < 95) progress += 0.2;
                }
                
                if (ocrProgressBar) {
                    const currentPct = Math.min(Math.round(progress), 99);
                    ocrProgressBar.style.width = `${currentPct}%`;
                    ocrProgressBar.textContent = `${currentPct}%`;
                }
                if (ocrStatusText && stepIndex < steps.length) {
                    ocrStatusText.textContent = steps[stepIndex].msg;
                }
            }, 100);

            const formData = new FormData();
            formData.append('file', file);

            try {
                // Call our backend proxy which calls the DL service
                const response = await fetch('/api/dl/detect', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                    }
                });

                const result = await response.json();

                if (result.success) {
                    if (ocrProgressBar) {
                        ocrProgressBar.style.width = '100%';
                        ocrProgressBar.textContent = '100%';
                        ocrProgressBar.classList.remove('progress-bar-animated');
                        ocrProgressBar.classList.add('bg-success');
                    }
                    if (ocrStatusText) ocrStatusText.textContent = 'Analysis Complete!';
                    
                    // Small delay to show 100%
                    await new Promise(r => setTimeout(r, 500));

                    extractedData = result.data;
                    renderOcrPreview(extractedData);
                    ocrResult.style.display = 'block';
                    btnSaveOcrImport.disabled = false;
                    ocrLoading.style.display = 'none';
                } else {
                    alert('OCR Failed: ' + (result.error || 'Unknown error'));
                    ocrLoading.style.display = 'none';
                }
            } catch (error) {
                console.error('OCR Error:', error);
                alert('Error processing invoice: ' + error.message);
                ocrLoading.style.display = 'none';
            } finally {
                clearInterval(progressInterval);
                // Reset file input to allow re-uploading the same file if needed
                ocrFile.value = ''; 
            }
        });
    }

    function _extractOcrItems(data) {
        // Support multiple shapes returned by DL service
        // Possible shapes:
        // - data.products (array)
        // - data.items (array)
        // - data.invoice.items
        // - data.data.products (when wrapped)
        const items = data?.products || data?.items || data?.invoice?.items || data?.invoice?.products || data?.data?.products || [];
        // Normalize fields to product_name, quantity, unit_price, total
        return items.map(item => ({
            product_name: item.product_name || item.name || item.product || item.product_name || '',
            quantity: item.quantity || item.qty || item.count || 1,
            unit_price: item.unit_price || item.unit || item.price || 0,
            total: item.line_total || item.total || item.lineTotal || (item.unit_price && item.quantity ? item.unit_price * item.quantity : 0)
        }));
    }

    function renderOcrPreview(data) {
        const items = _extractOcrItems(data);
        
        if (items.length === 0) {
            ocrItemsBody.innerHTML = '<tr><td colspan="5" class="text-center">No items detected</td></tr>';
            return;
        }

        // Make products dropdown for matching
        const productOptions = products.map(p => 
            `<option value="${p.id}" data-name="${p.name}">${p.code} - ${p.name}</option>`
        ).join('');

        ocrItemsBody.innerHTML = items.map((item, idx) => `
            <tr data-index="${idx}">
                <td>
                    <select class="form-select form-select-sm ocr-product-select" data-detected="${item.name || ''}">
                        <option value="">-- Select or keep detected --</option>
                        <option value="new" selected>${item.name || 'Unknown'} (new)</option>
                        ${productOptions}
                    </select>
                </td>
                <td>
                    <input type="number" class="form-control form-control-sm" value="${item.quantity || 1}" min="1">
                </td>
                <td>
                    <input type="number" class="form-control form-control-sm" value="${item.unit_price || 0}" min="0">
                </td>
                <td>
                    <span class="item-total">${item.total || 0}</span>
                </td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('tr').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    if (btnSaveOcrImport) {
        btnSaveOcrImport.addEventListener('click', async function() {
            if (!extractedData) return;
            
            const rows = document.querySelectorAll('#ocrItemsBody tr');
            const items = [];
            
            rows.forEach(row => {
                const select = row.querySelector('.ocr-product-select');
                const qtyInput = row.querySelectorAll('input')[0];
                const priceInput = row.querySelectorAll('input')[1];
                
                // If value is "new" or empty, we send null ID and the detected name
                // If value is a number (ID), we send that ID
                const isNew = select.value === 'new' || select.value === '';
                const productId = isNew ? null : select.value;
                const productName = select.dataset.detected || 'Unknown Product';
                
                items.push({
                    product_id: productId,
                    product_name: productName,
                    quantity: parseFloat(qtyInput.value) || 0,
                    unit_price: parseFloat(priceInput.value) || 0
                });
            });

            if (items.length === 0) {
                alert('No items to import');
                return;
            }

            const payload = {
                supplier_name: extractedData.invoice?.vendor_name || extractedData.vendor_name || 'OCR Import',
                notes: 'Imported via OCR Smart Import',
                items: items
            };

            try {
                // Show loading state
                const originalText = btnSaveOcrImport.innerHTML;
                btnSaveOcrImport.disabled = true;
                btnSaveOcrImport.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';

                const response = await fetch('/api/imports', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                    },
                    body: JSON.stringify(payload)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('ocrImportModal'));
                    modal.hide();
                    loadImports(); // Reload table
                    showAlert('success', 'Import created successfully!');
                    
                    // Reset OCR form
                    if (ocrItemsBody) ocrItemsBody.innerHTML = '';
                    if (ocrResult) ocrResult.style.display = 'none';
                    if (ocrFile) ocrFile.value = '';
                    extractedData = null;
                } else {
                    alert('Failed to create import: ' + data.message);
                }
            } catch (error) {
                console.error('Import Error:', error);
                alert('Error creating import: ' + error.message);
            } finally {
                btnSaveOcrImport.disabled = false;
                btnSaveOcrImport.innerHTML = originalText;
            }
        });
    }
});

