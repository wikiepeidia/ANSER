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

    const fetchAndRender = async () => {
        try {
            console.debug('Fetching analytics data...');
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
                options: { responsive:true, maintainAspectRatio:true, aspectRatio:1, plugins:{ tooltip } }
            });
            try { trafficSourcesChart.update(); trafficSourcesChart.resize(); } catch(e) { /* ignore */ }

            // Render a small textual legend for compact layout
            const legendEl = document.getElementById('trafficLegend');
            if (legendEl && data.traffic_sources && Array.isArray(data.traffic_sources.labels)) {
                const colors = ['#4285F4','#34A853','#FBBC05','#EA4335'];
                legendEl.innerHTML = data.traffic_sources.labels.map((l,i)=>`<div class="traffic-legend-item" style="display:inline-block;margin-right:10px;font-weight:600"><span class="traffic-legend-swatch" style="display:inline-block;width:12px;height:8px;background:${colors[i]};border-radius:2px;margin-right:6px"></span><span class="traffic-legend-label">${l}</span></div>`).join('');
            }
        }

        // Ensure charts resize correctly after render
        try {
            if (dailyUsersChart) { dailyUsersChart.update(); dailyUsersChart.resize(); }
            if (trafficSourcesChart) { trafficSourcesChart.update(); trafficSourcesChart.resize(); }
        } catch (e) { console.warn('Chart resize/update failed', e); }
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
