/* Workflow Automation for Retail - Global JavaScript */

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    initializeTheme();
    setupSidebar();
    setupMobileSidebar();
    setupSubmenus();
    setupSidebarSearch();
    setupCollapsedClickToExpand();
    setupHeader();
    setupNotificationPanel();
    setupUserPanel();
    setupSidebarUserMenu();
    setupToastContainer();
    setupFormHandlers();
    setupDemoAccounts();
    setupNotifications();
});

/* ==============================
   SIDEBAR (collapse + persist)
   ============================== */

/**
 * Sync main-wrapper's margin-left with the sidebar's actual rendered width.
 * This is the most reliable way to make the page content shift when the
 * sidebar expands/collapses — it reads the real offsetWidth (not hardcoded
 * values) so it works regardless of which width the sidebar ends up at.
 *
 * On mobile (≤768px), the responsive.css rule with `!important` keeps
 * main-wrapper at margin-left: 0 (sidebar is off-canvas overlay). This
 * function bails early on mobile to avoid fighting that rule.
 */
function syncMainWrapperMargin() {
    const sidebar = document.getElementById('sidebar');
    const mainWrapper = document.getElementById('mainWrapper');
    if (!sidebar || !mainWrapper) return;

    // Mobile: let the responsive.css !important rule win
    if (window.innerWidth <= 768) return;

    // Desktop/tablet: match the sidebar's actual rendered width
    const width = sidebar.offsetWidth;
    mainWrapper.style.marginLeft = width + 'px';
}

/**
 * Wait for the sidebar's width transition to complete, then sync the
 * main-wrapper. This is critical because reading offsetWidth during the
 * transition returns the OLD width, which would set the wrong margin
 * (e.g. collapsing from 240→72 while reading 240 would leave the content
 * at 240px margin, which is the REVERSE of what we want).
 */
function syncMainWrapperAfterTransition() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) {
        syncMainWrapperMargin();
        return;
    }
    // Listen for the width transition to end
    const onEnd = (e) => {
        if (e.propertyName === 'width') {
            sidebar.removeEventListener('transitionend', onEnd);
            syncMainWrapperMargin();
        }
    };
    sidebar.addEventListener('transitionend', onEnd);
    // Fallback: if transitionend doesn't fire (e.g. transition removed),
    // sync after 450ms (slightly longer than the 400ms transition)
    setTimeout(() => {
        sidebar.removeEventListener('transitionend', onEnd);
        syncMainWrapperMargin();
    }, 450);
}

// Expose to window so the inline `toggleDesktopSidebar` handler in
// base.html can call the modern transition-aware sync. Inline scripts
// run before deferred scripts, so we can't reference the function
// directly — base.html does setTimeout(50) and falls back to inline
// marginLeft if this isn't ready yet.
window.syncMainWrapperAfterTransition = syncMainWrapperAfterTransition;

function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    // Default expanded on every page load. We deliberately do NOT restore
    // the collapsed state from localStorage — the user wants the sidebar
    // to be expanded by default so layout has no awkward empty space.
    // (The click handler in base.html still saves state to localStorage
    // for future reference, but we ignore it on load.)
    sidebar.classList.remove('collapsed');

    // Sync on init (in case restore added .collapsed) — transition may not
    // have started yet, so we can sync immediately
    syncMainWrapperMargin();

    // Sync on window resize (debounced) for viewport changes
    let resizeTimer = null;
    window.addEventListener('resize', () => {
        if (resizeTimer) clearTimeout(resizeTimer);
        resizeTimer = setTimeout(syncMainWrapperMargin, 100);
    });
}

/**
 * Expand the sidebar (programmatic, used by click-to-expand on collapsed).
 * Idempotent — safe to call when already expanded.
 */
function expandSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    if (sidebar.classList.contains('collapsed')) {
        sidebar.classList.remove('collapsed');
        localStorage.setItem('sidebar-collapsed', 'false');
        // Wait for sidebar width transition to complete, then sync margin
        syncMainWrapperAfterTransition();
    }
}

/**
 * When the sidebar is collapsed, intercept clicks on any nav item and just expand
 * the sidebar instead of navigating. This is the "click any icon to expand and
 * choose" pattern — two clicks to navigate when collapsed.
 *
 * For group items, the existing setupSubmenus click handler will run after our
 * capture-phase intercept and toggle the submenu open (since we let the event
 * bubble by NOT calling stopPropagation).
 */
function setupCollapsedClickToExpand() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    // Use capture phase so we run before the specific item's bubble-phase listeners
    sidebar.addEventListener('click', (e) => {
        if (!sidebar.classList.contains('collapsed')) return;

        // Only intercept nav items (skip toggle button, footer, search, etc.)
        const item = e.target.closest('.sidebar__item, .sidebar__submenu-item');
        if (!item) return;

        // Sidebar is collapsed: expand instead of navigate
        e.preventDefault();
        expandSidebar();
    }, true);
}

/* ==============================
   MOBILE SIDEBAR DRAWER
   ============================== */
function setupMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('mobileSidebarToggle');
    const overlay = document.getElementById("sidebarOverlay");
    if (!sidebar || !toggle) return;

    function open() {
        sidebar.classList.add('active', 'mobile-open');
        if (overlay) overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function close() {
        sidebar.classList.remove('active', 'mobile-open');
        if (overlay) overlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        if (sidebar.classList.contains('mobile-open')) {
            close();
        } else {
            open();
        }
    });

    if (overlay) {
        overlay.addEventListener('click', close);
    }

    // Close on ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('mobile-open')) {
            close();
        }
    });

    // Close on window resize to desktop
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (window.innerWidth > 1024) close();
        }, 200);
    });
}

/* ==============================
   SUBMENU TOGGLE (groups)
   ============================== */
function setupSubmenus() {
    // Each .sidebar__item--has-sub toggles its sibling .sidebar__submenu
    document.querySelectorAll('.sidebar__item--has-sub').forEach((btn) => {
        const subId = btn.dataset.sub;
        if (!subId) return;
        const sub = document.getElementById(subId);
        if (!sub) return;
        const group = btn.closest('.sidebar__group');

        // Restore open state from localStorage
        const openKey = `sidebar-group-${btn.closest('.sidebar__group')?.dataset.group}`;
        if (openKey && localStorage.getItem(openKey) === 'true') {
            group?.classList.add('open');
            btn.setAttribute('aria-expanded', 'true');
            group?.setAttribute('aria-expanded', 'true');
        }

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (group) {
                const wasOpen = group.classList.contains('open');

                // Accordion: close all other groups first
                document.querySelectorAll('.sidebar__group.open').forEach(otherGroup => {
                    if (otherGroup !== group) {
                        otherGroup.classList.remove('open');
                        const otherBtn = otherGroup.querySelector('.sidebar__item--has-sub');
                        const otherKey = `sidebar-group-${otherGroup.dataset.group}`;
                        if (otherBtn) {
                            otherBtn.setAttribute('aria-expanded', 'false');
                            otherGroup.setAttribute('aria-expanded', 'false');
                        }
                        if (otherKey) localStorage.setItem(otherKey, 'false');
                    }
                });

                // Toggle the clicked group
                const isOpen = !wasOpen;
                group.classList.toggle('open', isOpen);
                btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
                group.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
                if (openKey) localStorage.setItem(openKey, isOpen);
            }
        });
    });

    // Auto-open the group containing the current page
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar__submenu-item').forEach((item) => {
        if (item.getAttribute('href') === currentPath) {
            const group = item.closest('.sidebar__group');
            const btn = group?.querySelector('.sidebar__item--has-sub');
            if (group && btn) {
                group.classList.add('open');
                btn.setAttribute('aria-expanded', 'true');
                group.setAttribute('aria-expanded', 'true');
                item.classList.add('active');
            }
        }
    });
}

/* ==============================
   SIDEBAR SEARCH (⌘K palette)
   ============================== */
function setupSidebarSearch() {
    const input = document.getElementById('sidebarSearch');
    const nav = document.getElementById('sidebarNav');
    const status = document.getElementById('sidebarSearchStatus');
    const clearBtn = document.getElementById('sidebarSearchClear');
    if (!input || !nav) return;

    // Normalize Vietnamese text for diacritic-insensitive search
    const normalize = (s) => (s || '').toString()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, ''); // strip combining diacritics

    const applyFilter = (rawQuery) => {
        const query = normalize(rawQuery.trim());
        if (!query) {
            // Clear filter: remove all --hidden classes + searching state
            nav.classList.remove('searching');
            nav.querySelectorAll('.sidebar__item--hidden, .sidebar__submenu-item--hidden, .sidebar__group--hidden')
                .forEach(el => el.classList.remove('sidebar__item--hidden', 'sidebar__submenu-item--hidden', 'sidebar__group--hidden'));
            if (status) status.hidden = true;
            if (clearBtn) clearBtn.hidden = true;
            return;
        }

        nav.classList.add('searching');
        if (clearBtn) clearBtn.hidden = false;

        let visibleCount = 0;

        // Iterate top-level items + groups
        nav.querySelectorAll(':scope > .sidebar__item, :scope > .sidebar__group').forEach(node => {
            if (node.classList.contains('sidebar__group')) {
                // Check if any submenu item matches
                let groupMatch = false;
                const subItems = node.querySelectorAll('.sidebar__submenu-item');
                subItems.forEach(item => {
                    const text = normalize(item.dataset.searchText || item.textContent);
                    const match = text.includes(query);
                    item.classList.toggle('sidebar__submenu-item--hidden', !match);
                    if (match) {
                        groupMatch = true;
                        visibleCount++;
                    }
                });
                // Also check the parent button itself
                const parentBtn = node.querySelector('.sidebar__item--has-sub');
                const parentText = normalize(parentBtn?.dataset.searchText || parentBtn?.textContent);
                if (parentText.includes(query)) {
                    // Show all children of this group too
                    subItems.forEach(item => item.classList.remove('sidebar__submenu-item--hidden'));
                    groupMatch = true;
                }
                node.classList.toggle('sidebar__group--hidden', !groupMatch);
            } else {
                // Standalone top-level item (Dashboard, Settings)
                const text = normalize(node.dataset.searchText || node.textContent);
                const match = text.includes(query);
                node.classList.toggle('sidebar__item--hidden', !match);
                if (match) visibleCount++;
            }
        });

        if (status) status.hidden = visibleCount > 0;
    };

    // Live filter on input
    input.addEventListener('input', (e) => applyFilter(e.target.value));

    // Clear button
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            input.value = '';
            applyFilter('');
            input.focus();
        });
    }

    // ⌘K / Ctrl+K to focus (global shortcut)
    document.addEventListener('keydown', (e) => {
        const isShortcut = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k';
        if (isShortcut) {
            e.preventDefault();
            input.focus();
            input.select();
        }
        // Escape to clear
        if (e.key === 'Escape' && document.activeElement === input) {
            input.value = '';
            applyFilter('');
            input.blur();
        }
    });
}

/* ==============================
   HEADER (search + menu toggle)
   ============================== */
function setupHeader() {
    // Mobile menu toggle inside header (alias for sidebar toggle)
    const menuToggle = document.getElementById('menuToggle');
    const mobileToggle = document.getElementById('mobileSidebarToggle');
    if (menuToggle && mobileToggle) {
        menuToggle.addEventListener('click', () => mobileToggle.click());
    }

    // Header theme toggle was removed — theme is now controlled from /settings.
    // (See components/header.html and settings.html [data-theme-option] buttons.)

    // Header search: simple debounced
    const search = document.getElementById('headerSearch');
    if (search) {
        let timer;
        search.addEventListener('input', (e) => {
            clearTimeout(timer);
            timer = setTimeout(() => {
                const event = new CustomEvent('header-search', { detail: { query: e.target.value } });
                window.dispatchEvent(event);
            }, 300);
        });
    }
}

/* ==============================
   NOTIFICATION PANEL
   ============================== */
function setupNotificationPanel() {
    const btn = document.getElementById('notificationBtn');
    const panel = document.getElementById('notiPanel');
    if (!btn || !panel) return;

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        // Close user panel if open
        document.getElementById('userPanel')?.classList.remove('active');
        panel.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
        if (!panel.contains(e.target) && !btn.contains(e.target)) {
            panel.classList.remove('active');
        }
    });

    // Mark all read
    panel.querySelector('[data-action="mark-all-read"]')?.addEventListener('click', () => {
        panel.querySelectorAll('.noti-panel__item--unread').forEach((el) => {
            el.classList.remove('noti-panel__item--unread');
        });
        const count = document.getElementById('notificationCount');
        if (count) {
            count.textContent = '0';
            count.style.display = 'none';
        }
        const countText = document.getElementById('notiCountText');
        if (countText) countText.textContent = 'Đã đọc tất cả';
    });
}

/* ==============================
   USER PANEL
   ============================== */
function setupUserPanel() {
    const btn = document.getElementById("userAvatar");
    const panel = document.getElementById('userPanel');
    if (!btn || !panel) return;

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        // Close noti panel if open
        document.getElementById('notiPanel')?.classList.remove('active');
        panel.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
        if (!panel.contains(e.target) && !btn.contains(e.target)) {
            panel.classList.remove('active');
        }
    });
}

/* ==============================
   TOAST CONTAINER (auto-create)
   ============================== */
function setupToastContainer() {
    if (document.getElementById('toast-container')) return;
    const c = document.createElement('div');
    c.id = 'toast-container';
    c.className = 'toast-container';
    document.body.appendChild(c);
}

/* ==============================
   SIDEBAR USER MENU (toggle on click)
   ============================== */
function setupSidebarUserMenu() {
    const card = document.getElementById('sidebarUserCard');
    const menu = document.getElementById('sidebarUserMenu');
    const sidebar = document.getElementById('sidebar');
    if (!card || !menu) return;

    card.addEventListener('click', (e) => {
        e.stopPropagation();
        // Close header user panel if open
        document.getElementById('userPanel')?.classList.remove('active');

        // When sidebar is collapsed, expand first so the user can see the
        // user card (name + role) properly, then toggle the menu.
        if (sidebar && sidebar.classList.contains('collapsed')) {
            expandSidebar();
            menu.classList.add('open');
        } else {
            menu.classList.toggle('open');
        }
    });

    document.addEventListener('click', (e) => {
        if (!menu.contains(e.target) && !card.contains(e.target)) {
            menu.classList.remove('open');
        }
    });
}

function showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;

    const icons = {
        success: 'fa-solid fa-check',
        error: 'fa-solid fa-xmark',
        warning: 'fa-solid fa-triangle-exclamation',
        info: 'fa-solid fa-info',
    };

    toast.innerHTML = `
        <div class="toast__icon"><i class="${icons[type] || icons.info}"></i></div>
        <div class="toast__content">
            <p class="toast__message">${message}</p>
        </div>
        <button class="toast__close" aria-label="Đóng"><i class="fa-solid fa-xmark"></i></button>
    `;

    container.appendChild(toast);

    const dismiss = () => {
        toast.classList.add('toast--leaving');
        setTimeout(() => toast.remove(), 300);
    };

    toast.querySelector('.toast__close')?.addEventListener('click', dismiss);
    if (duration > 0) setTimeout(dismiss, duration);
}

// Expose to window for ad-hoc use
window.showToast = showToast;

function initializeTheme() {
    const html = document.documentElement;
    const toggles = document.querySelectorAll('[data-theme-toggle]');
    const selectControls = document.querySelectorAll('[data-theme-select]');
    const optionControls = document.querySelectorAll('[data-theme-option]');
    const panelToggle = document.querySelector('[data-theme-panel-toggle]');
    const panel = document.querySelector('[data-theme-panel]');
    const preferenceKey = 'theme-preference';
    const legacyKey = 'landing-theme';
    const systemPreference = window.matchMedia('(prefers-color-scheme: dark)');
    const preferenceOrder = ['system', 'dark', 'light'];
    const themeLabels = {
        system: 'System theme',
        dark: 'Dark mode',
        light: 'Light mode'
    };
    const themeIcons = {
        system: 'fa-desktop',
        dark: 'fa-moon',
        light: 'fa-sun'
    };

    const normalizePreference = (value) => preferenceOrder.includes(value) ? value : 'system';

    if (!localStorage.getItem(preferenceKey)) {
        const legacyPreference = localStorage.getItem(legacyKey);
        if (legacyPreference) {
            const migrated = normalizePreference(legacyPreference);
            localStorage.setItem(preferenceKey, migrated);
            localStorage.removeItem(legacyKey);
        }
    }

    let currentPreference = normalizePreference(localStorage.getItem(preferenceKey) || 'system');

    const getEffectiveTheme = (preference) => {
        if (preference === 'system') {
            return systemPreference.matches ? 'dark' : 'light';
        }
        return preference;
    };

    const updateToggleButton = (button, preference, appliedTheme) => {
        const icon = button.querySelector('i');
        const normalizedPreference = normalizePreference(preference);
        const currentIndex = Math.max(preferenceOrder.indexOf(normalizedPreference), 0);
        const nextPreference = preferenceOrder[(currentIndex + 1) % preferenceOrder.length];
        if (icon) {
            icon.className = `fas ${themeIcons[normalizedPreference]}`;
        }
        button.dataset.themePreference = normalizedPreference;
        button.dataset.themeApplied = appliedTheme;
        button.setAttribute('aria-label', `${themeLabels[normalizedPreference]} (click to switch to ${themeLabels[nextPreference]})`);
        button.title = `${themeLabels[normalizedPreference]} • Currently ${appliedTheme}\nClick to switch to ${themeLabels[nextPreference]}`;
    };

    const syncPreferenceControls = (preference) => {
        selectControls.forEach((select) => {
            if (select.value !== preference) {
                select.value = preference;
            }
        });

        optionControls.forEach((button) => {
            const optionValue = button.dataset.themeOption;
            if (!optionValue) {
                return;
            }
            const isActive = optionValue === preference;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        });
    };

    const applyTheme = (preference) => {
        const normalizedPreference = normalizePreference(preference);
        const effectiveTheme = getEffectiveTheme(normalizedPreference);
        html.setAttribute('data-theme', effectiveTheme);
        html.classList.toggle('theme-dark', effectiveTheme === 'dark');
        document.body.classList.toggle('dark-mode', effectiveTheme === 'dark');
        toggles.forEach((button) => updateToggleButton(button, normalizedPreference, effectiveTheme));
        syncPreferenceControls(normalizedPreference);
        // Table theme is handled CSS-only by banle_helpers.js (no JS call needed)
    };

    const setPreference = (nextPreference) => {
        const normalizedPreference = normalizePreference(nextPreference);
        currentPreference = normalizedPreference;
        localStorage.setItem(preferenceKey, normalizedPreference);
        applyTheme(normalizedPreference);
    };

    const cyclePreference = () => {
        const currentIndex = Math.max(preferenceOrder.indexOf(currentPreference), 0);
        const nextPreference = preferenceOrder[(currentIndex + 1) % preferenceOrder.length];
        setPreference(nextPreference);
    };

    let panelOpen = false;
    const openPanel = () => {
        if (!panel) {
            return;
        }
        panel.removeAttribute('hidden');
        panel.classList.add('is-open');
        panelToggle?.setAttribute('aria-expanded', 'true');
        panelOpen = true;
    };

    const closePanel = () => {
        if (!panel) {
            return;
        }
        panel.classList.remove('is-open');
        panel.setAttribute('hidden', '');
        panelToggle?.setAttribute('aria-expanded', 'false');
        panelOpen = false;
    };

    const togglePanel = () => {
        if (!panel) {
            return;
        }
        if (panelOpen) {
            closePanel();
        } else {
            openPanel();
        }
    };

    toggles.forEach((button) => {
        button.addEventListener('click', cyclePreference);
    });

    selectControls.forEach((select) => {
        select.addEventListener('change', (event) => {
            setPreference(event.target.value);
        });
    });

    optionControls.forEach((button) => {
        button.addEventListener('click', () => {
            const optionValue = button.dataset.themeOption;
            if (optionValue) {
                setPreference(optionValue);
                closePanel();
            }
        });
    });

    panelToggle?.addEventListener('click', (event) => {
        event.stopPropagation();
        togglePanel();
    });

    document.addEventListener('click', (event) => {
        if (!panelOpen) {
            return;
        }
        if (panel?.contains(event.target) || panelToggle?.contains(event.target)) {
            return;
        }
        closePanel();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closePanel();
        }
    });

    systemPreference.addEventListener('change', () => {
        if (currentPreference === 'system') {
            applyTheme('system');
        }
    });

    closePanel();
    applyTheme(currentPreference);
}

/* Table theme sync is handled by `banle_helpers.js` (CSS-only, see
   syncAllTablesTheme there). The previous JS-based sync here was removed
   because it used undefined CSS variables (--surface-100/200) and would
   always fall back to light colors, breaking tables in dark mode. */

/**
 * Form Handlers
 */
function setupFormHandlers() {
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleLogin();
        });
    }
    
    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleSignup();
        });
    }
}

/**
 * Login Handler
 */
function handleLogin() {
    const email = document.getElementById('email')?.value;
    const password = document.getElementById('password')?.value;
    
    if (!email || !password) {
        showNotification('Please fill in all fields', 'error');
        return;
    }
    
    if (!validateEmail(email)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }
    
    // Submit form
    const form = document.getElementById('loginForm');
    if (form) {
        form.submit();
    }
}

/**
 * Signup Handler
 */
function handleSignup() {
    const username = document.getElementById('username')?.value;
    const email = document.getElementById('email')?.value;
    const password = document.getElementById('password')?.value;
    const confirmPassword = document.getElementById('confirmPassword')?.value;
    
    if (!username || !email || !password || !confirmPassword) {
        showNotification('Please fill in all fields', 'error');
        return;
    }
    
    if (!validateEmail(email)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }
    
    if (password !== confirmPassword) {
        showNotification('Passwords do not match', 'error');
        return;
    }
    
    if (password.length < 8) {
        showNotification('Password must be at least 8 characters long', 'error');
        return;
    }
    
    // Submit form
    const form = document.getElementById('signupForm');
    if (form) {
        form.submit();
    }
}

/**
 * Demo Account Autofill
 */
function setupDemoAccounts() {
    const demoCards = document.querySelectorAll('.demo-card');
    
    demoCards.forEach(card => {
        card.addEventListener('click', function() {
            const email = this.querySelector('.demo-email').textContent;
            const password = this.querySelector('.demo-password').textContent;
            
            const emailInput = document.getElementById('email');
            const passwordInput = document.getElementById('password');
            
            if (emailInput) emailInput.value = email;
            if (passwordInput) passwordInput.value = password;
            
            showNotification(`Demo account loaded: ${email}`, 'info');
        });
    });
}

/**
 * Fill Demo Credentials
 */
function fillDemo(email, password) {
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    
    if (emailInput) emailInput.value = email;
    if (passwordInput) passwordInput.value = password;
}

/**
 * Email Validation
 */
function validateEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

/**
 * Password Strength Checker
 */
function checkPasswordStrength(password) {
    let strength = 'weak';
    let score = 0;
    
    if (password.length >= 8) score++;
    if (password.match(/[a-z]/) && password.match(/[A-Z]/)) score++;
    if (password.match(/[0-9]/)) score++;
    if (password.match(/[^a-zA-Z0-9]/)) score++;
    
    if (score >= 3) strength = 'strong';
    else if (score >= 2) strength = 'medium';
    
    return strength;
}

/**
 * Notification System
 */
function setupNotifications() {
    const flashNodes = document.querySelectorAll('[data-flash-message]');
    flashNodes.forEach(node => {
        const message = node.dataset.flashMessage;
        const category = node.dataset.flashCategory || 'info';
        const allowed = ['success', 'error', 'warning', 'info'];
        const normalizedType = allowed.includes(category) ? category : 'info';
        if (message) {
            showNotification(message, normalizedType);
        }
        node.remove();
    });
}

/**
 * Show Notification
 */
const NOTIFICATION_AUTO_DISMISS_MS = 2000;  // auto-dismiss notifications every 2 seconds

function showNotification(message, type = 'info') {
    let container = document.querySelector('.notification-container');

    if (!container) {
        container = document.createElement('div');
        container.className = 'notification-container';
        document.body.appendChild(container);
    }

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.setAttribute('role', 'status');
    notification.setAttribute('aria-live', 'polite');

    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-times-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };

    const iconWrapper = document.createElement('div');
    iconWrapper.className = 'notification-icon';
    const iconElement = document.createElement('i');
    iconElement.className = icons[type] || icons.info;
    iconElement.setAttribute('aria-hidden', 'true');
    iconWrapper.appendChild(iconElement);

    const messageElement = document.createElement('div');
    messageElement.className = 'notification-message';
    messageElement.textContent = message || '';

    const closeButton = document.createElement('button');
    closeButton.className = 'notification-close';
    closeButton.type = 'button';
    closeButton.setAttribute('aria-label', 'Dismiss notification');
    closeButton.textContent = '×';

    notification.appendChild(iconWrapper);
    notification.appendChild(messageElement);
    notification.appendChild(closeButton);

    container.appendChild(notification);

    requestAnimationFrame(() => {
        notification.classList.add('show');
    });

    const removeNotification = () => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 250);
    };

    closeButton.addEventListener('click', removeNotification);

    let dismissTimer = setTimeout(removeNotification, NOTIFICATION_AUTO_DISMISS_MS);
    notification.addEventListener('mouseenter', () => clearTimeout(dismissTimer));
    notification.addEventListener('mouseleave', () => {
        dismissTimer = setTimeout(removeNotification, NOTIFICATION_AUTO_DISMISS_MS);
    });

    return notification;
}

/**
 * Clear All Notifications
 */
function clearNotifications() {
    const container = document.querySelector('.notification-container');
    if (container) {
        container.innerHTML = '';
    }
}

/**
 * Toggle Password Visibility
 */
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
    }
}

/**
 * Form Input Event Listeners
 */
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('.form-input');
    
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.classList.remove('error');
        });
        
        input.addEventListener('blur', function() {
            if (this.id === 'email' && this.value) {
                if (!validateEmail(this.value)) {
                    this.classList.add('error');
                } else {
                    this.classList.remove('error');
                }
            }
        });
    });
});

/**
 * Smooth Scroll
 */
function smoothScroll(target) {
    const element = document.querySelector(target);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

/**
 * Session Management
 */
function logout() {
    clearNotifications();
    showNotification('Logging out...', 'info');
    
    setTimeout(() => {
        // Redirect to login
        window.location.href = '/';
    }, 1000);
}

/**
 * Error Handler
 */
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    // Show more detailed error in development/debug
    const errorMessage = event.error ? event.error.message : (event.message || 'Unknown error');
    showNotification('An unexpected error occurred: ' + errorMessage, 'error');
});

/**
 * Network Status
 */
window.addEventListener('online', function() {
    showNotification('Connection restored', 'success');
});

window.addEventListener('offline', function() {
    showNotification('Connection lost. Some features may be unavailable', 'warning');
});

/**
 * Sidebar item tooltip (collapsed state only).
 * The sidebar scrolls its menu internally and uses backdrop-filter, both of
 * which clip any CSS ::after tooltip that pops outside its own box. Instead,
 * render the tooltip as a single element appended to <body> and position it
 * with JS on hover, so it always escapes the sidebar's clipped/scrolled box.
 */
document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    const items = sidebar.querySelectorAll('[data-tooltip]');
    if (!items.length) return;

    const tip = document.createElement('div');
    tip.className = 'sidebar-tooltip';
    document.body.appendChild(tip);

    items.forEach(function (item) {
        item.addEventListener('mouseenter', function () {
            if (!sidebar.classList.contains('collapsed')) return;
            const label = item.getAttribute('data-tooltip');
            if (!label) return;
            const rect = item.getBoundingClientRect();
            tip.textContent = label;
            tip.style.top = (rect.top + rect.height / 2) + 'px';
            tip.style.left = (rect.right + 12) + 'px';
            tip.classList.add('is-visible');
        });
        item.addEventListener('mouseleave', function () {
            tip.classList.remove('is-visible');
        });
    });
});

