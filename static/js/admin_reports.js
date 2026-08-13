let scheduledReports = [];

async function loadStats() {
    try {
        const response = await fetch('/api/reports/stats');
        const data = await response.json();
        if (data.success) {
            setReportMetric('monthRevenue', banleUI.formatVND(data.revenue));
            setReportMetric('monthExpense', banleUI.formatVND(data.expense));
            setReportMetric('monthProfit', banleUI.formatVND(data.profit));
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
            scheduledReports = data.reports || [];
            renderReportsTable();
        }
    } catch (error) {
        console.error('Error loading reports:', error);
    }
}

function frequencyTone(freq) {
    if (freq === 'daily') return 'blue';
    if (freq === 'weekly') return 'orange';
    if (freq === 'monthly') return 'purple';
    return 'gray';
}

function frequencyLabel(freq) {
    const map = { daily: 'Hằng ngày', weekly: 'Hằng tuần', monthly: 'Hằng tháng' };
    return map[freq] || freq;
}

function channelLabel(ch) {
    const map = { email: 'Email', slack: 'Slack', download: 'Tệp' };
    return map[ch] || ch;
}

function renderReportsTable() {
    const tbody = document.getElementById('scheduledReportsBody');
    if (scheduledReports.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="7">
                <div class="empty-state empty-state--compact">
                    <div class="empty-state__icon"><i class="fa-solid fa-calendar-check"></i></div>
                    <p class="empty-state__title">Chưa có báo cáo đã lên lịch</p>
                    <p class="empty-state__description">Nhấn "Lên lịch báo cáo" ở góc trên hoặc chọn một mẫu bên dưới để bắt đầu.</p>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = scheduledReports.map(report => {
        const isActive = report.status === 'active';
        const lastSent = banleUI.formatDateTimeVN(report.last_sent_at);
        const actions = [
            { label: 'Sửa', icon: 'fa-solid fa-pen', action: 'editReport' },
            { divider: true },
            { label: isActive ? 'Tạm dừng' : 'Kích hoạt', icon: isActive ? 'fa-solid fa-pause' : 'fa-solid fa-play', action: 'toggleReport' },
            { divider: true },
            { label: 'Xóa', icon: 'fa-solid fa-trash', action: 'deleteReport', danger: true },
        ];
        return `
        <tr>
            <td><strong>${banleUI.escapeHtml(report.name)}</strong></td>
            <td>${banleUI.escapeHtml(formatReportType(report.report_type))}</td>
            <td>${banleUI.statusPill(frequencyLabel(report.frequency), frequencyTone(report.frequency))}</td>
            <td>${banleUI.escapeHtml(channelLabel(report.channel))}</td>
            <td>${banleUI.statusPill(isActive ? 'Đang chạy' : 'Tạm dừng', isActive ? 'green' : 'gray')}</td>
            <td>${lastSent}</td>
            <td class="table__actions">${banleUI.renderRowActions(report.id, actions)}</td>
        </tr>
    `;
    }).join('');

    banleUI.bindRowActions(tbody);
}

function formatReportType(type) {
    const types = {
        'revenue_expense': 'Doanh thu & Chi phí',
        'inventory': 'Tình trạng tồn kho',
        'customer_activity': 'Hoạt động khách hàng',
        // English values returned by the API
        'alerts': 'Cảnh báo',
        'revenue': 'Doanh thu',
        'sales_summary': 'Tổng hợp bán hàng',
        'low_stock': 'Tồn kho thấp',
        'scheduled': 'Theo lịch',
        'integration': 'Tích hợp',
        'report': 'Báo cáo',
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
    openModal(modalElement.id);
};

// Fill the schedule form from a template and open the modal
window.useReportTemplate = function useReportTemplate(frequency, name) {
    const form = document.getElementById('scheduleReportForm');
    if (!form) return;

    form.reset();
    const nameInput = form.querySelector('[name="name"]');
    const frequencySelect = form.querySelector('[name="frequency"]');
    const reportTypeSelect = form.querySelector('[name="report_type"]');
    const channelSelect = form.querySelector('[name="channel"]');

    if (nameInput) nameInput.value = name;
    if (frequencySelect) frequencySelect.value = frequency;
    if (reportTypeSelect) reportTypeSelect.value = 'revenue_expense';
    if (channelSelect) channelSelect.value = 'email';

    openModal('scheduleReportModal');
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
            closeModal('scheduleReportModal');
            form.reset();
            loadScheduledReports();
            loadStats();
            banleUI.showAlert('success', 'Đã lên lịch báo cáo thành công');
        } else {
            banleUI.showAlert('error', result.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

async function deleteReport(id) {
    if (!confirm('Bạn có chắc chắn muốn xóa báo cáo đã lên lịch này?')) return;

    try {
        const response = await fetch(`/api/reports/scheduled/${id}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            }
        });

        const result = await response.json();
        if (result.success) {
            banleUI.showAlert('success', 'Đã xóa báo cáo');
            loadScheduledReports();
        } else {
            banleUI.showAlert('error', result.message);
        }
    } catch (error) {
        banleUI.showAlert('error', 'Lỗi: ' + error.message);
    }
}

function editReport(id) {
    const report = scheduledReports.find((r) => String(r.id) === String(id));
    if (!report) return;
    const form = document.getElementById('scheduleReportForm');
    if (!form) return;
    form.reset();
    form.querySelector('[name="name"]').value = report.name || '';
    form.querySelector('[name="frequency"]').value = report.frequency || 'monthly';
    form.querySelector('[name="report_type"]').value = report.report_type || 'revenue_expense';
    form.querySelector('[name="channel"]').value = report.channel || 'email';
    form.querySelector('[name="recipients"]').value = (report.recipients || []).join(', ');
    openModal('scheduleReportModal');
}

function toggleReport(id) {
    const report = scheduledReports.find((r) => String(r.id) === String(id));
    if (!report) return;
    const newStatus = report.status === 'active' ? 'paused' : 'active';
    banleUI.showAlert('info', `Tính năng chuyển trạng thái sang "${newStatus}" sẽ được thêm sau. Hiện tại vẫn dùng bảng modal.`);
}

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadScheduledReports();
    // Chart.js is loaded with `defer`, wait a tick then render chart
    if (typeof Chart !== 'undefined') {
        renderRevenueChart();
    } else {
        const waitChart = setInterval(() => {
            if (typeof Chart !== 'undefined') {
                clearInterval(waitChart);
                renderRevenueChart();
            }
        }, 100);
        setTimeout(() => clearInterval(waitChart), 5000); // give up after 5s
    }
});

let revenueChartInstance = null;

async function renderRevenueChart() {
    const canvas = document.getElementById('revenueChart');
    if (!canvas || typeof Chart === 'undefined') return;

    try {
        let labels = [];
        let revenue = [];
        let expense = [];

        const response = await fetch('/api/reports/stats', { credentials: 'same-origin' });
        if (response.ok) {
            const data = await response.json();
            if (Array.isArray(data.daily_revenue) && data.daily_revenue.length > 0) {
                labels = data.daily_revenue.map(d => d.date);
                revenue = data.daily_revenue.map(d => Number(d.value) || 0);
            }
            if (Array.isArray(data.daily_expense) && data.daily_expense.length > 0) {
                expense = data.daily_expense.map(d => Number(d.value) || 0);
            }
        }

        // Fallback: 7 dummy days so the chart always renders
        if (labels.length === 0) {
            labels = Array.from({ length: 7 }, (_, i) => {
                const d = new Date();
                d.setDate(d.getDate() - (6 - i));
                return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
            });
            revenue = [0, 0, 0, 0, 0, 0, 0];
            expense = [0, 0, 0, 0, 0, 0, 0];
        }

        // Ensure expense has same length as labels
        while (expense.length < labels.length) expense.push(0);
        while (revenue.length < labels.length) revenue.push(0);

        if (revenueChartInstance) revenueChartInstance.destroy();

        const styles = getComputedStyle(document.documentElement);
        const success = styles.getPropertyValue('--status-success').trim() || '#16a34a';
        const danger = styles.getPropertyValue('--status-error').trim() || '#dc2626';
        const gridColor = styles.getPropertyValue('--border-soft').trim() || 'rgba(0,0,0,0.08)';
        const textColor = styles.getPropertyValue('--text-muted').trim() || '#64748b';

        revenueChartInstance = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Doanh thu',
                        data: revenue,
                        backgroundColor: success + 'cc',
                        borderColor: success,
                        borderWidth: 1,
                        borderRadius: 6
                    },
                    {
                        label: 'Chi phí',
                        data: expense,
                        backgroundColor: danger + 'cc',
                        borderColor: danger,
                        borderWidth: 1,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { color: textColor, font: { size: 12 } } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${banleUI.formatVND(ctx.parsed.y)}`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        suggestedMax: 1000000,
                        ticks: {
                            color: textColor,
                          callback: (v) => banleUI.formatNumberCompact(v)
                        },
                        grid: { color: gridColor }
                    },
                    x: {
                        ticks: { color: textColor },
                        grid: { display: false }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Cannot render revenue chart:', error);
    }
}

// Re-render chart when tab becomes visible (avoid zero-height canvas)
window.addEventListener('resize', () => {
    if (revenueChartInstance) revenueChartInstance.resize();
});
