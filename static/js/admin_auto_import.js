let currentEditId = null;

async function loadAutomations() {
    try {
        const response = await fetch('/api/automations');
        const data = await response.json();
        if (data.success) {
            automations = data.automations;
            renderAutomationsTable();
            updateStats();
        }
    } catch (error) {
        console.error('Error loading automations:', error);
    }
}

function renderAutomationsTable() {
    const tbody = document.getElementById('automationsTableBody');
    if (automations.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="6">
                <div class="empty-state empty-state--compact">
                    <div class="empty-state__icon"><i class="fa-solid fa-robot"></i></div>
                    <p class="empty-state__title">Chưa có quy tắc tự động</p>
                    <p class="empty-state__description">Nhấn "Tạo quy tắc" ở góc trên hoặc chọn một mẫu bên dưới.</p>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = automations.map(auto => {
        const isActive = auto.status === 'active';
        const actions = [
            { label: 'Sửa', icon: 'fa-solid fa-pen', action: 'editAutomation' },
            { divider: true },
            { label: isActive ? 'Tạm dừng' : 'Kích hoạt', icon: isActive ? 'fa-solid fa-pause' : 'fa-solid fa-play', action: 'toggleStatusFromRow' },
            { divider: true },
            { label: 'Xóa', icon: 'fa-solid fa-trash', action: 'deleteAutomation', danger: true },
        ];
        return `
        <tr>
            <td><strong>${banleUI.escapeHtml(auto.name)}</strong></td>
            <td>${formatType(auto.type)}</td>
            <td>
                <div class="form-check form-switch" title="${auto.status === 'active' ? 'Đang bật' : 'Đang tắt'}">
                    <input class="form-check-input" type="checkbox" aria-label="Bật/tắt quy tự động"
                        ${isActive ? 'checked' : ''}
                        onchange="toggleStatus(${auto.id}, this.checked)">
                </div>
            </td>
            <td>${auto.last_run ? banleUI.formatDateTimeVN(auto.last_run) : '—'}</td>
            <td>${formatConfig(auto.type, auto.config)}</td>
            <td class="table__actions">${banleUI.renderRowActions(auto.id, actions)}</td>
        </tr>
    `;
    }).join('');

    banleUI.bindRowActions(tbody);
}

function toggleStatusFromRow(id) {
    const auto = automations.find((a) => String(a.id) === String(id));
    if (!auto) return;
    const newStatus = auto.status === 'active' ? false : true;
    toggleStatus(id, newStatus);
}

function updateStats() {
    const activeCount = automations.filter(a => a.status === 'active').length;
    document.getElementById('activeAutomations').textContent = activeCount;

    const lastRun = automations
        .filter(a => a.last_run)
        .sort((a, b) => new Date(b.last_run) - new Date(a.last_run))[0];

    document.getElementById('lastRun').textContent = lastRun ? banleUI.formatDateTimeVN(lastRun.last_run) : '—';
}

function formatType(type) {
    const tones = {
        'low_stock': 'orange',
        'scheduled': 'blue',
        'smart_forecast': 'purple',
        'report': 'green',
        'integration': 'red',
    };
    const labels = {
        'low_stock': 'Tồn kho thấp',
        'scheduled': 'Theo lịch',
        'smart_forecast': 'Dự báo AI',
        'report': 'Báo cáo',
        'integration': 'Tích hợp',
    };
    const label = labels[type] || type;
    const tone = tones[type] || 'gray';
    return banleUI.statusPill(label, tone);
}

function formatConfig(type, config) {
    let c = config;
    if (typeof c === 'string') {
        try { c = JSON.parse(c); } catch (e) { return banleUI.escapeHtml(String(config)); }
    }
    if (!c || typeof c !== 'object') return banleUI.escapeHtml(String(config || '—'));

    const entries = Object.entries(c);
    if (type === 'low_stock') {
        const thr = c.threshold !== undefined ? c.threshold : '—';
        const qty = c.reorder_quantity !== undefined ? c.reorder_quantity : '—';
        const scope = c.product_id && c.product_id !== 'all' ? ` (SP: ${c.product_id})` : ' (Tất cả SP)';
        return `<span class="table__json" title="threshold: ${thr}, reorder: ${qty}">Ngưỡng &lt; ${thr} • Đặt ${qty}${scope}</span>`;
    } else if (type === 'scheduled') {
        const parts = [];
        if (c.frequency) parts.push(c.frequency);
        if (c.time) parts.push(`lúc ${c.time}`);
        if (c.day) parts.push(`(${c.day})`);
        return `<span class="table__json" title="${banleUI.escapeHtml(JSON.stringify(c))}">${parts.join(' ') || banleUI.escapeHtml(JSON.stringify(c))}</span>`;
    } else if (type === 'smart_forecast') {
        return `<span class="table__json" title="${banleUI.escapeHtml(JSON.stringify(c))}">Nhìn trước: ${c.look_ahead_days || '—'} ngày${c.auto_approve ? ' • Tự duyệt' : ''}</span>`;
    }

    // Generic fallback: render as a compact key:value pill (never raw JSON)
    const summary = entries
        .slice(0, 3)
        .map(([k, v]) => {
            const vs = typeof v === 'object' ? JSON.stringify(v) : String(v);
            return `<span class="table__json-key">${banleUI.escapeHtml(k)}</span>: ${banleUI.escapeHtml(vs.length > 20 ? vs.slice(0, 20) + '…' : vs)}`;
        })
        .join(' • ');
    const more = entries.length > 3 ? ` <span class="text-muted">+${entries.length - 3}</span>` : '';
    return `<span class="table__json" title="${banleUI.escapeHtml(JSON.stringify(c))}">${summary}${more}</span>`;
}

window.useTemplate = function(type) {
    currentEditId = null;
    openModal('automationModal');
    
    // Reset form
    document.getElementById('automationForm').reset();
    
    // Set type
    const typeSelect = document.getElementById('automationTypeSelect');
    typeSelect.value = type;
    
    // Update UI
    updateConfigUI();
    
    // Set default name
    const nameInput = document.querySelector('input[name="name"]');
    if (type === 'low_stock') {
        nameInput.value = 'Tự động nhập khi tồn kho thấp';
    } else if (type === 'scheduled') {
        nameInput.value = 'Nhập hàng theo lịch hàng tuần';
    }
};

window.openAddAutomationModal = function() {
    currentEditId = null;
    document.getElementById('automationForm').reset();
    openModal('automationModal');
    updateConfigUI();
};

window.editAutomation = function(id) {
    currentEditId = id;
    const auto = automations.find(a => a.id === id);
    if (!auto) return;
    
    openModal('automationModal');
    
    // Fill form
    document.querySelector('input[name="name"]').value = auto.name;
    document.getElementById('automationTypeSelect').value = auto.type;
    document.getElementById('automationActive').checked = (auto.status === 'active');
    
    updateConfigUI();
    
    // Fill config
    const config = typeof auto.config === 'string' ? JSON.parse(auto.config) : auto.config;
    
    if (auto.type === 'low_stock') {
        document.getElementById('cfgProductScope').value = config.product_id || 'all';
        document.getElementById('cfgThreshold').value = config.threshold || 10;
        document.getElementById('cfgReorderQty').value = config.reorder_quantity || 50;
    } else if (auto.type === 'scheduled') {
        document.getElementById('cfgFrequency').value = config.frequency || 'weekly';
        document.getElementById('cfgDay').value = config.day || 'monday';
        document.getElementById('cfgTime').value = config.time || '09:00';
    } else if (auto.type === 'smart_forecast') {
        document.getElementById('cfgLookAhead').value = config.look_ahead_days || 30;
        document.getElementById('cfgAutoApprove').value = config.auto_approve ? 'true' : 'false';
    }
};

// New form-based UI switcher (replaces JSON template system)
window.updateConfigUI = function() {
    const type = document.getElementById('automationTypeSelect').value;
    
    // Hide all config sections
    document.querySelectorAll('.config-section').forEach(el => el.style.display = 'none');
    
    // Show relevant section
    if (type === 'low_stock') {
        document.getElementById('configLowStock').style.display = 'block';
    } else if (type === 'scheduled') {
        document.getElementById('configScheduled').style.display = 'block';
    } else if (type === 'smart_forecast') {
        document.getElementById('configForecast').style.display = 'block';
    }
};

// Build config JSON from form fields
function buildConfigFromForm() {
    const type = document.getElementById('automationTypeSelect').value;
    let config = {};
    
    if (type === 'low_stock') {
        config = {
            product_id: document.getElementById('cfgProductScope').value,
            threshold: parseInt(document.getElementById('cfgThreshold').value) || 10,
            reorder_quantity: parseInt(document.getElementById('cfgReorderQty').value) || 50
        };
    } else if (type === 'scheduled') {
        config = {
            frequency: document.getElementById('cfgFrequency').value,
            day: document.getElementById('cfgDay').value,
            time: document.getElementById('cfgTime').value
        };
    } else if (type === 'smart_forecast') {
        config = {
            model: "lstm",
            look_ahead_days: parseInt(document.getElementById('cfgLookAhead').value) || 30,
            auto_approve: document.getElementById('cfgAutoApprove').value === 'true'
        };
    }
    
    return JSON.stringify(config);
}

// Legacy support for old JSON-based modal (kept for backwards compatibility)
window.updateConfigPlaceholder = function() {
    // Redirect to new UI function if new form exists
    if (document.getElementById('configLowStock')) {
        updateConfigUI();
        return;
    }
    
    // Fallback for old JSON textarea approach
    const type = document.getElementById('automationTypeSelect').value;
    const configArea = document.getElementById('automationConfig');
    const helpText = document.getElementById('configHelp');
    
    if (!configArea) return;
    
    const templates = {
        'low_stock': '{\n  "product_id": "all",\n  "threshold": 10,\n  "reorder_quantity": 50\n}',
        'scheduled': '{\n  "frequency": "weekly",\n  "day": "monday",\n  "time": "09:00"\n}',
        'smart_forecast': '{\n  "model": "lstm",\n  "look_ahead_days": 30,\n  "auto_approve": false\n}'
    };
    
    configArea.placeholder = templates[type] || '{}';
    
    const helpTexts = {
        'low_stock': 'Kích hoạt khi tồn kho xuống dưới ngưỡng.',
        'scheduled': 'Chạy tạo phiếu nhập theo lịch cố định.',
        'smart_forecast': 'Dùng AI dự báo nhu cầu và tạo đơn hàng.'
    };
    helpText.textContent = helpTexts[type] || 'Tham số cấu hình ở định dạng JSON.';
};

window.submitAutomation = async function() {
    const form = document.getElementById('automationForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Use new form-based config builder if available
    if (document.getElementById('configLowStock')) {
        data.config = buildConfigFromForm();
    } else {
        // Legacy: Validate JSON from textarea
        try {
            JSON.parse(data.config);
        } catch (e) {
            banleUI.showAlert('error', 'Cấu hình JSON không hợp lệ');
            return;
        }
    }

    try {
        let url = '/api/automations';
        let method = 'POST';
        
        if (currentEditId) {
            url = `/api/automations/${currentEditId}`;
            method = 'PUT';
        }

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        if (result.success) {
            closeModal('automationModal');
            form.reset();
            currentEditId = null;
            loadAutomations();
            banleUI.showAlert('success', currentEditId ? 'Cập nhật quy tự động thành công' : 'Tạo quy tự động thành công');
        } else {
            banleUI.showAlert('error', result.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
};

window.toggleStatus = async function(id, isActive) {
    try {
        const response = await fetch(`/api/automations/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ status: isActive ? 'active' : 'inactive' })
        });

        const result = await response.json();
        if (result.success) {
            // No label to update — status is shown via the toggle switch only
            updateStats();
        } else {
            banleUI.showAlert('error', 'Không cập nhật được trạng thái: ' + result.message);
            loadAutomations();
        }
    } catch (error) {
        console.error('Error toggling status:', error);
        loadAutomations();
    }
};

window.deleteAutomation = async function(id) {
    if (!confirm('Bạn có chắc muốn xóa quy tắc này?')) return;

    try {
        const response = await fetch(`/api/automations/${id}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            }
        });

        const result = await response.json();
        if (result.success) {
            banleUI.showAlert('success', 'Đã xóa quy tắc');
            loadAutomations();
        } else {
            banleUI.showAlert('error', result.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    loadAutomations();
});
