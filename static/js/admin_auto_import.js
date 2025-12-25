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
            <tr>
                <td colspan="6" class="text-center">
                    No automations yet. Click "Create automation" to get started.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = automations.map(auto => `
        <tr>
            <td><strong>${auto.name}</strong></td>
            <td>${formatType(auto.type)}</td>
            <td>
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" 
                        ${auto.status === 'active' ? 'checked' : ''} 
                        onchange="toggleStatus(${auto.id}, this.checked)">
                    <label class="form-check-label" id="status-label-${auto.id}">${auto.status}</label>
                </div>
            </td>
            <td>${auto.last_run ? new Date(auto.last_run).toLocaleString() : 'Never'}</td>
            <td><small class="text-muted font-monospace">${formatConfig(auto.type, auto.config)}</small></td>
            <td>
                <button class="btn btn-sm btn-primary me-1" onclick="editAutomation(${auto.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteAutomation(${auto.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function updateStats() {
    const activeCount = automations.filter(a => a.status === 'active').length;
    document.getElementById('activeAutomations').textContent = activeCount;
    
    // Mock completed runs for now, or calculate if we had run history
    // document.getElementById('completedRuns').textContent = '0'; 
    
    const lastRun = automations
        .filter(a => a.last_run)
        .sort((a, b) => new Date(b.last_run) - new Date(a.last_run))[0];
        
    document.getElementById('lastRun').textContent = lastRun ? new Date(lastRun.last_run).toLocaleString() : 'None';
}

function formatType(type) {
    const types = {
        'low_stock': '<span class="badge bg-warning text-dark">Low Stock</span>',
        'scheduled': '<span class="badge bg-info">Scheduled</span>',
        'smart_forecast': '<span class="badge bg-primary">AI Forecast</span>'
    };
    return types[type] || type;
}

function formatConfig(type, config) {
    try {
        const c = typeof config === 'string' ? JSON.parse(config) : config;
        if (type === 'low_stock') {
            return `Threshold: < ${c.threshold}, Order: ${c.reorder_quantity}`;
        } else if (type === 'scheduled') {
            return `${c.frequency} at ${c.time} (${c.day || 'All'})`;
        } else if (type === 'smart_forecast') {
            return `Look ahead: ${c.look_ahead_days} days`;
        }
        return JSON.stringify(c).substring(0, 30) + '...';
    } catch (e) {
        return String(config);
    }
}

window.useTemplate = function(type) {
    currentEditId = null;
    const modal = new bootstrap.Modal(document.getElementById('automationModal'));
    
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
        nameInput.value = 'Auto Import on Low Stock';
    } else if (type === 'scheduled') {
        nameInput.value = 'Weekly Scheduled Import';
    }
    
    modal.show();
};

window.openAddAutomationModal = function() {
    currentEditId = null;
    document.getElementById('automationForm').reset();
    const modal = new bootstrap.Modal(document.getElementById('automationModal'));
    updateConfigUI();
    modal.show();
};

window.editAutomation = function(id) {
    currentEditId = id;
    const auto = automations.find(a => a.id === id);
    if (!auto) return;
    
    const modal = new bootstrap.Modal(document.getElementById('automationModal'));
    
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
    
    modal.show();
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
        'low_stock': 'Trigger when stock falls below threshold.',
        'scheduled': 'Run import generation on a fixed schedule.',
        'smart_forecast': 'Use AI to predict demand and generate orders.'
    };
    helpText.textContent = helpTexts[type] || 'Configuration parameters in JSON format.';
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
            alert('Invalid JSON configuration');
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
            bootstrap.Modal.getInstance(document.getElementById('automationModal')).hide();
            form.reset();
            currentEditId = null;
            loadAutomations();
            alert(currentEditId ? 'Automation updated successfully' : 'Automation created successfully');
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
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
            // Update label
            const label = document.getElementById(`status-label-${id}`);
            if (label) label.textContent = isActive ? 'active' : 'inactive';
            updateStats();
        } else {
            alert('Failed to update status: ' + result.message);
            // Revert checkbox
            loadAutomations();
        }
    } catch (error) {
        console.error('Error toggling status:', error);
        loadAutomations();
    }
};

window.deleteAutomation = async function(id) {
    if (!confirm('Are you sure you want to delete this automation?')) return;

    try {
        const response = await fetch(`/api/automations/${id}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            }
        });

        const result = await response.json();
        if (result.success) {
            loadAutomations();
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    loadAutomations();
});
