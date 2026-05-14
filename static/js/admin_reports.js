let scheduledReports = [];

async function loadStats() {
    try {
        const response = await fetch('/api/reports/stats');
        const data = await response.json();
        if (data.success) {
            setReportMetric('monthRevenue', Number(data.revenue).toLocaleString('en-US') + ' VND');
            setReportMetric('monthExpense', Number(data.expense).toLocaleString('en-US') + ' VND');
            setReportMetric('monthProfit', Number(data.profit).toLocaleString('en-US') + ' VND');
            setReportMetric('reportsSent', data.reports_sent);
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadScheduledReports() {
    try {
        const response = await fetch('/api/reports/scheduled');
        const data = await response.json();
        if (data.success) {
            scheduledReports = data.reports;
            renderReportsTable();
        }
    } catch (error) {
        console.error('Error loading reports:', error);
    }
}

function renderReportsTable() {
    const tbody = document.getElementById('scheduledReportsBody');
    if (scheduledReports.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">
                    No scheduled reports yet. Click "Schedule report" to get started.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = scheduledReports.map(report => `
        <tr>
            <td><strong>${report.name}</strong></td>
            <td>${formatReportType(report.report_type)}</td>
            <td><span class="badge bg-info">${report.frequency}</span></td>
            <td>${report.channel}</td>
            <td><span class="badge bg-${report.status === 'active' ? 'success' : 'secondary'}">${report.status}</span></td>
            <td>${report.last_sent_at ? new Date(report.last_sent_at).toLocaleString() : 'Never'}</td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteReport(${report.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function formatReportType(type) {
    const types = {
        'revenue_expense': 'Revenue & Expense',
        'inventory': 'Inventory Status',
        'customer_activity': 'Customer Activity'
    };
    return types[type] || type;
}

function setReportMetric(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

window.openScheduleReportModal = function openScheduleReportModal() {
    const modalElement = document.getElementById('scheduleReportModal');
    if (!modalElement) {
        return;
    }
    const modalInstance = bootstrap.Modal.getOrCreateInstance(modalElement);
    modalInstance.show();
};

async function submitScheduleReport() {
    const form = document.getElementById('scheduleReportForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/api/reports/scheduled', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        if (result.success) {
            bootstrap.Modal.getInstance(document.getElementById('scheduleReportModal')).hide();
            form.reset();
            loadScheduledReports();
            loadStats(); // Update stats if needed
            alert('Report scheduled successfully');
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function deleteReport(id) {
    if (!confirm('Are you sure you want to delete this scheduled report?')) return;

    try {
        const response = await fetch(`/api/reports/scheduled/${id}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            }
        });

        const result = await response.json();
        if (result.success) {
            loadScheduledReports();
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadScheduledReports();
});
