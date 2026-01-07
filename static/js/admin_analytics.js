(() => {
    // Minimal, robust analytics UI script expecting structured data from /api/admin/analytics/data
    let dailyUsersChart, trafficSourcesChart;
    const dom = {};

    const SELECTORS = {
        dailyUsersChart: 'dailyUsersChart',
        trafficSourcesChart: 'trafficSourcesChart',
        totalUsers: 'totalUsers',
        totalPageViews: 'totalPageViews',
        avgTime: 'avgTime',
        newUsers: 'newUsers',
        topPagesContainer: 'topPagesContainer',
        analyticsContainer: 'analyticsContainer',
        errorMessage: 'errorMessage'
    };

    const getThemeColors = () => {
        const styles = getComputedStyle(document.documentElement);
        return {
            text: styles.getPropertyValue('--gray-900').trim() || '#0f172a',
            border: styles.getPropertyValue('--border-soft').trim() || 'rgba(15, 23, 42, 0.12)',
            surfaceAlt: styles.getPropertyValue('--surface-200').trim() || '#f8fafc',
            primary: styles.getPropertyValue('--primary').trim() || '#3b82f6',
            secondary: styles.getPropertyValue('--secondary').trim() || '#6366f1'
        };
    };

    const applyChartDefaults = () => {
        const colors = getThemeColors();
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not available');
            showError('Charting library missing. Charts will not render.');
            return colors;
        }
        // Basic colors
        Chart.defaults.color = colors.text;
        Chart.defaults.borderColor = colors.border;
        Chart.defaults.font.family = 'Inter, "Segoe UI", sans-serif';

        // Determine dark mode based on attribute/class
        const isDark = (document.documentElement.getAttribute('data-theme') === 'dark') || document.body.classList.contains('dark-mode');
        const tooltipBg = isDark ? 'rgba(15,23,42,0.92)' : colors.surfaceAlt;
        const tooltipText = isDark ? '#ffffff' : colors.text;

        // Tooltip styling to respect theme (title/body color, background, borders)
        Chart.defaults.plugins = Chart.defaults.plugins || {};
        Chart.defaults.plugins.tooltip = Object.assign({}, Chart.defaults.plugins.tooltip || {}, {
            backgroundColor: tooltipBg,
            titleColor: tooltipText,
            bodyColor: tooltipText,
            borderColor: colors.border,
            borderWidth: 1,
            padding: 8,
        });

        // Legend label color
        Chart.defaults.plugins.legend = Object.assign({}, Chart.defaults.plugins.legend || {}, {
            labels: Object.assign({}, (Chart.defaults.plugins.legend && Chart.defaults.plugins.legend.labels) || {}, { color: colors.text })
        });

        return colors;
    };

    const cacheDom = () => {
        for (const k in SELECTORS) dom[k] = document.getElementById(SELECTORS[k]);
    };

    const showError = (msg) => {
        if (dom.errorMessage) {
            dom.errorMessage.style.display = 'block';
            dom.errorMessage.textContent = msg;
        }
    };

    const fetchAndRender = async (forceLive = false) => {
        try {
            console.debug('Fetching analytics data...');
            
            // Load mock data by default unless forceLive is true
            if (!forceLive) {
                console.debug('Loading mock data by default');
                loadMockData();
                return;
            }
            
            const resp = await fetch('/api/admin/analytics/data', {
                credentials: 'include'
            });
            // read body as text so we can surface raw JSON in the debug panel
            const respText = await resp.text();
            let parsed = null;
            try { parsed = JSON.parse(respText); } catch(e) { parsed = { __raw: respText }; }
            console.debug('Analytics response:', parsed, resp.status);

            // If cached response is empty, attempt a forced live fetch to bypass cache
            const isCachedEmpty = (parsed && parsed.source === 'cache' && (
                !(parsed.data && parsed.data.daily_users && parsed.data.daily_users.labels && parsed.data.daily_users.labels.length) &&
                !(parsed.data && parsed.data.traffic_sources && parsed.data.traffic_sources.labels && parsed.data.traffic_sources.labels.length) &&
                !(parsed.data && parsed.data.top_pages && parsed.data.top_pages.length) &&
                !(parsed.data && parsed.data.user_stats && (parsed.data.user_stats.total_users || 0) > 0)
            ));
            if (isCachedEmpty) {
                console.warn('Cached analytics data is empty — forcing a live refresh');
                const forcedResp = await fetch('/api/admin/analytics/data?force=1', { credentials: 'include' });
                const forcedText = await forcedResp.text();
                let forcedJson = null;
                try { forcedJson = JSON.parse(forcedText); } catch(e) { forcedJson = { __raw: forcedText }; }
                console.debug('Forced analytics fetch:', forcedJson, forcedResp.status);
                if (forcedJson && forcedJson.success) {
                    parsed = forcedJson;
                }
            }

            if (!resp.ok) {
                // show helpful message about auth/login
                showError('Failed to load analytics data (HTTP ' + resp.status + '). Please ensure you are signed in as an admin or manager.');
                showNoDataPlaceholder('No analytics data (unauthorized)');
                // Render client-side mock data so UI is visible and interactive for debugging
                renderClientMockData();
                // Update badge to show mock data
                const badge = document.getElementById('analyticsSourceBadge');
                if (badge) {
                    badge.textContent = 'Mock';
                    badge.classList.remove('bg-success');
                    badge.classList.add('bg-warning');
                }
                return;
            }

            const json = parsed;
            if (!json.success) throw new Error(json.error || 'No data');
            const data = json.data;

            // Metrics
            if (dom.totalUsers) dom.totalUsers.textContent = (data.user_stats.total_users || 0).toLocaleString();
            if (dom.totalPageViews) dom.totalPageViews.textContent = (data.daily_users.page_views || []).reduce((a,b)=>a+b,0).toLocaleString();
            if (dom.avgTime) dom.avgTime.textContent = `${Math.round((data.user_stats.avg_engagement_time || 0)/60)}m ${Math.round((data.user_stats.avg_engagement_time || 0)%60)}s`;
            if (dom.newUsers) dom.newUsers.textContent = (data.user_stats.new_users || 0).toLocaleString();

            // Indicate data source (live/mock/cache)
            const badge = document.getElementById('analyticsSourceBadge');
            console.log('Updating badge:', badge, 'with source:', json.source);
            if (badge) {
                const sourceText = json.source ? (json.source === 'live' ? 'Live' : (json.source === 'cache' ? 'Cache' : 'Mock')) : 'Unknown';
                badge.textContent = sourceText;
                console.log('Badge text set to:', sourceText);
                console.debug('Analytics JSON:', json, resp.status);
            }

            // If backend reports empty live data, show a clear UI message and do NOT fallback to mock
            if (json.source === 'live' && json.empty) {
                showError('Google Analytics returned no data for this property / date range. Verify tracking and property settings.');
                showNoDataPlaceholder('No analytics data (live-empty)');
                if (badge) {
                    badge.textContent = 'Live (no data)';
                    badge.classList.remove('bg-warning','bg-secondary');
                    badge.classList.add('bg-info');
                }
                window.__lastAnalyticsData = data;
                console.debug('Analytics data loaded (empty)', data);
                // Render empty charts so the UI shows placeholders
                buildCharts(data);
                return;
            }

            if (json.source === 'mock') {
                badge.classList.remove('bg-success');
                badge.classList.add('bg-warning');
            } else if (json.source === 'live') {
                badge.classList.remove('bg-warning');
                badge.classList.add('bg-success');
                // Update button to show "Load Mock Data" when live data is active
                const btnToggle = document.getElementById('btnLoadMock');
                if (btnToggle) {
                    btnToggle.innerHTML = '<i class="fas fa-database"></i><span>Load Mock Data</span>';
                    window.__currentDataSource = 'live';
                }
            } else {
                badge.classList.remove('bg-warning');
                badge.classList.remove('bg-success');
                badge.classList.add('bg-secondary');
            }

            // Clear previous error if any
            if (dom.errorMessage) dom.errorMessage.style.display = 'none';

            // Save and render data
            window.__lastAnalyticsData = data;
            console.debug('Analytics data loaded', data);
            // Charts
            buildCharts(data);

            // Top pages
            if (dom.topPagesContainer) {
                dom.topPagesContainer.innerHTML = data.top_pages.map(p => `<div class="list-item"><span>${p.page}</span><strong>${p.views.toLocaleString()}</strong></div>`).join('');
            }
        } catch (e) {
            console.error('Analytics load failed', e);
            showError('Failed to load analytics data.');
            showNoDataPlaceholder('No analytics data (load failed)');
            // Provide mock data so the UI is interactive for debugging
            renderClientMockData();
        }
    };

    const teardown = (c) => { if (c) c.destroy(); };

    const clearNoDataPlaceholders = () => {
        document.querySelectorAll('.chart-card .no-data').forEach(n => n.remove());
    };
    const showNoDataPlaceholder = (message = 'No data to display') => {
        document.querySelectorAll('.chart-card').forEach(c => {
            if (!c.querySelector('.no-data')) {
                const div = document.createElement('div');
                div.className = 'no-data';
                div.textContent = message;
                c.appendChild(div);
            }
        });
    };

    // Debug panel helpers


    // Quick client-side tracking check
    const checkTrackingInstalled = () => {
        const scripts = Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
        const matches = scripts.filter(s => /googletagmanager|google-analytics|gtag|analytics.js|gstatic/.test(s));
        const foundGtag = !!window.gtag;
        return { found: foundGtag || matches.length>0, details: (foundGtag? 'window.gtag() present' : (matches.length? 'Found scripts: ' + matches.join(', ') : 'No GA scripts found')) };
    };

    // Debug panel removed; keep console logging only
    const updateDebugPanel = (body, status) => { console.debug('Debug:', status, body); };

    const renderClientMockData = () => {
        const sample = {
            daily_users: { labels: ['20251220','20251221','20251222','20251223','20251224'], active_users: [30,45,38,50,42], page_views: [120,180,150,220,190] },
            traffic_sources: { labels: ['Direct','Organic','Referral','Social'], users: [80,40,20,10] },
            top_pages: [{page:'/','views':350},{page:'/products','views':210}],
            user_stats: { total_users: 520, new_users: 34, avg_engagement_time: 240 }
        };
        // Populate metric cards
        if (dom.totalUsers) dom.totalUsers.textContent = (sample.user_stats.total_users || 0).toLocaleString();
        if (dom.totalPageViews) dom.totalPageViews.textContent = (sample.daily_users.page_views || []).reduce((a,b)=>a+b,0).toLocaleString();
        if (dom.avgTime) dom.avgTime.textContent = `${Math.round((sample.user_stats.avg_engagement_time || 0)/60)}m ${Math.round((sample.user_stats.avg_engagement_time || 0)%60)}s`;
        if (dom.newUsers) dom.newUsers.textContent = (sample.user_stats.new_users || 0).toLocaleString();

        // Top pages
        if (dom.topPagesContainer) dom.topPagesContainer.innerHTML = sample.top_pages.map(p => `<div class="list-item"><span>${p.page}</span><strong>${p.views.toLocaleString()}</strong></div>`).join('');

        // Render charts
        window.__lastAnalyticsData = sample;
        clearNoDataPlaceholders();
        buildCharts(sample);
        updateDebugPanel({source: 'mock', data: sample}, 'mock');
    };

    const buildCharts = (data) => {
        clearNoDataPlaceholders();
        const colors = applyChartDefaults();
        const tooltip = { backgroundColor: colors.surfaceAlt, borderColor: colors.border, borderWidth: 1 };

        // Daily users
        if (dom.dailyUsersChart && data.daily_users) {
            teardown(dailyUsersChart);
            dailyUsersChart = new Chart(dom.dailyUsersChart, {
                type: 'line',
                data: { labels: data.daily_users.labels.map(d=>d.replace(/(\d{4})(\d{2})(\d{2})/, '$3/$2')), datasets: [{ label: 'Active Users', data: data.daily_users.active_users, borderColor: colors.primary, backgroundColor: 'rgba(59,130,246,0.08)', fill:true, tension: 0.3 }, { label:'Page Views', data:data.daily_users.page_views, borderColor: colors.secondary, backgroundColor: 'rgba(99,102,241,0.08)', fill:true, tension: 0.3 }] },
                options: { responsive:true, maintainAspectRatio:false, devicePixelRatio: window.devicePixelRatio || 1, plugins:{ tooltip }, scales:{ y:{ beginAtZero:true } } }
            });
        }

        // Traffic sources (small doughnut, render legend into #trafficLegend)
        if (dom.trafficSourcesChart && data.traffic_sources) {
            teardown(trafficSourcesChart);
            trafficSourcesChart = new Chart(dom.trafficSourcesChart, {
                type: 'doughnut',
                data: { labels: data.traffic_sources.labels, datasets:[{ data:data.traffic_sources.users, backgroundColor:['#4285F4','#34A853','#FBBC05','#EA4335'] }] },
                options: { 
                    responsive:true, 
                    maintainAspectRatio:true, 
                    aspectRatio:1, 
                    plugins:{ 
                        tooltip,
                        legend: {
                            display: true,
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                boxWidth: 15,
                                boxHeight: 15,
                                font: {
                                    size: 13,
                                    family: 'Inter, "Segoe UI", sans-serif',
                                    weight: '600'
                                },
                                color: colors.text,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }
                        }
                    } 
                }
            });
            try { trafficSourcesChart.update(); trafficSourcesChart.resize(); } catch(e) { /* ignore */ }
        }

        // Ensure charts resize correctly after render
        try {
            if (dailyUsersChart) { dailyUsersChart.update(); dailyUsersChart.resize(); }
            if (trafficSourcesChart) { trafficSourcesChart.update(); trafficSourcesChart.resize(); }
        } catch (e) { console.warn('Chart resize/update failed', e); }
    };

    const loadVIPCustomers = async () => {
        try {
            const response = await fetch('/api/admin/users');
            if (!response.ok) {
                throw new Error('Failed to load customers');
            }

            const data = await response.json();
            const customers = (data.users || []).filter((user) => user.role === 'customer');
            const container = document.getElementById('topCustomers');

            if (!container) {
                return;
            }

            if (customers.length === 0) {
                container.innerHTML = '<div class="text-center py-4 text-muted">No VIP customers found</div>';
                return;
            }

            // Sort by mock revenue and take top 5
            const topCustomers = customers
                .map(customer => ({
                    ...customer,
                    revenue: Math.floor(Math.random() * 100000000) + 50000000,
                    orders: Math.floor(Math.random() * 50) + 10
                }))
                .sort((a, b) => b.revenue - a.revenue)
                .slice(0, 5);

            container.innerHTML = topCustomers
                .map((customer, index) => {
                    const rankClass = index === 0 ? 'gold' : index === 1 ? 'silver' : index === 2 ? 'bronze' : '';
                    return `
                        <div class="customer-item">
                            <div class="item-rank ${rankClass}">${index + 1}</div>
                            <div class="item-info">
                                <div class="item-name">${customer.name}</div>
                                <div class="item-detail">${customer.email} • ${customer.orders} orders</div>
                            </div>
                            <div>
                                <strong style="color: #43e97b; font-size: 16px;">${formatCurrency(customer.revenue)} VND</strong>
                            </div>
                        </div>
                    `;
                })
                .join('');
        } catch (error) {
            console.error('Error loading VIP customers:', error);
            const container = document.getElementById('topCustomers');
            if (container) {
                container.innerHTML = '<div class="text-center py-4 text-danger">Failed to load customers</div>';
            }
        }
    };

    const loadManagerPerformance = async () => {
        try {
            const response = await fetch('/api/admin/users');
            if (!response.ok) {
                throw new Error('Failed to load managers');
            }

            const data = await response.json();
            const managers = (data.users || []).filter((user) => user.role === 'manager');
            const tbody = document.getElementById('managerPerformanceTable');

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
                            <td><span class="badge bg-info">${permissionsGranted} permissions</span></td>
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

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('vi-VN').format(amount);
    };

    const highlightSubChart = (key) => {
        // Add a visual highlight to selected sub-chart inside chartsSection
        document.querySelectorAll('.chart-card').forEach(c => c.classList.remove('highlight'));
        if (!key) return;
        const el = document.querySelector(`.chart-card[data-chart="${key}"]`);
        if (el) el.classList.add('highlight');
    };

    const switchTab = (targetId, subChartKey) => {
        const sections = document.querySelectorAll('.analytics-section');
        sections.forEach(s => s.classList.remove('active'));
        const target = document.getElementById(targetId);
        if (target) target.classList.add('active');

        document.querySelectorAll('.tab-button').forEach(btn => {
            const active = btn.dataset.target === targetId && (typeof subChartKey === 'undefined' || btn.dataset.chart === subChartKey || btn.dataset.chart === undefined);
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });

        // If charts section is active, rebuild charts to ensure proper sizing and colors
        if (targetId === 'chartsSection' && window.__lastAnalyticsData) {
            buildCharts(window.__lastAnalyticsData);
            highlightSubChart(subChartKey);
        }

        if (targetId === 'managerSection') {
            // load managers' performance when tab becomes active
            loadManagerPerformance();
        }

        if (targetId === 'customersSection') {
            // load VIP customers when tab becomes active
            loadVIPCustomers();
        }
    };

    const initTabs = () => {
        const buttons = Array.from(document.querySelectorAll('.tab-button'));
        if (!buttons.length) return;

        // Click/key handlers for each button
        buttons.forEach((btn, idx) => {
            btn.addEventListener('click', () => switchTab(btn.dataset.target, btn.dataset.chart));
            btn.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); switchTab(btn.dataset.target, btn.dataset.chart); }
                if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                    const nextIdx = e.key === 'ArrowRight' ? (idx + 1) % buttons.length : (idx - 1 + buttons.length) % buttons.length;
                    buttons[nextIdx].focus();
                }
            });
        });

        // Event delegation fallback: container-level click handler
        const tabsContainer = document.querySelector('.analytics-tabs');
        if (tabsContainer) {
            tabsContainer.addEventListener('click', (e) => {
                const btn = e.target.closest('.tab-button');
                if (btn) switchTab(btn.dataset.target, btn.dataset.chart);
            });
        }

        // Set initial active tab
        const activeBtn = document.querySelector('.tab-button.active') || buttons[0];
        buttons.forEach(btn => btn.classList.toggle('active', btn === activeBtn));
        buttons.forEach(btn => btn.setAttribute('aria-selected', btn === activeBtn ? 'true' : 'false'));

        // Hide all sections except active
        const sections = document.querySelectorAll('.analytics-section');
        sections.forEach(s => s.classList.remove('active'));
        const firstTarget = activeBtn.dataset.target;
        const el = document.getElementById(firstTarget);
        if (el) el.classList.add('active');
    };

    const observeThemeChanges = () => {
        const html = document.documentElement;
        if (!html || typeof MutationObserver === 'undefined') return;
        const obs = new MutationObserver((mutations) => {
            if (mutations.some(m => m.attributeName === 'data-theme')) {
                if (window.__lastAnalyticsData) buildCharts(window.__lastAnalyticsData);
                // refresh active tab visuals
                document.querySelectorAll('.tab-button').forEach(b=> b.classList.toggle('active', b.getAttribute('aria-selected')==='true'));
            }
        });
        obs.observe(html, { attributes: true, attributeFilter: ['data-theme'] });
    };

    // Ensure initial active tab is applied even if CSS or DOM arrives late
    const performMetricAction = (el) => {
        const action = el.dataset.action;
        if (!action) return;

        if (action === 'toggle-dataset') {
            const dsLabel = el.dataset.dataset;
            if (!dailyUsersChart) return;
            const ds = dailyUsersChart.data.datasets.find(d => d.label === dsLabel);
            if (ds) {
                ds.hidden = !ds.hidden;
                dailyUsersChart.update();
                el.classList.toggle('active', !ds.hidden);
            }
        }

        if (action === 'show-info') {
            const info = el.dataset.info;
            const infoPanelId = 'metricInfoPanel';
            let panel = document.getElementById(infoPanelId);
            if (!panel) {
                panel = document.createElement('div');
                panel.id = infoPanelId;
                panel.className = 'metric-info-panel';
                const chartsSection = document.getElementById('chartsSection');
                if (chartsSection) chartsSection.prepend(panel);
            }
            panel.textContent = '';
            if (info === 'avg_engagement') {
                panel.textContent = `Avg engagement: ${Math.round((window.__lastAnalyticsData?.user_stats?.avg_engagement_time||0)/60)} min`;
            } else if (info === 'new_users') {
                panel.textContent = `New users: ${window.__lastAnalyticsData?.user_stats?.new_users || 0}`;
            }
            panel.style.opacity = '1';
            setTimeout(()=>{ panel.style.opacity = '0'; }, 3500);
        }
    };

    const initMetricCards = () => {
        const cards = Array.from(document.querySelectorAll('.metric-card[role="button"]'));
        if (!cards.length) return;
        cards.forEach(c => {
            c.addEventListener('click', ()=> performMetricAction(c));
            c.addEventListener('keydown', (e)=> { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); performMetricAction(c); } });
        });
    };

    document.addEventListener('DOMContentLoaded', () => {
        cacheDom(); fetchAndRender(); initTabs(); observeThemeChanges(); initMetricCards();
        const activeBtn = document.querySelector('.tab-button.active');
        if (activeBtn) {
            activeBtn.focus();
            switchTab(activeBtn.dataset.target);
        }

        const btnCheck = document.getElementById('btnCheckTracking');
        if (btnCheck) {
            btnCheck.addEventListener('click', async () => {
                btnCheck.disabled = true; btnCheck.textContent = 'Refreshing...';
                try {
                    const resp = await fetch('/api/admin/analytics/clear_cache', { method: 'POST', credentials: 'include' });
                    const text = await resp.text();
                    let json;
                    try { json = JSON.parse(text); } catch(e) { json = { success:false, message:'Invalid JSON', raw: text }; }
                    updateDebugPanel({ clear_cache: json }, resp.status);
                    if (resp.ok && json && json.success) {
                        // refetch fresh data
                        // remove any existing debug cache marker
                        await fetchAndRender();
                        alert('Cache cleared and refreshed');
                    } else {
                        alert('Failed to clear cache: ' + (json && json.message || 'Unknown'));
                    }
                } catch (err) {
                    console.error('Clear cache failed', err);
                    alert('Clear cache failed: ' + err.message);
                } finally {
                    btnCheck.disabled = false; btnCheck.textContent = 'Refresh cache';
                }
            });
        }

        // Mock data loading function
        const loadMockData = () => {
            const mockData = {
                "daily_users": {
                    "labels": ["20241220","20241221","20241222","20241223","20241224","20241225","20241226"],
                    "active_users": [120, 135, 140, 130, 150, 145, 160],
                    "page_views": [450, 480, 500, 470, 520, 510, 550]
                },
                "traffic_sources": {
                    "labels": ["Direct","Organic Search","Referral","Social Media"],
                    "users": [85, 40, 15, 10]
                },
                "top_pages": [
                    {"page": "/", "views": 250},
                    {"page": "/products", "views": 150},
                    {"page": "/about", "views": 95},
                    {"page": "/contact", "views": 60},
                    {"page": "/services", "views": 45}
                ],
                "user_stats": {
                    "total_users": 150,
                    "new_users": 35,
                    "avg_engagement_time": 180
                }
            };

            // Manually inject mock data
            window.__lastAnalyticsData = mockData;
            window.__currentDataSource = 'mock';
            
            // Update realtime overview
            const realtimeUsersEl = document.getElementById('realtimeUsers');
            if (realtimeUsersEl) realtimeUsersEl.textContent = '12';
            
            const deviceDesktopEl = document.getElementById('deviceDesktop');
            if (deviceDesktopEl) deviceDesktopEl.textContent = '68%';
            
            const deviceMobileEl = document.getElementById('deviceMobile');
            if (deviceMobileEl) deviceMobileEl.textContent = '32%';
            
            // Update stats cards
            if (dom.totalUsers) dom.totalUsers.textContent = mockData.user_stats.total_users.toLocaleString();
            if (dom.totalPageViews) {
                const totalPageViews = mockData.daily_users.page_views.reduce((a, b) => a + b, 0);
                dom.totalPageViews.textContent = totalPageViews.toLocaleString();
            }
            if (dom.avgTime) {
                const minutes = Math.floor(mockData.user_stats.avg_engagement_time / 60);
                const seconds = mockData.user_stats.avg_engagement_time % 60;
                dom.avgTime.textContent = `${minutes}m ${seconds}s`;
            }
            if (dom.newUsers) dom.newUsers.textContent = mockData.user_stats.new_users.toLocaleString();
            
            // Update top pages
            if (dom.topPagesContainer) {
                dom.topPagesContainer.innerHTML = mockData.top_pages.map(p => 
                    `<div class="list-item"><span>${p.page}</span><strong>${p.views.toLocaleString()}</strong></div>`
                ).join('');
            }
            
            // Build charts
            clearNoDataPlaceholders();
            buildCharts(mockData);
            
            // Update badge
            const badge = document.getElementById('analyticsSourceBadge');
            if (badge) {
                badge.textContent = 'Mock';
                badge.classList.remove('bg-success', 'bg-secondary', 'bg-info');
                badge.classList.add('bg-warning');
            }
            
            // Update button text
            const btnToggle = document.getElementById('btnLoadMock');
            if (btnToggle) {
                btnToggle.innerHTML = '<i class="fas fa-wifi"></i><span>Load Live Data</span>';
            }
            
            // Clear error if any
            if (dom.errorMessage) dom.errorMessage.style.display = 'none';
            
            console.log('Mock data loaded successfully');
        };

        // Mock/Live data toggle button handler
        const btnLoadMock = document.getElementById('btnLoadMock');
        if (btnLoadMock) {
            btnLoadMock.addEventListener('click', async () => {
                const currentSource = window.__currentDataSource || 'mock';
                btnLoadMock.disabled = true;
                
                if (currentSource === 'mock') {
                    // Switch to live data
                    btnLoadMock.textContent = 'Loading...';
                    try {
                        // Clear cache first
                        await fetch('/api/admin/analytics/clear_cache', { method: 'POST', credentials: 'include' });
                        // Force live data fetch
                        await fetchAndRender(true);
                        
                        // Update button
                        btnLoadMock.innerHTML = '<i class="fas fa-database"></i><span>Load Mock Data</span>';
                        window.__currentDataSource = 'live';
                    } catch (err) {
                        console.error('Load live failed', err);
                        alert('Failed to load live data: ' + err.message);
                        btnLoadMock.innerHTML = '<i class="fas fa-wifi"></i><span>Load Live Data</span>';
                    }
                } else {
                    // Switch to mock data
                    btnLoadMock.textContent = 'Loading...';
                    try {
                        loadMockData();
                    } catch (err) {
                        console.error('Load mock failed', err);
                        alert('Failed to load mock data: ' + err.message);
                    }
                }
                
                btnLoadMock.disabled = false;
            });
        }

        // Fallback: if badge is still "Loading..." after 5 seconds, force update
        setTimeout(() => {
            const badge = document.getElementById('analyticsSourceBadge');
            if (badge && badge.textContent === 'Loading...') {
                console.warn('Badge still loading, forcing mock update');
                badge.textContent = 'Mock';
                badge.classList.remove('bg-success', 'bg-secondary');
                badge.classList.add('bg-warning');
            }
        }, 5000);
    });
})();
