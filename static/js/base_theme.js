(function attachCsrfToken() {
    const meta = document.querySelector("meta[name='csrf-token']");
    if (!meta) {
        return;
    }

    const token = meta.getAttribute('content');
    if (!token) {
        return;
    }

    const headerName = 'X-CSRFToken';
    window.csrfToken = token;

    if (window.axios) {
        window.axios.defaults.headers.common[headerName] = token;
    }

    const originalFetch = typeof window.fetch === 'function' ? window.fetch.bind(window) : null;

    const hasHeader = (headers, name) => {
        const lower = name.toLowerCase();
        if (headers instanceof Headers) {
            return headers.has(name) || headers.has(lower);
        }
        if (Array.isArray(headers)) {
            return headers.some(([key]) => (key || '').toLowerCase() === lower);
        }
        return Object.keys(headers || {}).some((key) => (key || '').toLowerCase() === lower);
    };

    const setHeader = (headers, name, value) => {
        if (headers instanceof Headers) {
            if (!headers.has(name)) {
                headers.set(name, value);
            }
            return headers;
        }
        if (Array.isArray(headers)) {
            if (!hasHeader(headers, name)) {
                headers.push([name, value]);
            }
            return headers;
        }
        const next = Object.assign({}, headers);
        if (!hasHeader(next, name)) {
            next[name] = value;
        }
        return next;
    };

    if (originalFetch && !window.__csrfFetchPatched) {
        window.__csrfFetchPatched = true;
        window.fetch = function (resource, config) {
            const nextConfig = Object.assign({}, config || {});
            nextConfig.headers = setHeader(nextConfig.headers || {}, headerName, token);
            // Ensure cookies are sent for same-origin requests
            nextConfig.credentials = nextConfig.credentials || 'same-origin';
            return originalFetch(resource, nextConfig);
        };
    }
})();

// Periodically check session status (keepalive/notify) to warn users
;(function sessionKeepalive() {
    if (typeof window.fetch !== 'function') return;
    
    // ĐỊNH NGHĨA ROUTE ĐĂNG NHẬP MỚI VÀ CÁC TRANG KHÔNG CẦN CHUYỂN HƯỚNG
    const LOGIN_URL = '/auth/login'; 
    // Thêm /auth/authorize vì đây là trang callback sau khi Google xác thực
    const UNAUTHENTICATED_PAGES = ['/auth/login', '/auth/signin', '/auth/authorize', '/']; 

    const check = async () => {
        try {
            const res = await fetch('/api/session', { credentials: 'same-origin' });
            if (!res.ok) {
                return;
            }
            const data = await res.json();
            
            // Nếu phiên đã hết hạn
            if (!data.authenticated) {
                const currentPath = window.location.pathname;
                
                // CHỈ CHUYỂN HƯỚNG NẾU NGƯỜI DÙNG KHÔNG Ở TRÊN CÁC TRANG CÔNG KHAI/ĐĂNG NHẬP
                if (!UNAUTHENTICATED_PAGES.some(p => currentPath === p || currentPath.startsWith(p))) {
                    try { 
                        if (typeof showNotification === 'function') {
                            showNotification('Session expired. Please log in again.', 'error'); 
                        }
                    } catch (e) {}
                    
                    // Chuyển hướng đến route OAuth mới sau 3 giây
                    setTimeout(() => { 
                        window.location.href = LOGIN_URL; 
                    }, 3000);
                }
            }
        } catch (e) {
            // ignore connection errors
        }
    };
    
    // Run immediately and schedule (every 2 minutes)
    check();
    setInterval(check, 120000); 
})();

// Add a global handler for unauthorized (401/403) responses so AJAX calls redirect to signin
;(function attachUnauthorizedHandler() {
    if (typeof window.fetch !== 'function' || window.__unauthorizedFetchPatched) return;
    window.__unauthorizedFetchPatched = true;
    
    // ĐỊNH NGHĨA ROUTE ĐĂNG NHẬP MỚI
    const LOGIN_URL = '/auth/login'; 

    const originalFetch = window.fetch.bind(window);
    window.fetch = function(resource, config) {
        return originalFetch(resource, config).then(res => {
            if (res && (res.status === 401 || res.status === 403)) {
                // Chỉ xử lý chuyển hướng nếu không phải là API Call to /api/session
                if (resource !== '/api/session') {
                    try {
                        if (typeof showNotification === 'function') {
                            showNotification('Session expired. Please log in again.', 'error');
                        }
                    } catch (e) {
                        // ignore
                    }
                    // Chuyển hướng đến route OAuth mới sau 3 giây
                    setTimeout(() => window.location.href = LOGIN_URL, 3000); 
                }
            }
            return res;
        });
    };
})();
