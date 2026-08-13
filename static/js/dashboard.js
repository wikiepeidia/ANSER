document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    setTimeout(() => {
        renderRevenueChart();
        loadTopProducts();
    }, 200);
});

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/dashboard/stats', { credentials: 'same-origin' });
        if (!response.ok) return;
        const data = await response.json();
        if (data.success) {
            const todayRevenueEl = document.querySelector('[data-stat="today_revenue"]');
            if (todayRevenueEl) todayRevenueEl.textContent = formatCurrency(data.today_revenue || 0);
            const todayCountEl = document.querySelector('[data-stat="today_sales_count"]');
            if (todayCountEl) todayCountEl.textContent = `${data.today_sales_count || 0} đơn hôm nay`;
            const revenueEl = document.querySelector('[data-stat="revenue"]');
            if (revenueEl) revenueEl.textContent = formatCurrency(data.revenue || 0);
            const ordersEl = document.querySelector('[data-stat="new_orders"]');
            if (ordersEl) ordersEl.textContent = data.new_orders || 0;
            const newOrdersLabelEl = document.querySelector('[data-stat="new_orders_label"]');
            if (newOrdersLabelEl) newOrdersLabelEl.textContent = `${data.new_orders || 0} đơn`;
            const returnsEl = document.querySelector('[data-stat="pending_returns"]');
            if (returnsEl) returnsEl.textContent = data.pending_returns || 0;
        }
    } catch (error) {
        console.error('Không tải được thống kê dashboard', error);
    }
}

let revenueChartInstance = null;

async function renderRevenueChart() {
    const canvas = document.getElementById('revenueChart');
    if (!canvas || typeof Chart === 'undefined') return;

    try {
        const response = await fetch('/api/dashboard/stats?days=7', { credentials: 'same-origin' });
        const data = await response.json();

        // Build labels + data — fallback to 7 dummy days if API doesn't return series
        const labels = data.labels || Array.from({ length: 7 }, (_, i) => {
            const d = new Date();
            d.setDate(d.getDate() - (6 - i));
            return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
        });
        const values = data.daily_revenue || data.revenue_series || [0, 0, 0, 0, 0, 0, 0];

        if (revenueChartInstance) revenueChartInstance.destroy();

        const styles = getComputedStyle(document.documentElement);
        const primary = styles.getPropertyValue('--brand-primary').trim() || '#003152';
        const gridColor = styles.getPropertyValue('--border-soft').trim() || 'rgba(0,0,0,0.08)';
        const textColor = styles.getPropertyValue('--text-muted').trim() || '#64748b';

        revenueChartInstance = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Doanh thu (VND)',
                    data: values,
                    borderColor: primary,
                    backgroundColor: primary + '20',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointBackgroundColor: primary
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => formatCurrency(ctx.parsed.y)
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        suggestedMax: 1000000,
                        ticks: {
                            color: textColor,
                            callback: (v) => v >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? (v / 1e3).toFixed(0) + 'K' : v
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

        // Range button handlers
        document.querySelectorAll('.chart-btn[data-range]').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.chart-btn[data-range]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const range = btn.dataset.range;
                fetch(`/api/dashboard/stats?days=${range}`, { credentials: 'same-origin' })
                    .then(r => r.json())
                    .then(d => {
                        if (revenueChartInstance && d) {
                            revenueChartInstance.data.labels = d.labels || revenueChartInstance.data.labels;
                            revenueChartInstance.data.datasets[0].data = d.daily_revenue || d.revenue_series || revenueChartInstance.data.datasets[0].data;
                            revenueChartInstance.update();
                        }
                    })
                    .catch(() => {});
            });
        });
    } catch (error) {
        console.error('Cannot render revenue chart:', error);
    }
}

async function loadTopProducts() {
    const container = document.getElementById('topProductsList');
    if (!container) return;

    try {
        // Get recent sales to compute top products
        const response = await fetch('/api/sales/history?limit=50', { credentials: 'same-origin' });
        if (!response.ok) {
            container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-box-open"></i><p>Chưa có dữ liệu bán hàng</p></div>';
            return;
        }
        const data = await response.json();

        // Aggregate product sales
        const productMap = new Map();
        (data.sales || []).forEach(sale => {
            (sale.items || []).forEach(item => {
                const key = item.product_id;
                const existing = productMap.get(key) || { name: item.product_name || item.name || 'Sản phẩm', code: item.product_code || '', qty: 0, revenue: 0 };
                existing.qty += item.quantity || 0;
                existing.revenue += (item.quantity || 0) * (item.unit_price || 0);
                productMap.set(key, existing);
            });
        });

        const top = Array.from(productMap.values())
            .sort((a, b) => b.qty - a.qty)
            .slice(0, 5);

        if (top.length === 0) {
            container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-box-open"></i><p>Chưa có sản phẩm bán chạy</p></div>';
            return;
        }

        container.innerHTML = top.map((p, i) => `
            <div class="iot-event">
                <div class="iot-event__icon iot-event__icon--${i % 2 === 0 ? 'blue' : 'green'}">
                    <span style="font-weight: 700;">${i + 1}</span>
                </div>
                <div class="iot-event__content">
                    <p class="iot-event__title">${escapeHtml(p.name)}</p>
                    <span class="iot-event__meta">${p.qty} sản phẩm · ${formatCurrency(p.revenue)}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Cannot load top products:', error);
        container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><p>Không tải được dữ liệu</p></div>';
    }
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

function formatCurrency(value) {
    if (value == null || isNaN(value)) return '0 ₫';
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
}
