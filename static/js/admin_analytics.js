(() => {
    let revenueChart;
    let categoryChart;
    let accessChart;
    let usersChart;
    let themeObserver;

    const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const REVENUE_SERIES = [45000, 52000, 48000, 61000, 55000, 67000, 72000];
    const PROFIT_SERIES = [12000, 15000, 13000, 18000, 16000, 20000, 22000];

    const SELECTORS = {
        timeRange: 'timeRangeFilter',
        totalRevenue: 'totalRevenue',
        revenueChange: 'revenueChange',
        totalVisits: 'totalVisits',
        visitsChange: 'visitsChange',
        totalOrders: 'totalOrders',
        ordersChange: 'ordersChange',
        totalProfit: 'totalProfit',
        profitChange: 'profitChange',
        managerTable: 'managerPerformanceTable',
        topProducts: 'topProducts',
        topCustomers: 'topCustomers',
    };

    const formatCurrency = (value) => value.toLocaleString('en-US');

    const getThemeColors = () => {
        const styles = getComputedStyle(document.documentElement);
        return {
            text: styles.getPropertyValue('--gray-900').trim() || '#0f172a',
            muted: styles.getPropertyValue('--gray-600').trim() || '#64748b',
            border: styles.getPropertyValue('--border-soft').trim() || 'rgba(15, 23, 42, 0.12)',
            surface: styles.getPropertyValue('--surface-100').trim() || '#ffffff',
            surfaceAlt: styles.getPropertyValue('--surface-200').trim() || '#f8fafc',
        };
    };

    const applyChartDefaults = () => {
        const colors = getThemeColors();
        Chart.defaults.color = colors.text;
        Chart.defaults.borderColor = colors.border;
        Chart.defaults.font.family = 'Inter, "Segoe UI", sans-serif';
        return colors;
    };

    const updateMetrics = () => {
        document.getElementById(SELECTORS.totalRevenue).textContent = '245,500,000 VND';
        document.getElementById(SELECTORS.revenueChange).innerHTML = '<i class="fas fa-arrow-up"></i> +15.3%';

        document.getElementById(SELECTORS.totalVisits).textContent = '12,458';
        document.getElementById(SELECTORS.visitsChange).innerHTML = '<i class="fas fa-arrow-up"></i> +8.7%';

        document.getElementById(SELECTORS.totalOrders).textContent = '1,234';
        document.getElementById(SELECTORS.ordersChange).innerHTML = '<i class="fas fa-arrow-up"></i> +12.5%';

        document.getElementById(SELECTORS.totalProfit).textContent = '98,200,000 VND';
        document.getElementById(SELECTORS.profitChange).innerHTML = '<i class="fas fa-arrow-up"></i> +18.2%';
    };

    const teardownChart = (chartInstance) => {
        if (chartInstance) {
            chartInstance.destroy();
        }
    };

    const buildCharts = () => {
        const colors = applyChartDefaults();
        const axisColor = colors.text;
        const gridColor = colors.border;
        const tooltipConfig = {
            backgroundColor: colors.surfaceAlt,
            borderColor: colors.border,
            borderWidth: 1,
            titleColor: axisColor,
            bodyColor: axisColor,
        };

        const revenueCtx = document.getElementById('revenueChart');
        teardownChart(revenueChart);
        revenueChart = new Chart(revenueCtx, {
            type: 'line',
            data: {
                labels: DAYS,
                datasets: [
                    {
                        label: 'Revenue (×1000 VND)',
                        data: REVENUE_SERIES,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true,
                    },
                    {
                        label: 'Profit (×1000 VND)',
                        data: PROFIT_SERIES,
                        borderColor: '#43e97b',
                        backgroundColor: 'rgba(67, 233, 123, 0.1)',
                        tension: 0.4,
                        fill: true,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: axisColor } },
                    tooltip: tooltipConfig,
                },
                scales: {
                    x: {
                        ticks: { color: axisColor },
                        grid: { color: gridColor },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: axisColor },
                        grid: { color: gridColor },
                    },
                },
            },
        });

        const categoryCtx = document.getElementById('categoryChart');
        teardownChart(categoryChart);
        categoryChart = new Chart(categoryCtx, {
            type: 'doughnut',
            data: {
                labels: ['Imports', 'Exports', 'Services', 'Other'],
                datasets: [
                    {
                        data: [120000, 85000, 30000, 10000],
                        backgroundColor: ['#667eea', '#43e97b', '#ffd89b', '#f093fb'],
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true, position: 'bottom', labels: { color: axisColor } },
                    tooltip: tooltipConfig,
                },
            },
        });

        const accessCtx = document.getElementById('accessChart');
        teardownChart(accessChart);
        accessChart = new Chart(accessCtx, {
            type: 'bar',
            data: {
                labels: ['0h', '4h', '8h', '12h', '16h', '20h'],
                datasets: [
                    {
                        label: 'Visits',
                        data: [120, 80, 450, 890, 1200, 650],
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: tooltipConfig,
                },
                scales: {
                    x: {
                        ticks: { color: axisColor },
                        grid: { color: gridColor },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: axisColor },
                        grid: { color: gridColor },
                    },
                },
            },
        });

        const usersCtx = document.getElementById('usersChart');
        teardownChart(usersChart);
        usersChart = new Chart(usersCtx, {
            type: 'line',
            data: {
                labels: DAYS,
                datasets: [
                    {
                        label: 'Active users',
                        data: [45, 52, 48, 61, 55, 67, 72],
                        borderColor: '#f093fb',
                        backgroundColor: 'rgba(240, 147, 251, 0.1)',
                        tension: 0.4,
                        fill: true,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: tooltipConfig,
                },
                scales: {
                    x: {
                        ticks: { color: axisColor },
                        grid: { color: gridColor },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: axisColor },
                        grid: { color: gridColor },
                    },
                },
            },
        });
    };

    const observeThemeChanges = () => {
        const html = document.documentElement;
        if (!html || typeof MutationObserver === 'undefined') {
            return;
        }

        themeObserver?.disconnect();
        themeObserver = new MutationObserver((mutations) => {
            const hasThemeMutation = mutations.some((mutation) => mutation.attributeName === 'data-theme');
            if (hasThemeMutation) {
                buildCharts();
            }
        });

        themeObserver.observe(html, { attributes: true, attributeFilter: ['data-theme'] });
    };

    const loadManagerPerformance = async () => {
        try {
            const response = await fetch('/api/admin/users');
            if (!response.ok) {
                throw new Error('Failed to load managers');
            }

            const data = await response.json();
            const managers = (data.users || []).filter((user) => user.role === 'manager');
            const tbody = document.getElementById(SELECTORS.managerTable);

            if (!tbody) {
                return;
            }

                if (managers.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center">No managers found</td></tr>';
                return;
            }

            tbody.innerHTML = managers
                .map((manager) => {
                    const revenue = Math.floor(Math.random() * 50000000) + 20000000;
                    const usersManaged = Math.floor(Math.random() * 15) + 5;
                    const permissionsGranted = Math.floor(Math.random() * 30) + 10;

                    return `
                        <tr>
                            <td><strong>${manager.name}</strong></td>
                            <td>${manager.email}</td>
                            <td><span class="badge bg-primary">${usersManaged} users</span></td>
                            <td><span class="badge bg-info">${permissionsGranted} quyền</span></td>
                            <td><strong style="color: #43e97b;">${formatCurrency(revenue)} VND</strong></td>
                            <td><span class="badge bg-success">Active</span></td>
                        </tr>
                    `;
                })
                .join('');
        } catch (error) {
            console.error('Error loading manager performance:', error);
        }
    };

    const loadTopProducts = () => {
        const products = [
            { name: 'Laptop Dell XPS 13', sold: 245, revenue: 45000000 },
            { name: 'iPhone 15 Pro Max', sold: 189, revenue: 38000000 },
            { name: 'Samsung Galaxy S24', sold: 156, revenue: 28000000 },
            { name: 'MacBook Pro M3', sold: 134, revenue: 67000000 },
            { name: 'AirPods Pro 2', sold: 298, revenue: 15000000 },
        ];

        const container = document.getElementById(SELECTORS.topProducts);
        if (!container) {
            return;
        }

        container.innerHTML = products
            .map((product, idx) => {
                const rankClass = idx === 0 ? 'gold' : idx === 1 ? 'silver' : idx === 2 ? 'bronze' : '';
                return `
                    <div class="product-item">
                        <div class="item-rank ${rankClass}">${idx + 1}</div>
                        <div class="item-info">
                            <div class="item-name">${product.name}</div>
                            <div class="item-detail">Sold: ${product.sold} units</div>
                        </div>
                        <div class="item-value">${(product.revenue / 1_000_000).toFixed(1)}M VND</div>
                    </div>
                `;
            })
            .join('');
    };

    const loadTopCustomers = () => {
        const customers = [
            { name: 'Nguyễn Văn A', orders: 45, revenue: 125000000 },
            { name: 'Trần Thị B', orders: 38, revenue: 98000000 },
            { name: 'Lê Văn C', orders: 32, revenue: 87000000 },
            { name: 'Phạm Thị D', orders: 28, revenue: 76000000 },
            { name: 'Hoàng Văn E', orders: 25, revenue: 65000000 },
        ];

        const container = document.getElementById(SELECTORS.topCustomers);
        if (!container) {
            return;
        }

        container.innerHTML = customers
            .map((customer, idx) => {
                const rankClass = idx === 0 ? 'gold' : idx === 1 ? 'silver' : idx === 2 ? 'bronze' : '';
                return `
                    <div class="customer-item">
                        <div class="item-rank ${rankClass}">${idx + 1}</div>
                        <div class="item-info">
                            <div class="item-name">${customer.name}</div>
                            <div class="item-detail">${customer.orders} orders</div>
                        </div>
                        <div class="item-value">${(customer.revenue / 1_000_000).toFixed(1)}M VND</div>
                    </div>
                `;
            })
            .join('');
    };

    const loadAnalytics = () => {
        updateMetrics();
        buildCharts();
        loadManagerPerformance();
        loadTopProducts();
        loadTopCustomers();
    };

    const wireEvents = () => {
        const timeRangeSelect = document.getElementById(SELECTORS.timeRange);
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', loadAnalytics);
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        wireEvents();
        loadAnalytics();
        observeThemeChanges();
    });
})();
