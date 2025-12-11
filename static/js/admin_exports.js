let exportsData = [];

async function loadExports() {
    try {
        const response = await fetch('/api/exports');
        const data = await response.json();

        if (data.success) {
            exportsData = data.exports;
            renderExportsTable();
            updateStats();
        } else {
            showAlert('error', 'Lỗi tải dữ liệu');
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
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
            <td>${exp.customer_name || 'Khách lẻ'}</td>
            <td class="text-end"><strong>${Number(exp.total_amount).toLocaleString('en-US')} VND</strong></td>
            <td><span class="badge bg-${exp.status === 'completed' ? 'success' : 'warning'}">${exp.status === 'completed' ? 'Hoàn thành' : 'Đang xử lý'}</span></td>
            <td>${new Date(exp.created_at).toLocaleDateString('en-US')}</td>
            <td>${exp.notes || '-'}</td>
            <td>
                <button class="btn btn-sm btn-info" onclick="alert('Xem chi tiết: ' + '${exp.code}')">
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

document.addEventListener('DOMContentLoaded', loadExports);
