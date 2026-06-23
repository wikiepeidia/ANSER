document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
});

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/dashboard/stats');
        if (!response.ok) return;

        const data = await response.json();
        if (data.success) {
            // Cập nhật Doanh thu
            const revenueEl = document.querySelector('.glance-card:nth-child(1) h3');
            if (revenueEl) revenueEl.textContent = formatCurrency(data.revenue);

            // Cập nhật Đơn hàng mới
            const ordersEl = document.querySelector('.glance-card:nth-child(2) h3');
            if (ordersEl) ordersEl.textContent = data.new_orders;

            // Cập nhật Yêu cầu trả hàng
            const returnsEl = document.querySelector('.glance-card:nth-child(3) h3');
            if (returnsEl) returnsEl.textContent = data.pending_returns;

            // Cập nhật Credits
            const creditsEl = document.querySelector('.wallet-glance:nth-child(3) .glance-card:nth-child(1) h3');
            if (creditsEl) creditsEl.textContent = data.credits;

            // Cập nhật Dự án
            const projectsEl = document.querySelector('.wallet-glance:nth-child(3) .glance-card:nth-child(2) h3');
            if (projectsEl) projectsEl.textContent = `${data.active_projects} / 5`;

            // Cập nhật Trạng thái
            const statusEl = document.querySelector('.wallet-glance:nth-child(3) .glance-card:nth-child(3) h3');
            if (statusEl) statusEl.textContent = data.subscription_status;
        }
    } catch (error) {
        console.error('Không tải được thống kê dashboard', error);
    }
}

function formatCurrency(value) {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
}
