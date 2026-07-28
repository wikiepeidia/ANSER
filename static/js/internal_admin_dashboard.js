/**
 * Internal Admin Dashboard - Mock Data & Rendering
 */

(function() {
    'use strict';

    // ==================== MOCK DATA ====================
    const MOCK_DATA = {
        platform_health: {
            ban_le: { status: 'online', last_check: '2 phút trước' },
            san_xuat: { status: 'online', last_check: '2 phút trước' },
            gateway: { status: 'online', last_check: '1 phút trước' },
            n8n: { status: 'online', last_check: '5 phút trước' },
            dl_service: { status: 'offline', last_check: '1 giờ trước' }
        },
        platform_overview: {
            total_shops: 142,
            total_revenue: 2350000000, // VND
            total_users: 1247,
            total_orders_24h: 8934
        },
        apps: {
            ban_le: {
                name: 'Bán lẻ',
                shops_active: 98,
                shops_total: 110,
                revenue_month: 1800000000,
                orders_24h: 7234,
                top_shop: 'ABC Store'
            },
            san_xuat: {
                name: 'Sản xuất',
                productions_active: 44,
                productions_total: 48,
                revenue_month: 550000000,
                orders_24h: 1700,
                pending_qc: 12
            }
        },
        n8n_workflows: [
            { name: 'sync_inventory', status: 'success', last_run: '5 phút trước' },
            { name: 'sync_orders', status: 'success', last_run: '3 phút trước' },
            { name: 'daily_report', status: 'success', last_run: '1 giờ trước' },
            { name: 'sync_products', status: 'warning', last_run: '2 giờ trước' },
            { name: 'backup', status: 'failed', last_run: '6 giờ trước' },
            { name: 'send_notifications', status: 'success', last_run: '10 phút trước' }
        ]
    };

    // ==================== UTILITY FUNCTIONS ====================
    
    /**
     * Format number to short VND format
     */
    function formatCurrency(num) {
        if (num >= 1000000000) {
            return (num / 1000000000).toFixed(1) + 'B';
        } else if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    /**
     * Format number with thousand separators
     */
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    /**
     * Get current time string
     */
    function getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    /**
     * Get current date/time string
     */
    function getCurrentDateTime() {
        const now = new Date();
        return now.toLocaleString('vi-VN', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    // ==================== RENDER FUNCTIONS ====================

    /**
     * Update platform overview stats
     */
    function renderPlatformOverview() {
        const data = MOCK_DATA.platform_overview;
        
        document.getElementById('totalShops').textContent = formatNumber(data.total_shops);
        document.getElementById('totalRevenue').textContent = formatCurrency(data.total_revenue);
        document.getElementById('totalUsers').textContent = formatNumber(data.total_users);
        document.getElementById('totalOrders').textContent = formatNumber(data.total_orders_24h);
    }

    /**
     * Update platform health indicators
     */
    function renderPlatformHealth() {
        const health = MOCK_DATA.platform_health;
        
        // Update health cards
        updateHealthCard('health-banle', health.ban_le);
        updateHealthCard('health-sanxuat', health.san_xuat);
        updateHealthCard('health-gateway', health.gateway);
        updateHealthCard('health-n8n', health.n8n);
        updateHealthCard('health-dl', health.dl_service);
    }

    function updateHealthCard(cardId, service) {
        const card = document.getElementById(cardId);
        if (!card) return;
        
        const statusDot = card.querySelector('.status-dot');
        const statusText = card.querySelector('.health-status');
        const timeText = card.querySelector('.health-time');
        
        // Update status indicator
        statusDot.className = 'status-dot';
        if (service.status === 'online') {
            statusDot.classList.add('status-online');
        } else if (service.status === 'warning') {
            statusDot.classList.add('status-warning');
        } else {
            statusDot.classList.add('status-offline');
        }
        
        // Update status text
        statusText.innerHTML = `<span class="status-dot status-${service.status}"></span> ${service.status === 'online' ? 'Online' : service.status === 'warning' ? 'Warning' : 'Offline'}`;
        
        // Update time
        timeText.textContent = service.last_check;
    }

    /**
     * Update per-app statistics
     */
    function renderAppStats() {
        const apps = MOCK_DATA.apps;
        
        // Ban le stats
        document.getElementById('retail-shops').textContent = `${apps.ban_le.shops_active}/${apps.ban_le.shops_total}`;
        document.getElementById('retail-revenue').textContent = formatCurrency(apps.ban_le.revenue_month);
        document.getElementById('retail-orders').textContent = formatNumber(apps.ban_le.orders_24h);
        document.getElementById('retail-topshop').textContent = apps.ban_le.top_shop;
        
        // San xuat stats
        document.getElementById('sanxuat-productions').textContent = `${apps.san_xuat.productions_active}/${apps.san_xuat.productions_total}`;
        document.getElementById('sanxuat-revenue').textContent = formatCurrency(apps.san_xuat.revenue_month);
        document.getElementById('sanxuat-orders').textContent = formatNumber(apps.san_xuat.orders_24h);
        document.getElementById('sanxuat-pendingqc').textContent = apps.san_xuat.pending_qc;
    }

    /**
     * Render n8n workflows list
     */
    function renderWorkflows() {
        const workflowsList = document.getElementById('workflowsList');
        if (!workflowsList) return;
        
        const workflows = MOCK_DATA.n8n_workflows;
        
        workflowsList.innerHTML = workflows.map(workflow => `
            <div class="workflow-item">
                <div class="workflow-icon ${workflow.status}">
                    <i class="fas fa-${getWorkflowIcon(workflow.status)}"></i>
                </div>
                <div class="workflow-info">
                    <div class="workflow-name">${formatWorkflowName(workflow.name)}</div>
                    <div class="workflow-time">${workflow.last_run}</div>
                </div>
            </div>
        `).join('');
    }

    function getWorkflowIcon(status) {
        switch(status) {
            case 'success': return 'check';
            case 'warning': return 'exclamation';
            case 'failed': return 'times';
            default: return 'circle';
        }
    }

    function formatWorkflowName(name) {
        return name.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    /**
     * Update time displays
     */
    function updateTimeDisplays() {
        document.getElementById('serverTime').textContent = getCurrentTime();
        document.getElementById('lastRefreshTime').textContent = getCurrentDateTime();
    }

    // ==================== ACTIONS ====================

    /**
     * Refresh all data
     */
    function refreshData() {
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.classList.add('loading');
        }
        
        // Simulate loading
        setTimeout(() => {
            renderAll();
            
            if (refreshBtn) {
                refreshBtn.classList.remove('loading');
            }
            
            document.getElementById('lastUpdate').textContent = `Cập nhật: ${getCurrentDateTime()}`;
        }, 500);
    }

    /**
     * Render all components
     */
    function renderAll() {
        renderPlatformOverview();
        renderPlatformHealth();
        renderAppStats();
        renderWorkflows();
        updateTimeDisplays();
    }

    // ==================== INITIALIZATION ====================

    function init() {
        // Initial render
        renderAll();
        
        // Setup refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', refreshData);
        }
        
        // Auto refresh every 30 seconds
        setInterval(refreshData, 30000);
        
        // Update time every second
        setInterval(updateTimeDisplays, 1000);
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
