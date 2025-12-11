let importsData = [];

async function loadImports() {
    try {
        const response = await fetch('/api/imports');
        const data = await response.json();

        if (data.success) {
            importsData = data.imports;
            renderImportsTable();
            updateStats();
        } else {
            showAlert('error', 'Lỗi tải dữ liệu');
        }
    } catch (error) {
        showAlert('error', 'Lỗi: ' + error.message);
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
            <td><span class="badge bg-${imp.status === 'completed' ? 'success' : 'warning'}">${imp.status === 'completed' ? 'Hoàn thành' : 'Đang xử lý'}</span></td>
            <td>${new Date(imp.created_at).toLocaleDateString('en-US')}</td>
            <td>${imp.notes || '-'}</td>
            <td>
                <button class="btn btn-sm btn-info" onclick="alert('Xem chi tiết: ' + '${imp.code}')">
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

document.addEventListener('DOMContentLoaded', loadImports);
