/* Workflow Automation for Retail - Global JavaScript */

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    initializeTheme();
    setupFormHandlers();
    setupDemoAccounts();
    setupNotifications();
});

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
        // Ensure table inline styles (if any) are rebuilt when theme changes
        if (typeof syncAllTablesTheme === 'function') {
            syncAllTablesTheme();
        }
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

/* Re-apply inline table backgrounds if any JS set them earlier and were based on CSS variables.
   This keeps tables consistent on dynamic theme changes. Prefer CSS variables but keep JS as a safe fallback.
*/
function syncAllTablesTheme() {
    const rootStyles = getComputedStyle(document.documentElement);
    const bg = rootStyles.getPropertyValue('--surface-100') || '#ffffff';
    const alt = rootStyles.getPropertyValue('--surface-200') || '#f8fafc';
    document.querySelectorAll('.table').forEach(table => {
        // Only adjust if there is an inline style or the computed style is white (bootstrap default)
        const computed = getComputedStyle(table).backgroundColor || '';
        // Note: computed is an rgb() string - we can't easily compare hex; however we still reapply
        // because CSS variables now control colors. If the site uses inline background=white we override with CSS var
        table.style.setProperty('background', bg.trim(), 'important');
        [...table.querySelectorAll('tbody tr')].forEach((row, idx) => {
            const color = (idx % 2 === 0) ? bg.trim() : alt.trim();
            row.style.setProperty('background', color, 'important');
        });
    });
}

// Observe DOM attribute changes to the html `data-theme` to refresh table inline styles
const _themeAttrObserver = new MutationObserver((mutations) => {
    const changed = mutations.some(m => m.attributeName === 'data-theme');
    if (changed) syncAllTablesTheme();
});
_themeAttrObserver.observe(document.documentElement, { attributes: true });

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
 * Mobile Sidebar Toggle
 */
document.addEventListener('DOMContentLoaded', function() {
    const mobileToggle = document.getElementById('mobile-sidebar-toggle');
    // Support both modern-sidebar (dashboard) and legacy sidebar (scenarios)
    const sidebar = document.querySelector('.modern-sidebar, .sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (mobileToggle && sidebar && overlay) {
        function toggleSidebar() {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
            
            // Update aria-expanded
            const isOpen = sidebar.classList.contains('open');
            mobileToggle.setAttribute('aria-expanded', isOpen);
        }

        mobileToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleSidebar();
        });

        overlay.addEventListener('click', function() {
            toggleSidebar();
        });

        // Close sidebar when clicking a link (optional, good for UX)
        const sidebarLinks = sidebar.querySelectorAll('a');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('open');
                    overlay.classList.remove('active');
                }
            });
        });
        
        // Handle resize
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768) {
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
            }
        });
    }
});
