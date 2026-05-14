(() => {
    const START_TIME = Date.now();

    const SELECTORS = {
        totalUsers: 'totalUsers',
        totalManagers: 'totalManagers',
        totalProducts: 'totalProducts',
        totalCustomers: 'totalCustomers',
        activities: 'recentActivities',
        uptime: 'systemUptime',
    };

    const safeSetText = (id, value) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = value;
        }
    };

    const fetchJson = async (url) => {
        const response = await fetch(url, { credentials: 'same-origin' });
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }
        return response.json();
    };

    const loadUserStats = async () => {
        try {
            const { users = [] } = await fetchJson('/api/admin/users');
            safeSetText(SELECTORS.totalUsers, users.length);
            safeSetText(
                SELECTORS.totalManagers,
                users.filter((user) => user.role === 'manager').length,
            );
        } catch (error) {
            console.error('Failed to load user stats', error);
        }
    };

    const loadProducts = async () => {
        try {
            const { products = [] } = await fetchJson('/api/products');
            safeSetText(SELECTORS.totalProducts, products.length);
        } catch (error) {
            console.error('Failed to load products', error);
        }
    };

    const loadCustomers = async () => {
        try {
            const { customers = [] } = await fetchJson('/api/customers');
            safeSetText(SELECTORS.totalCustomers, customers.length);
        } catch (error) {
            console.error('Failed to load customers', error);
        }
    };

    const loadActivities = async () => {
        const container = document.getElementById(SELECTORS.activities);
        if (!container) return;

        try {
            const { activities = [] } = await fetchJson('/api/admin/activity');
            
            if (activities.length === 0) {
                container.innerHTML = '<div class="text-center text-muted p-3">No recent activity</div>';
                return;
            }

            container.innerHTML = activities.map(
                (activity) => `
                <div class="activity-item">
                    <div class="activity-icon">
                        <i class="${getActivityIcon(activity.action)}"></i>
                    </div>
                    <div class="activity-content">
                        <div class="activity-title">
                            <strong>${activity.user_name}</strong> 
                            ${activity.is_google_user ? '<i class="fab fa-google text-danger ms-1" title="Google User" style="font-size: 0.8em;"></i>' : ''}
                            ${activity.action}
                        </div>
                        <div class="activity-details text-muted small">
                            ${activity.details || ''}
                        </div>
                        <div class="activity-time">${timeAgo(activity.created_at)}</div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load activities', error);
            container.innerHTML = '<div class="text-center text-danger p-3">Failed to load activity</div>';
        }
    };

    const getActivityIcon = (action) => {
        const lower = action.toLowerCase();
        if (lower.includes('login')) return 'fas fa-sign-in-alt';
        if (lower.includes('register') || lower.includes('create user')) return 'fas fa-user-plus';
        if (lower.includes('delete')) return 'fas fa-trash';
        if (lower.includes('update') || lower.includes('edit')) return 'fas fa-edit';
        if (lower.includes('product')) return 'fas fa-box';
        if (lower.includes('order')) return 'fas fa-shopping-cart';
        return 'fas fa-info-circle';
    };

    const timeAgo = (dateString) => {
        const date = new Date(dateString);
        const seconds = Math.floor((new Date() - date) / 1000);
        
        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + " years ago";
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + " months ago";
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + " days ago";
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + " hours ago";
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + " minutes ago";
        return Math.floor(seconds) + " seconds ago";
    };

    const updateUptime = () => {
        const el = document.getElementById(SELECTORS.uptime);
        if (!el) {
            return;
        }
        const diff = Math.max(0, Math.floor((Date.now() - START_TIME) / 1000));
        const hours = Math.floor(diff / 3600);
        const minutes = Math.floor((diff % 3600) / 60);
        const seconds = diff % 60;
        el.textContent = `${hours}h ${minutes}m ${seconds}s`;
    };

    const init = () => {
        loadUserStats();
        loadProducts();
        loadCustomers();
        loadActivities();
        updateUptime();
        setInterval(updateUptime, 1000);
    };

    document.addEventListener('DOMContentLoaded', init);
})();
