function fillDemo(email, password) {// Fun Work Hub - Professional Login JavaScript// Fun Work Hub - Professional Login JavaScript// Fun Work Hub - Professional Login JavaScript// ===== FUN WORK HUB - PROFESSIONAL LOGIN JAVASCRIPT =====// ===== FUN WORK HUB - PROFESSIONAL LOGIN JAVASCRIPT =====// ===== FUN WORK HUB - PROFESSIONAL LOGIN JAVASCRIPT =====

    document.getElementById('email').value = email;

    document.getElementById('password').value = password;

}
document.addEventListener('DOMContentLoaded', function() {

    console.log('🚀 Fun Work Hub Professional Login initialized!');

    // Initialize when DOM loads

    // Get form elements

    const emailInput = document.getElementById('email');document.addEventListener('DOMContentLoaded', function() {

    const passwordInput = document.getElementById('password');

    const loginForm = document.querySelector('.login-form');    console.log('🚀 Fun Work Hub Professional Login initialized!');document.addEventListener('DOMContentLoaded', function() {

    const loginBtn = document.querySelector('.login-btn');

        

    // Initialize features

    if (loginForm) {    // Initialize all features    console.log('🚀 Fun Work Hub Professional Login initialized!');

        initFormValidation();

        initAnimations();    initFormValidation();

        initAutoComplete();

    }    initAnimations();    // DOM Elements

});

    initAutoComplete();

// Form validation

function initFormValidation() {    initKeyboardShortcuts();    // Get form elements

    const emailInput = document.getElementById('email');

    const passwordInput = document.getElementById('password');    initAdvancedFeatures();

    const loginForm = document.querySelector('.login-form');

            const emailInput = document.getElementById('email');let emailInput, passwordInput, loginForm, loginBtn;

    if (!emailInput || !passwordInput || !loginForm) return;

        // Start entrance animations

    // Real-time validation

    emailInput.addEventListener('input', validateEmail);    setTimeout(startEntranceAnimations, 300);    const passwordInput = document.getElementById('password');

    passwordInput.addEventListener('input', validatePassword);

    });

    // Form submission

    loginForm.addEventListener('submit', handleFormSubmit);    const loginForm = document.querySelector('.login-form');// DOM Elements// DOM Elements

}

// DOM Elements (cached for performance)

function validateEmail() {

    const emailInput = document.getElementById('email');const elements = {    const loginBtn = document.querySelector('.login-btn');

    const email = emailInput.value.trim();

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;    get emailInput() { return document.getElementById('email'); },

    

    if (email === '') {    get passwordInput() { return document.getElementById('password'); },    // Initialize when DOM is loaded

        setFieldState(emailInput, 'neutral');

        return true;    get loginForm() { return document.querySelector('.login-form'); },

    } else if (!emailRegex.test(email)) {

        setFieldState(emailInput, 'error', 'Vui lòng nhập email hợp lệ');    get loginBtn() { return document.querySelector('.login-btn'); },    // Initialize features

        return false;

    } else {    get emailError() { return document.getElementById('email-error'); },

        setFieldState(emailInput, 'success');

        return true;    get passwordError() { return document.getElementById('password-error'); }    if (loginForm) {document.addEventListener('DOMContentLoaded', function() {let emailInput, passwordInput, loginForm, loginBtn;let emailInput, passwordInput, loginForm, loginBtn;

    }

}};



function validatePassword() {        initFormValidation();

    const passwordInput = document.getElementById('password');

    const password = passwordInput.value;// Form Validation with Advanced Features

    

    if (password === '') {function initFormValidation() {        initAnimations();    console.log('🚀 Fun Work Hub PRO Login initialized!');

        setFieldState(passwordInput, 'neutral');

        return true;    const { emailInput, passwordInput, loginForm } = elements;

    } else if (password.length < 6) {

        setFieldState(passwordInput, 'error', 'Mật khẩu phải có ít nhất 6 ký tự');            initAutoComplete();

        return false;

    } else {    if (!loginForm) return;

        setFieldState(passwordInput, 'success');

        return true;        }    

    }

}    // Real-time validation



function setFieldState(input, state, message = '') {    emailInput?.addEventListener('input', debounce(validateEmail, 300));});

    const wrapper = input.closest('.form-group');

    if (!wrapper) return;    passwordInput?.addEventListener('input', debounce(validatePassword, 300));

    

    // Remove all state classes    passwordInput?.addEventListener('input', updatePasswordStrength);    // Get form elements

    input.classList.remove('error', 'success', 'warning', 'info');

        

    // Add new state

    if (state !== 'neutral') {    // Form submission// Form validation

        input.classList.add(state);

    }    loginForm.addEventListener('submit', handleFormSubmit);

    

    // Handle error message    function initFormValidation() {    emailInput = document.getElementById('email');// Initialize when DOM is loaded// Initialize when DOM is loaded

    let errorElement = wrapper.querySelector('.error-message');

    if (!errorElement && message) {    // Add floating labels effect

        errorElement = document.createElement('div');

        errorElement.className = 'error-message';    addFloatingLabels();    const form = document.querySelector('.login-form');

        wrapper.appendChild(errorElement);

    }}

    

    if (errorElement) {    const emailInput = document.getElementById('email');    passwordInput = document.getElementById('password');

        if (message) {

            errorElement.textContent = message;function validateEmail() {

            errorElement.classList.add('show');

        } else {    const { emailInput, emailError } = elements;    const passwordInput = document.getElementById('password');

            errorElement.classList.remove('show');

        }    const email = emailInput.value.trim();

    }

}    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;        loginForm = document.querySelector('.login-form');document.addEventListener('DOMContentLoaded', function() {document.addEventListener('DOMContentLoaded', function() {



function handleFormSubmit(e) {    

    e.preventDefault();

        if (email === '') {    if (emailInput) emailInput.addEventListener('input', validateEmail);

    const emailValid = validateEmail();

    const passwordValid = validatePassword();        showFieldState(emailInput, 'neutral');

    const emailInput = document.getElementById('email');

    const passwordInput = document.getElementById('password');        return true; // Allow empty for now    if (passwordInput) passwordInput.addEventListener('input', validatePassword);    loginBtn = document.querySelector('.login-btn');

    

    if (!emailValid || !passwordValid) {    } else if (!emailRegex.test(email)) {

        shakeForm();

        showNotification('Vui lòng kiểm tra lại thông tin đăng nhập', 'error');        showFieldState(emailInput, 'error', 'Vui lòng nhập email hợp lệ');    

        return;

    }        return false;

    

    if (!emailInput.value || !passwordInput.value) {    } else {    if (form) {        console.log('🚀 Fun Work Hub PRO Login initialized!');    console.log('🚀 Fun Work Hub PRO Login initialized!');

        shakeForm();

        showNotification('Vui lòng điền đầy đủ thông tin', 'warning');        showFieldState(emailInput, 'success');

        return;

    }        return true;        form.addEventListener('submit', function(e) {

    

    // Show loading state    }

    showLoadingState();

    }            e.preventDefault();    // Initialize all features

    // Submit form after delay

    setTimeout(() => {

        document.querySelector('.login-form').submit();

    }, 1500);function validatePassword() {            

}

    const { passwordInput } = elements;

function showLoadingState() {

    const loginBtn = document.querySelector('.login-btn');    const password = passwordInput.value;            if (validateEmail() && validatePassword()) {    initFormValidation();        

    if (loginBtn) {

        loginBtn.classList.add('loading');    

        loginBtn.disabled = true;

        loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang đăng nhập...';    if (password === '') {                showLoadingState();

    }

}        showFieldState(passwordInput, 'neutral');



function shakeForm() {        return true; // Allow empty for now                setTimeout(() => {    initSmoothAnimations();

    const loginForm = document.querySelector('.login-form');

    if (loginForm) {    } else if (password.length < 6) {

        loginForm.style.animation = 'shake 0.5s ease-in-out';

        setTimeout(() => {        showFieldState(passwordInput, 'warning', 'Mật khẩu nên có ít nhất 6 ký tự');                    form.submit();

            loginForm.style.animation = '';

        }, 500);        return false;

    }

}    } else if (password.length >= 8) {                }, 1500);    initInteractions();    // Get form elements    // Get form elements



// Animations        showFieldState(passwordInput, 'success');

function initAnimations() {

    // Entrance animations        return true;            } else {

    setTimeout(startEntranceAnimations, 300);

        } else {

    // Hover effects

    document.querySelectorAll('.demo-card, .social-btn, .feature-item').forEach(element => {        showFieldState(passwordInput, 'info', 'Mật khẩu tốt!');                shakeForm();    initAutoComplete();

        element.addEventListener('mouseenter', function() {

            this.style.transform = 'translateY(-5px) scale(1.02)';        return true;

            this.style.transition = 'all 0.3s ease';

        });    }            }

        

        element.addEventListener('mouseleave', function() {}

            this.style.transform = 'translateY(0) scale(1)';

        });        });        emailInput = document.getElementById('email');    emailInput = document.getElementById('email');

    });

    function showFieldState(input, state, message = '') {

    // Input focus effects

    document.querySelectorAll('.form-input').forEach(input => {    const wrapper = input.closest('.form-group');    }

        input.addEventListener('focus', function() {

            const group = this.closest('.form-group');    const errorElement = wrapper.querySelector('.error-message');

            if (group) {

                group.classList.add('focused');    }    // Add entrance animations

            }

        });    // Remove all state classes

        

        input.addEventListener('blur', function() {    input.classList.remove('error', 'success', 'warning', 'info');

            const group = this.closest('.form-group');

            if (group && !this.value) {    

                group.classList.remove('focused');

            }    // Add new statefunction validateEmail() {    animateOnLoad();    passwordInput = document.getElementById('password');    passwordInput = document.getElementById('password');

        });

    });    if (state !== 'neutral') {

}

        input.classList.add(state);    const emailInput = document.getElementById('email');

function startEntranceAnimations() {

    // Animate panels    }

    const panels = document.querySelectorAll('.branding-panel, .login-panel');

    panels.forEach((panel, index) => {        const email = emailInput.value.trim();});

        panel.style.opacity = '0';

        panel.style.transform = index === 0 ? 'translateX(-50px)' : 'translateX(50px)';    // Show/hide message

        

        setTimeout(() => {    if (errorElement) {    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            panel.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';

            panel.style.opacity = '1';        if (message) {

            panel.style.transform = 'translateX(0)';

        }, index * 200);            errorElement.textContent = message;    const errorElement = document.getElementById('email-error');    loginForm = document.querySelector('.login-form');    loginForm = document.querySelector('.login-form');

    });

                errorElement.className = `error-message ${state} show`;

    // Animate form elements

    const formElements = document.querySelectorAll('.form-group, .social-login, .demo-accounts');        } else {    

    formElements.forEach((element, index) => {

        element.style.opacity = '0';            errorElement.classList.remove('show');

        element.style.transform = 'translateY(30px)';

                }    if (email === '') {// ===== FORM VALIDATION =====

        setTimeout(() => {

            element.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';    }

            element.style.opacity = '1';

            element.style.transform = 'translateY(0)';}        showFieldError(emailInput, errorElement, '');

        }, 800 + index * 150);

    });

}

// Password Strength Indicator        return false;function initFormValidation() {    loginBtn = document.querySelector('.login-btn');    loginBtn = document.querySelector('.login-btn');

// Auto-complete

function initAutoComplete() {function updatePasswordStrength() {

    const emailInput = document.getElementById('email');

    if (!emailInput) return;    const { passwordInput } = elements;    } else if (!emailRegex.test(email)) {

    

    // Load saved email    const password = passwordInput.value;

    const savedEmail = localStorage.getItem('fun_work_hub_email');

    if (savedEmail) {    const wrapper = passwordInput.closest('.form-group');        showFieldError(emailInput, errorElement, 'Vui lòng nhập email hợp lệ');    if (!loginForm) return;

        emailInput.value = savedEmail;

        const group = emailInput.closest('.form-group');    

        if (group) {

            group.classList.add('focused');    let strengthElement = wrapper.querySelector('.password-strength');        return false;

        }

    }    if (!strengthElement) {

    

    // Save email on change        strengthElement = document.createElement('div');    } else {            

    emailInput.addEventListener('change', function() {

        if (this.value && validateEmail()) {        strengthElement.className = 'password-strength';

            localStorage.setItem('fun_work_hub_email', this.value);

        }        strengthElement.innerHTML = `        showFieldSuccess(emailInput, errorElement);

    });

}            <div class="strength-bars">



// Demo account functions                <div class="strength-bar"></div>        return true;    // Real-time validation

function fillDemoAccount(email, password) {

    const emailInput = document.getElementById('email');                <div class="strength-bar"></div>

    const passwordInput = document.getElementById('password');

    const loginBtn = document.querySelector('.login-btn');                <div class="strength-bar"></div>    }

    

    if (emailInput && passwordInput) {                <div class="strength-bar"></div>

        // Animate filling

        emailInput.style.transform = 'scale(1.05)';            </div>}    if (emailInput) emailInput.addEventListener('input', validateEmail);    // Initialize all features    // Initialize all features

        passwordInput.style.transform = 'scale(1.05)';

                    <span class="strength-text">Độ mạnh mật khẩu</span>

        setTimeout(() => {

            emailInput.value = email;        `;

            emailInput.style.transform = 'scale(1)';

            emailInput.closest('.form-group').classList.add('focused');        wrapper.appendChild(strengthElement);

            

            setTimeout(() => {    }function validatePassword() {    if (passwordInput) passwordInput.addEventListener('input', validatePassword);

                passwordInput.value = password;

                passwordInput.style.transform = 'scale(1)';    

                passwordInput.closest('.form-group').classList.add('focused');

                    const strength = calculatePasswordStrength(password);    const passwordInput = document.getElementById('password');

                // Validate fields

                validateEmail();    const bars = strengthElement.querySelectorAll('.strength-bar');

                validatePassword();

                    const text = strengthElement.querySelector('.strength-text');    const password = passwordInput.value;        initFormValidation();    initFormValidation();

                // Focus login button

                if (loginBtn) {    

                    loginBtn.focus();

                    loginBtn.style.transform = 'scale(1.05)';    // Reset bars    const errorElement = document.getElementById('password-error');

                    setTimeout(() => {

                        loginBtn.style.transform = 'scale(1)';    bars.forEach(bar => bar.className = 'strength-bar');

                    }, 200);

                }            // Form submission

            }, 300);

        }, 200);    // Fill bars based on strength

        

        showNotification('Đã điền thông tin demo! Click "Đăng nhập" để tiếp tục.', 'success');    for (let i = 0; i < strength.level; i++) {    if (password === '') {

    }

}        bars[i].classList.add(strength.class);



// Password toggle    }        showFieldError(passwordInput, errorElement, '');    loginForm.addEventListener('submit', handleFormSubmit);    initSmoothAnimations();    initSmoothAnimations();

function togglePassword() {

    const passwordInput = document.getElementById('password');    

    const eyeIcon = document.getElementById('password-eye');

        text.textContent = strength.text;        return false;

    if (passwordInput && eyeIcon) {

        if (passwordInput.type === 'password') {    strengthElement.style.opacity = password.length > 0 ? '1' : '0';

            passwordInput.type = 'text';

            eyeIcon.classList.remove('fa-eye');}    } else if (password.length < 6) {}

            eyeIcon.classList.add('fa-eye-slash');

        } else {

            passwordInput.type = 'password';

            eyeIcon.classList.remove('fa-eye-slash');function calculatePasswordStrength(password) {        showFieldError(passwordInput, errorElement, 'Mật khẩu phải có ít nhất 6 ký tự');

            eyeIcon.classList.add('fa-eye');

        }    if (password.length === 0) return { level: 0, class: '', text: 'Độ mạnh mật khẩu' };

        

        // Animate icon    if (password.length < 6) return { level: 1, class: 'weak', text: 'Yếu' };        return false;    initInteractions();    initInteractions();

        eyeIcon.style.transform = 'scale(1.2)';

        setTimeout(() => {    

            eyeIcon.style.transform = 'scale(1)';

        }, 150);    let score = 0;    } else {

    }

}    if (password.length >= 8) score++;



// Social login handlers    if (/[a-z]/.test(password)) score++;        showFieldSuccess(passwordInput, errorElement);function validateEmail() {

document.addEventListener('DOMContentLoaded', function() {

    // Social buttons    if (/[A-Z]/.test(password)) score++;

    document.querySelectorAll('.social-btn').forEach(btn => {

        btn.addEventListener('click', function() {    if (/[0-9]/.test(password)) score++;        return true;

            const platform = this.classList.contains('google-btn') ? 'Google' : 'GitHub';

            showNotification(`Đăng nhập với ${platform} đang được phát triển!`, 'info');    if (/[^A-Za-z0-9]/.test(password)) score++;

        });

    });        }    const email = emailInput.value.trim();    initAutoComplete();    initAutoComplete();

    

    // Forgot password    if (score <= 2) return { level: 2, class: 'fair', text: 'Trung bình' };

    const forgotLink = document.querySelector('.forgot-password');

    if (forgotLink) {    if (score <= 3) return { level: 3, class: 'good', text: 'Tốt' };}

        forgotLink.addEventListener('click', function(e) {

            e.preventDefault();    return { level: 4, class: 'strong', text: 'Mạnh' };

            showNotification('Tính năng quên mật khẩu đang được phát triển!', 'info');

        });}    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    }

    

    // Signup link

    const signupLink = document.querySelector('.signup-link');// Form Submission with Loading Statesfunction showFieldError(input, errorElement, message) {

    if (signupLink) {

        signupLink.addEventListener('click', function(e) {function handleFormSubmit(e) {

            e.preventDefault();

            showNotification('Tính năng đăng ký đang được phát triển!', 'info');    e.preventDefault();    input.classList.add('error');    const errorElement = document.getElementById('email-error');        

        });

    }    

});

    const emailValid = validateEmail();    input.classList.remove('success');

// Notifications

function showNotification(message, type = 'info', duration = 5000) {    const passwordValid = validatePassword();

    const container = getNotificationContainer();

                

    const notification = document.createElement('div');

    notification.className = `notification notification-${type}`;    if (!emailValid || !passwordValid) {

    notification.innerHTML = `

        <div class="notification-content">        shakeForm();    if (message && errorElement) {

            <i class="notification-icon fas ${getNotificationIcon(type)}"></i>

            <span class="notification-message">${message}</span>        showNotification('Vui lòng kiểm tra lại thông tin đăng nhập', 'error');

            <button class="notification-close" onclick="this.closest('.notification').remove()">

                <i class="fas fa-times"></i>        return;        errorElement.textContent = message;    if (email === '') {    // Add entrance animations    // Add entrance animations

            </button>

        </div>    }

    `;

                errorElement.classList.add('show');

    container.appendChild(notification);

        if (elements.emailInput.value === '' || elements.passwordInput.value === '') {

    // Animate in

    setTimeout(() => {        shakeForm();    }        showFieldError(emailInput, errorElement, '');

        notification.classList.add('show');

    }, 10);        showNotification('Vui lòng điền đầy đủ thông tin', 'warning');

    

    // Auto remove        return;}

    if (duration > 0) {

        setTimeout(() => {    }

            notification.classList.add('hide');

            setTimeout(() => {            return false;    animateOnLoad();    animateOnLoad();

                if (notification.parentNode) {

                    notification.remove();    // Show loading state

                }

            }, 300);    showLoadingState();function showFieldSuccess(input, errorElement) {

        }, duration);

    }    

}

    // Simulate API call with realistic delay    input.classList.remove('error');    } else if (!emailRegex.test(email)) {

function getNotificationContainer() {

    let container = document.querySelector('.notification-container');    setTimeout(() => {

    if (!container) {

        container = document.createElement('div');        elements.loginForm.submit();    input.classList.add('success');

        container.className = 'notification-container';

        container.style.cssText = `    }, 1500);

            position: fixed;

            top: 20px;}            showFieldError(emailInput, errorElement, 'Vui lòng nhập email hợp lệ');});});

            right: 20px;

            z-index: 10000;

            display: flex;

            flex-direction: column;function showLoadingState() {    if (errorElement) {

            gap: 10px;

        `;    const { loginBtn } = elements;

        document.body.appendChild(container);

    }            errorElement.classList.remove('show');        return false;

    return container;

}    loginBtn.classList.add('loading');



function getNotificationIcon(type) {    loginBtn.disabled = true;    }

    const icons = {

        success: 'fa-check-circle',    

        error: 'fa-exclamation-circle',

        warning: 'fa-exclamation-triangle',    // Create loading overlay}    } else {

        info: 'fa-info-circle'

    };    const overlay = document.createElement('div');

    return icons[type] || icons.info;

}    overlay.className = 'loading-overlay';



// Keyboard shortcuts    overlay.innerHTML = `

document.addEventListener('keydown', function(e) {

    // Enter on demo cards        <div class="loading-content">function showLoadingState() {        showFieldSuccess(emailInput, errorElement);

    if (e.key === 'Enter' && e.target.classList.contains('demo-card')) {

        e.target.click();            <div class="loading-spinner"></div>

    }

                <p>Đang đăng nhập...</p>    const loginBtn = document.querySelector('.login-btn');

    // Escape to close notifications

    if (e.key === 'Escape') {        </div>

        document.querySelectorAll('.notification').forEach(notif => notif.remove());

    }    `;    if (loginBtn) {        return true;// ===== FORM VALIDATION =====// ===== FORM VALIDATION =====

    

    // Ctrl/Cmd + Enter to submit    document.body.appendChild(overlay);

    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {

        const loginForm = document.querySelector('.login-form');            loginBtn.classList.add('loading');

        if (loginForm) {

            loginForm.dispatchEvent(new Event('submit'));    setTimeout(() => overlay.classList.add('show'), 10);

        }

    }}        loginBtn.disabled = true;    }

});



// Easter egg

let logoClickCount = 0;// Advanced Animations    }

document.addEventListener('DOMContentLoaded', function() {

    const logoIcon = document.querySelector('.logo-icon');function initAnimations() {

    if (logoIcon) {

        logoIcon.addEventListener('click', function() {    // Smooth focus animations}}function initFormValidation() {function initFormValidation() {

            logoClickCount++;

            if (logoClickCount === 5) {    document.querySelectorAll('.form-input').forEach(input => {

                this.style.animation = 'pulse 0.5s ease-in-out 3';

                showNotification('🎉 Bạn đã tìm ra easter egg! Chúc mừng!', 'success');        input.addEventListener('focus', function() {

                

                // Create confetti            this.closest('.form-group').classList.add('focused');

                for (let i = 0; i < 30; i++) {

                    createConfetti();        });function shakeForm() {

                }

                        

                logoClickCount = 0;

            }        input.addEventListener('blur', function() {    const form = document.querySelector('.login-form');

        });

    }            if (!this.value) {

});

                this.closest('.form-group').classList.remove('focused');    if (form) {function validatePassword() {    if (!loginForm) return;    if (!loginForm) return;

function createConfetti() {

    const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#feca57', '#ff9ff3'];            }

    const confetti = document.createElement('div');

    confetti.style.cssText = `        });        form.style.animation = 'shake 0.5s ease-in-out';

        position: fixed;

        width: 10px;    });

        height: 10px;

        background: ${colors[Math.floor(Math.random() * colors.length)]};            setTimeout(() => {    const password = passwordInput.value;

        left: ${Math.random() * window.innerWidth}px;

        top: -10px;    // Hover animations for interactive elements

        z-index: 10000;

        pointer-events: none;    document.querySelectorAll('.demo-card, .social-btn, .feature-item').forEach(element => {            form.style.animation = '';

        animation: confetti-fall 3s linear forwards;

    `;        element.addEventListener('mouseenter', function() {

    

    document.body.appendChild(confetti);            this.style.transform = 'translateY(-5px) scale(1.02)';        }, 500);    const errorElement = document.getElementById('password-error');        

    setTimeout(() => confetti.remove(), 3000);

}        });



// Add CSS for animations and effects            }

const style = document.createElement('style');

style.textContent = `        element.addEventListener('mouseleave', function() {

    @keyframes shake {

        0%, 100% { transform: translateX(0); }            this.style.transform = 'translateY(0) scale(1)';}    

        25% { transform: translateX(-10px); }

        75% { transform: translateX(10px); }        });

    }

        });

    @keyframes confetti-fall {

        to {}

            transform: translateY(100vh) rotate(360deg);

            opacity: 0;// Demo account functionality    if (password === '') {    // Real-time validation    // Real-time validation

        }

    }function startEntranceAnimations() {

    

    @keyframes pulse {    // Animate panelsfunction fillDemoAccount(email, password) {

        0%, 100% { transform: scale(1); }

        50% { transform: scale(1.1); }    const panels = document.querySelectorAll('.branding-panel, .login-panel');

    }

        panels.forEach((panel, index) => {    const emailInput = document.getElementById('email');        showFieldError(passwordInput, errorElement, '');

    .form-input.success {

        border-color: var(--success) !important;        panel.style.opacity = '0';

        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1) !important;

    }        panel.style.transform = index === 0 ? 'translateX(-50px)' : 'translateX(50px)';    const passwordInput = document.getElementById('password');

    

    .form-input.error {        

        border-color: var(--error) !important;

        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;        setTimeout(() => {            return false;    emailInput?.addEventListener('input', validateEmail);    emailInput?.addEventListener('input', validateEmail);

    }

                panel.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';

    .error-message {

        color: var(--error);            panel.style.opacity = '1';    if (emailInput && passwordInput) {

        font-size: 0.875rem;

        margin-top: 0.5rem;            panel.style.transform = 'translateX(0)';

        opacity: 0;

        transform: translateY(-10px);        }, index * 200);        emailInput.value = email;    } else if (password.length < 6) {

        transition: all 0.3s ease;

    }    });

    

    .error-message.show {            passwordInput.value = password;

        opacity: 1;

        transform: translateY(0);    // Animate form elements with stagger

    }

        const formElements = document.querySelectorAll('.form-group, .social-login, .demo-accounts');                showFieldError(passwordInput, errorElement, 'Mật khẩu phải có ít nhất 6 ký tự');    passwordInput?.addEventListener('input', validatePassword);    passwordInput?.addEventListener('input', validatePassword);

    .notification {

        background: white;    formElements.forEach((element, index) => {

        border-radius: 12px;

        box-shadow: 0 10px 25px rgba(0,0,0,0.1);        element.style.opacity = '0';        // Validate fields

        border-left: 4px solid var(--info);

        max-width: 400px;        element.style.transform = 'translateY(30px)';

        transform: translateX(100%);

        opacity: 0;                validateEmail();        return false;

        transition: all 0.3s ease;

    }        setTimeout(() => {

    

    .notification.show {            element.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';        validatePassword();

        transform: translateX(0);

        opacity: 1;            element.style.opacity = '1';

    }

                element.style.transform = 'translateY(0)';            } else {        

    .notification.hide {

        transform: translateX(100%);        }, 800 + index * 150);

        opacity: 0;

    }    });        // Show success message

    

    .notification-success { border-left-color: var(--success); }    

    .notification-error { border-left-color: var(--error); }

    .notification-warning { border-left-color: #f59e0b; }    // Animate features with delay        showMessage('Đã điền thông tin demo! Click "Đăng nhập" để tiếp tục.', 'success');        showFieldSuccess(passwordInput, errorElement);

    .notification-info { border-left-color: var(--info); }

        const features = document.querySelectorAll('.feature-item');

    .notification-content {

        display: flex;    features.forEach((feature, index) => {        

        align-items: center;

        gap: 12px;        feature.style.opacity = '0';

        padding: 16px;

    }        feature.style.transform = 'translateY(30px)';        // Focus login button        return true;    // Form submission    // Form submission

    

    .notification-icon {        

        font-size: 1.2rem;

    }        setTimeout(() => {        const loginBtn = document.querySelector('.login-btn');

    

    .notification-success .notification-icon { color: var(--success); }            feature.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';

    .notification-error .notification-icon { color: var(--error); }

    .notification-warning .notification-icon { color: #f59e0b; }            feature.style.opacity = '1';        if (loginBtn) {    }

    .notification-info .notification-icon { color: var(--info); }

                feature.style.transform = 'translateY(0)';

    .notification-message {

        flex: 1;        }, 1200 + index * 100);            loginBtn.focus();

        font-size: 0.9rem;

        color: var(--gray-700);    });

    }

    }        }}    loginForm.addEventListener('submit', handleFormSubmit);    loginForm.addEventListener('submit', handleFormSubmit);

    .notification-close {

        background: none;

        border: none;

        color: var(--gray-400);function shakeForm() {    }

        cursor: pointer;

        padding: 4px;    const { loginForm } = elements;

        border-radius: 4px;

        transition: color 0.3s ease;    loginForm.style.animation = 'shake 0.5s ease-in-out';}

    }

        setTimeout(() => {

    .notification-close:hover {

        color: var(--gray-600);        loginForm.style.animation = '';

    }

        }, 500);

    .form-group.focused .form-label {

        transform: translateY(-20px) scale(0.85);}// Password togglefunction showFieldError(input, errorElement, message) {}}

        color: var(--primary);

    }

    

    .login-btn.loading {// Auto-complete and Local Storagefunction togglePassword() {

        background: var(--gray-400) !important;

        cursor: not-allowed;function initAutoComplete() {

    }

`;    const { emailInput } = elements;    const passwordInput = document.getElementById('password');    input.classList.add('error');

document.head.appendChild(style);

    

console.log('🎯 Fun Work Hub Professional Login ready!');

console.log('Features: Form validation, Animations, Auto-complete, Keyboard shortcuts, Easter eggs');    if (!emailInput) return;    const eyeIcon = document.getElementById('password-eye');

    

    // Load saved email        input.classList.remove('success');

    const savedEmail = localStorage.getItem('fun_work_hub_email');

    if (savedEmail) {    if (passwordInput && eyeIcon) {

        emailInput.value = savedEmail;

        emailInput.closest('.form-group').classList.add('focused');        if (passwordInput.type === 'password') {    

    }

                passwordInput.type = 'text';

    // Save email on change

    emailInput.addEventListener('change', function() {            eyeIcon.classList.remove('fa-eye');    if (message && errorElement) {function validateEmail() {function validateEmail() {

        if (this.value && validateEmail()) {

            localStorage.setItem('fun_work_hub_email', this.value);            eyeIcon.classList.add('fa-eye-slash');

        }

    });        } else {        errorElement.textContent = message;

}

            passwordInput.type = 'password';

// Demo Account Functions

function fillDemoAccount(email, password) {            eyeIcon.classList.remove('fa-eye-slash');        errorElement.classList.add('show');    const email = emailInput.value.trim();    const email = emailInput.value.trim();

    const { emailInput, passwordInput, loginBtn } = elements;

                eyeIcon.classList.add('fa-eye');

    // Animate the filling process

    const fillSequence = async () => {        }    }

        // Focus and fill email

        emailInput.focus();    }

        await animateTyping(emailInput, email);

        emailInput.closest('.form-group').classList.add('focused');}}    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        

        // Small delay

        await delay(300);

        // Auto complete

        // Focus and fill password

        passwordInput.focus();function initAutoComplete() {

        await animateTyping(passwordInput, password);

        passwordInput.closest('.form-group').classList.add('focused');    const emailInput = document.getElementById('email');function showFieldSuccess(input, errorElement) {    const errorElement = document.getElementById('email-error');    const errorElement = document.getElementById('email-error');

        

        // Validate both fields    

        validateEmail();

        validatePassword();    if (emailInput) {    input.classList.remove('error');

        

        // Focus login button with animation        // Load saved email

        loginBtn.focus();

        loginBtn.style.transform = 'scale(1.05)';        const savedEmail = localStorage.getItem('fun_work_hub_email');    input.classList.add('success');        

        setTimeout(() => {

            loginBtn.style.transform = 'scale(1)';        if (savedEmail) {

        }, 200);

    };            emailInput.value = savedEmail;    

    

    fillSequence();            validateEmail();

    showNotification('Đã điền thông tin demo! Click "Đăng nhập" để tiếp tục.', 'success');

}        }    if (errorElement) {    if (email === '') {    if (email === '') {



// Password Toggle        

function togglePassword() {

    const passwordInput = document.getElementById('password');        // Save email on change        errorElement.classList.remove('show');

    const eyeIcon = document.getElementById('password-eye');

            emailInput.addEventListener('change', function() {

    if (passwordInput.type === 'password') {

        passwordInput.type = 'text';            if (this.value && validateEmail()) {    }        showFieldError(emailInput, errorElement, '');        showFieldError(emailInput, errorElement, '');

        eyeIcon.classList.remove('fa-eye');

        eyeIcon.classList.add('fa-eye-slash');                localStorage.setItem('fun_work_hub_email', this.value);

    } else {

        passwordInput.type = 'password';            }}

        eyeIcon.classList.remove('fa-eye-slash');

        eyeIcon.classList.add('fa-eye');        });

    }

        }        return false;        return false;

    // Animate the icon

    eyeIcon.style.transform = 'scale(1.2) rotate(15deg)';}

    setTimeout(() => {

        eyeIcon.style.transform = 'scale(1) rotate(0deg)';// ===== FORM SUBMISSION =====

    }, 150);

}// Animations



// Advanced Featuresfunction initAnimations() {function handleFormSubmit(e) {    } else if (!emailRegex.test(email)) {    } else if (!emailRegex.test(email)) {

function initAdvancedFeatures() {

    // Social login buttons    // Add hover effects to cards

    document.querySelectorAll('.social-btn').forEach(btn => {

        btn.addEventListener('click', function() {    const cards = document.querySelectorAll('.demo-card, .feature-item');    e.preventDefault();

            const platform = this.classList.contains('google-btn') ? 'Google' : 'GitHub';

            showNotification(`Đăng nhập với ${platform} đang được phát triển!`, 'info');    cards.forEach(card => {

        });

    });        card.addEventListener('mouseenter', function() {            showFieldError(emailInput, errorElement, 'Vui lòng nhập email hợp lệ');        showFieldError(emailInput, errorElement, 'Vui lòng nhập email hợp lệ');

    

    // Forgot password            this.style.transform = 'translateY(-5px) scale(1.02)';

    const forgotLink = document.querySelector('.forgot-password');

    if (forgotLink) {            this.style.transition = 'transform 0.3s ease';    // Validate all fields

        forgotLink.addEventListener('click', function(e) {

            e.preventDefault();        });

            showNotification('Tính năng quên mật khẩu đang được phát triển!', 'info');

        });            const emailValid = validateEmail();        return false;        return false;

    }

            card.addEventListener('mouseleave', function() {

    // Signup link

    const signupLink = document.querySelector('.signup-link');            this.style.transform = 'translateY(0) scale(1)';    const passwordValid = validatePassword();

    if (signupLink) {

        signupLink.addEventListener('click', function(e) {        });

            e.preventDefault();

            showNotification('Tính năng đăng ký đang được phát triển!', 'info');    });        } else {    } else {

        });

    }    

    

    // Add click effect to logo    // Social button interactions    if (!emailValid || !passwordValid) {

    const logoIcon = document.querySelector('.logo-icon');

    if (logoIcon) {    const socialBtns = document.querySelectorAll('.social-btn');

        let clickCount = 0;

        logoIcon.addEventListener('click', function() {    socialBtns.forEach(btn => {        shakeForm();        showFieldSuccess(emailInput, errorElement);        showFieldSuccess(emailInput, errorElement);

            clickCount++;

            if (clickCount === 5) {        btn.addEventListener('click', function() {

                triggerEasterEgg();

                clickCount = 0;            const platform = this.classList.contains('google-btn') ? 'Google' : 'GitHub';        return false;

            }

        });            showMessage(`Đăng nhập với ${platform} đang được phát triển!`, 'info');

    }

}        });    }        return true;        return true;



// Keyboard Shortcuts    });

function initKeyboardShortcuts() {

    document.addEventListener('keydown', function(e) {        

        // Enter on demo cards

        if (e.key === 'Enter' && e.target.classList.contains('demo-card')) {    // Forgot password link

            e.target.click();

        }    const forgotLink = document.querySelector('.forgot-password');    // Show loading state    }    }

        

        // Escape to close notifications    if (forgotLink) {

        if (e.key === 'Escape') {

            document.querySelectorAll('.notification').forEach(notif => notif.remove());        forgotLink.addEventListener('click', function(e) {    showLoadingState();

        }

                    e.preventDefault();

        // Ctrl/Cmd + Enter to submit form

        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {            showMessage('Tính năng quên mật khẩu đang được phát triển!', 'info');    }}

            elements.loginForm?.dispatchEvent(new Event('submit'));

        }        });

        

        // Tab navigation enhancement    }    // Simulate API call

        if (e.key === 'Tab') {

            document.body.classList.add('keyboard-navigation');}

        }

    });    setTimeout(() => {

    

    // Remove keyboard navigation class on mouse use// Show message

    document.addEventListener('mousedown', function() {

        document.body.classList.remove('keyboard-navigation');function showMessage(message, type) {        // Submit the form

    });

}    const container = document.querySelector('.flash-container') || createFlashContainer();



// Floating Labels            loginForm.submit();function validatePassword() {function validatePassword() {

function addFloatingLabels() {

    document.querySelectorAll('.form-group').forEach(group => {    const messageDiv = document.createElement('div');

        const input = group.querySelector('.form-input');

        const label = group.querySelector('.form-label');    messageDiv.className = `flash-message flash-${type}`;    }, 1500);

        

        if (input && label) {    messageDiv.innerHTML = `

            // Check if input has value on load

            if (input.value) {        <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i>}    const password = passwordInput.value;    const password = passwordInput.value;

                group.classList.add('focused');

            }        <span>${message}</span>

            

            input.addEventListener('focus', () => group.classList.add('focused'));        <button class="flash-close" onclick="this.parentElement.remove()">

            input.addEventListener('blur', () => {

                if (!input.value) group.classList.remove('focused');            <i class="fas fa-times"></i>

            });

        }        </button>function showLoadingState() {    const errorElement = document.getElementById('password-error');    const errorElement = document.getElementById('password-error');

    });

}    `;



// Enhanced Notifications        loginBtn.classList.add('loading');

function showNotification(message, type = 'info', duration = 5000) {

    const container = getNotificationContainer();    container.appendChild(messageDiv);

    

    const notification = document.createElement('div');        loginBtn.disabled = true;        

    notification.className = `notification notification-${type}`;

    notification.innerHTML = `    // Auto remove after 5 seconds

        <div class="notification-content">

            <i class="notification-icon fas ${getNotificationIcon(type)}"></i>    setTimeout(() => {}

            <span class="notification-message">${message}</span>

            <button class="notification-close" onclick="this.closest('.notification').remove()">        if (messageDiv.parentElement) {

                <i class="fas fa-times"></i>

            </button>            messageDiv.style.opacity = '0';    if (password === '') {    if (password === '') {

        </div>

    `;            messageDiv.style.transform = 'translateX(100%)';

    

    container.appendChild(notification);            setTimeout(() => {function hideLoadingState() {

    

    // Animate in                messageDiv.remove();

    requestAnimationFrame(() => {

        notification.classList.add('show');            }, 300);    loginBtn.classList.remove('loading');        showFieldError(passwordInput, errorElement, '');        showFieldError(passwordInput, errorElement, '');

    });

            }

    // Auto remove

    if (duration > 0) {    }, 5000);    loginBtn.disabled = false;

        setTimeout(() => {

            notification.classList.add('hide');}

            setTimeout(() => notification.remove(), 300);

        }, duration);}        return false;        return false;

    }

}function createFlashContainer() {



function getNotificationContainer() {    const container = document.createElement('div');

    let container = document.querySelector('.notification-container');

    if (!container) {    container.className = 'flash-container';

        container = document.createElement('div');

        container.className = 'notification-container';    container.style.cssText = `// ===== SMOOTH ANIMATIONS =====    } else if (password.length < 6) {    } else if (password.length < 6) {

        document.body.appendChild(container);

    }        position: fixed;

    return container;

}        top: 20px;function initSmoothAnimations() {



function getNotificationIcon(type) {        right: 20px;

    const icons = {

        success: 'fa-check-circle',        z-index: 9999;    // Add focus animations to inputs        showFieldError(passwordInput, errorElement, 'Mật khẩu phải có ít nhất 6 ký tự');        showFieldError(passwordInput, errorElement, 'Mật khẩu phải có ít nhất 6 ký tự');

        error: 'fa-exclamation-circle',

        warning: 'fa-exclamation-triangle',        display: flex;

        info: 'fa-info-circle'

    };        flex-direction: column;    const inputs = document.querySelectorAll('.form-input');

    return icons[type] || icons.info;

}        gap: 0.5rem;



// Easter Egg    `;    inputs.forEach(input => {        return false;        return false;

function triggerEasterEgg() {

    showNotification('🎉 Bạn đã tìm ra easter egg! Chúc mừng!', 'success');    document.body.appendChild(container);

    

    // Create confetti effect    return container;        input.addEventListener('focus', function() {

    for (let i = 0; i < 50; i++) {

        createConfetti();}

    }

                this.parentElement.style.transform = 'scale(1.02)';    } else {    } else {

    // Animate logo

    const logoIcon = document.querySelector('.logo-icon');// Add dynamic CSS

    if (logoIcon) {

        logoIcon.style.animation = 'pulse 0.5s ease-in-out 3';const style = document.createElement('style');            this.parentElement.style.transition = 'transform 0.2s ease';

    }

}style.textContent = `



function createConfetti() {    @keyframes shake {        });        showFieldSuccess(passwordInput, errorElement);        showFieldSuccess(passwordInput, errorElement);

    const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#feca57', '#ff9ff3', '#54a0ff'];

    const confetti = document.createElement('div');        0%, 100% { transform: translateX(0); }

    confetti.className = 'confetti';

    confetti.style.cssText = `        25% { transform: translateX(-10px); }        

        position: fixed;

        width: ${Math.random() * 10 + 5}px;        75% { transform: translateX(10px); }

        height: ${Math.random() * 10 + 5}px;

        background: ${colors[Math.floor(Math.random() * colors.length)]};    }        input.addEventListener('blur', function() {        return true;        return true;

        left: ${Math.random() * window.innerWidth}px;

        top: -10px;    

        z-index: 10000;

        pointer-events: none;    .form-input.error {            this.parentElement.style.transform = 'scale(1)';

        border-radius: ${Math.random() > 0.5 ? '50%' : '0'};

        animation: confetti-fall ${Math.random() * 2 + 2}s linear forwards;        border-color: #ef4444 !important;

    `;

            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;        });    }    }

    document.body.appendChild(confetti);

    setTimeout(() => confetti.remove(), 4000);    }

}

        });

// Utility Functions

function debounce(func, wait) {    .form-input.success {

    let timeout;

    return function executedFunction(...args) {        border-color: #10b981 !important;    }}

        const later = () => {

            clearTimeout(timeout);        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1) !important;

            func(...args);

        };    }    // Add hover effects to cards

        clearTimeout(timeout);

        timeout = setTimeout(later, wait);    

    };

}    .error-message.show {    const cards = document.querySelectorAll('.demo-card, .feature-item');



function delay(ms) {        opacity: 1 !important;

    return new Promise(resolve => setTimeout(resolve, ms));

}        transform: translateY(0) !important;    cards.forEach(card => {



async function animateTyping(input, text) {    }

    input.value = '';

    for (let i = 0; i <= text.length; i++) {            card.addEventListener('mouseenter', function() {function showFieldError(input, errorElement, message) {function showFieldError(input, errorElement, message) {

        input.value = text.substring(0, i);

        await delay(50);    .flash-container {

    }

}        position: fixed;            this.style.transform = 'translateY(-5px) scale(1.02)';



// Add dynamic CSS rules        top: 20px;

function addCSS() {

    const style = document.createElement('style');        right: 20px;            this.style.boxShadow = '0 20px 40px rgba(0,0,0,0.1)';    input.classList.add('error');    input.classList.add('error');

    style.textContent = `

        @keyframes shake {        z-index: 9999;

            0%, 100% { transform: translateX(0); }

            25% { transform: translateX(-10px); }        display: flex;        });

            75% { transform: translateX(10px); }

        }        flex-direction: column;

        

        @keyframes confetti-fall {        gap: 0.5rem;            input.classList.remove('success');    input.classList.remove('success');

            to {

                transform: translateY(100vh) rotate(360deg);    }

                opacity: 0;

            }            card.addEventListener('mouseleave', function() {

        }

            .flash-message {

        .form-input.warning {

            border-color: var(--warning);        background: white;            this.style.transform = 'translateY(0) scale(1)';        

            box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);

        }        border-radius: 12px;

        

        .form-input.info {        padding: 1rem 1.5rem;            this.style.boxShadow = '';

            border-color: var(--info);

            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);

        }

                border-left: 4px solid #10b981;        });    if (message && errorElement) {    if (message && errorElement) {

        .password-strength {

            margin-top: 0.5rem;        display: flex;

            opacity: 0;

            transition: opacity 0.3s ease;        align-items: center;    });

        }

                gap: 0.75rem;

        .strength-bars {

            display: flex;        max-width: 400px;}        errorElement.textContent = message;        errorElement.textContent = message;

            gap: 4px;

            margin-bottom: 4px;        transform: translateX(100%);

        }

                opacity: 0;

        .strength-bar {

            height: 4px;        transition: all 0.3s ease;

            background: var(--gray-200);

            border-radius: 2px;        border: 1px solid #e2e8f0;// ===== DEMO ACCOUNTS =====        errorElement.classList.add('show');        errorElement.classList.add('show');

            flex: 1;

            transition: background-color 0.3s ease;    }

        }

            function fillDemoAccount(email, password) {

        .strength-bar.weak { background: var(--error); }

        .strength-bar.fair { background: var(--warning); }    .flash-success {

        .strength-bar.good { background: var(--info); }

        .strength-bar.strong { background: var(--success); }        border-left-color: #10b981;    // Animate the filling    }    }

        

        .strength-text {    }

            font-size: 0.8rem;

            color: var(--gray-500);        emailInput.style.transform = 'scale(1.05)';

        }

            .flash-info {

        .notification-container {

            position: fixed;        border-left-color: #3b82f6;    passwordInput.style.transform = 'scale(1.05)';}}

            top: 20px;

            right: 20px;    }

            z-index: 10000;

            display: flex;        

            flex-direction: column;

            gap: 10px;    .flash-close {

        }

                background: none;    setTimeout(() => {

        .notification {

            background: white;        border: none;

            border-radius: 12px;

            box-shadow: var(--shadow-lg);        color: #94a3b8;        emailInput.value = email;

            border-left: 4px solid var(--info);

            max-width: 400px;        cursor: pointer;

            transform: translateX(100%);

            opacity: 0;        padding: 0.25rem;        emailInput.style.transform = 'scale(1)';function showFieldSuccess(input, errorElement) {function showFieldSuccess(input, errorElement) {

            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

        }        border-radius: 4px;

        

        .notification.show {        margin-left: auto;        

            transform: translateX(0);

            opacity: 1;        transition: color 0.3s ease;

        }

            }        setTimeout(() => {    input.classList.remove('error');    input.classList.remove('error');

        .notification.hide {

            transform: translateX(100%);    

            opacity: 0;

        }    .flash-close:hover {            passwordInput.value = password;

        

        .notification-success { border-left-color: var(--success); }        color: #475569;

        .notification-error { border-left-color: var(--error); }

        .notification-warning { border-left-color: var(--warning); }    }            passwordInput.style.transform = 'scale(1)';    input.classList.add('success');    input.classList.add('success');

        .notification-info { border-left-color: var(--info); }

        `;

        .notification-content {

            display: flex;document.head.appendChild(style);            

            align-items: center;

            gap: 12px;

            padding: 16px;

        }console.log('✅ Fun Work Hub Professional Login ready!');            // Validate fields        

        

        .notification-icon {console.log('• Real-time form validation');

            font-size: 1.2rem;

        }console.log('• Demo account quick-fill');            validateEmail();

        

        .notification-success .notification-icon { color: var(--success); }console.log('• Auto-save email');

        .notification-error .notification-icon { color: var(--error); }

        .notification-warning .notification-icon { color: var(--warning); }console.log('• Password visibility toggle');            validatePassword();    if (errorElement) {    if (errorElement) {

        .notification-info .notification-icon { color: var(--info); }

        console.log('• Smooth animations');

        .notification-message {            

            flex: 1;

            font-size: 0.9rem;            // Focus submit button        errorElement.classList.remove('show');        errorElement.classList.remove('show');

            color: var(--gray-700);

        }            loginBtn.focus();

        

        .notification-close {            loginBtn.style.transform = 'scale(1.05)';    }    }

            background: none;

            border: none;            

            color: var(--gray-400);

            cursor: pointer;            setTimeout(() => {}}

            padding: 4px;

            border-radius: 4px;                loginBtn.style.transform = 'scale(1)';

            transition: color 0.3s ease;

        }            }, 200);

        

        .notification-close:hover {            

            color: var(--gray-600);

        }        }, 300);// ===== FORM SUBMISSION =====// ===== FORM SUBMISSION =====

        

        .loading-overlay {    }, 200);

            position: fixed;

            top: 0;    function handleFormSubmit(e) {function handleFormSubmit(e) {

            left: 0;

            right: 0;    // Show success message

            bottom: 0;

            background: rgba(255, 255, 255, 0.95);    showMessage('Đã điền thông tin demo! Click "Đăng nhập" để tiếp tục.', 'success');    e.preventDefault();    e.preventDefault();

            backdrop-filter: blur(10px);

            z-index: 9999;}

            display: flex;

            align-items: center;        

            justify-content: center;

            opacity: 0;// ===== PASSWORD TOGGLE =====

            visibility: hidden;

            transition: all 0.3s ease;function togglePassword() {    // Validate all fields    // Validate all fields

        }

            const passwordInput = document.getElementById('password');

        .loading-overlay.show {

            opacity: 1;    const eyeIcon = document.getElementById('password-eye');    const emailValid = validateEmail();    const emailValid = validateEmail();

            visibility: visible;

        }    

        

        .loading-content {    if (passwordInput.type === 'password') {    const passwordValid = validatePassword();    const passwordValid = validatePassword();

            text-align: center;

            color: var(--gray-700);        passwordInput.type = 'text';

        }

                eyeIcon.classList.remove('fa-eye');        

        .loading-spinner {

            width: 40px;        eyeIcon.classList.add('fa-eye-slash');

            height: 40px;

            border: 4px solid var(--gray-200);    } else {    if (!emailValid || !passwordValid) {    if (!emailValid || !passwordValid) {

            border-top: 4px solid var(--primary);

            border-radius: 50%;        passwordInput.type = 'password';

            animation: spin 1s linear infinite;

            margin: 0 auto 16px;        eyeIcon.classList.remove('fa-eye-slash');        shakeForm();        shakeForm();

        }

                eyeIcon.classList.add('fa-eye');

        @keyframes spin {

            0% { transform: rotate(0deg); }    }        return false;        return false;

            100% { transform: rotate(360deg); }

        }    

        

        .form-group.focused .form-label {    // Add little animation    }    }

            transform: translateY(-20px) scale(0.85);

            color: var(--primary);    eyeIcon.style.transform = 'scale(1.2)';

        }

            setTimeout(() => {        

        .keyboard-navigation *:focus {

            outline: 2px solid var(--primary) !important;        eyeIcon.style.transform = 'scale(1)';

            outline-offset: 2px !important;

        }    }, 150);    // Show loading state    // Show loading state

        

        .error-message.warning { color: var(--warning); }}

        .error-message.info { color: var(--info); }

    `;    showLoadingState();    showLoadingState();

    document.head.appendChild(style);

}// ===== AUTO COMPLETE =====



// Initialize CSSfunction initAutoComplete() {        

addCSS();

    // Remember email

console.log('🎯 Fun Work Hub Professional Login ready!');

console.log('Features: Form validation, Password strength, Auto-complete, Animations, Keyboard shortcuts, Easter eggs');    const savedEmail = localStorage.getItem('fun_work_hub_email');    // Simulate API call    // Simulate API call

    if (savedEmail && emailInput) {

        emailInput.value = savedEmail;    setTimeout(() => {    setTimeout(() => {

        validateEmail();

    }        // Submit the form        // Submit the form

    

    // Save email on input        loginForm.submit();        loginForm.submit();

    if (emailInput) {

        emailInput.addEventListener('change', function() {    }, 1500);    }, 1500);

            if (this.value && validateEmail()) {

                localStorage.setItem('fun_work_hub_email', this.value);}}

            }

        });

    }

}function showLoadingState() {function showLoadingState() {



// ===== INTERACTIONS =====    loginBtn.classList.add('loading');    loginBtn.classList.add('loading');

function initInteractions() {

    // Social login buttons    loginBtn.disabled = true;    loginBtn.disabled = true;

    const socialBtns = document.querySelectorAll('.social-btn');

    socialBtns.forEach(btn => {        

        btn.addEventListener('click', function() {

            const platform = this.classList.contains('google-btn') ? 'Google' : 'GitHub';    // Show overlay    // Show overlay

            showMessage(`Đăng nhập với ${platform} đang được phát triển!`, 'info');

        });    const overlay = document.getElementById('loadingOverlay');    const overlay = document.getElementById('loadingOverlay');

    });

        if (overlay) {    if (overlay) {

    // Forgot password

    const forgotLink = document.querySelector('.forgot-password');        overlay.classList.add('show');        overlay.classList.add('show');

    if (forgotLink) {

        forgotLink.addEventListener('click', function(e) {    }    }

            e.preventDefault();

            showMessage('Tính năng quên mật khẩu đang được phát triển!', 'info');}}

        });

    }

    

    // Signup linkfunction hideLoadingState() {function hideLoadingState() {

    const signupLink = document.querySelector('.signup-link');

    if (signupLink) {    loginBtn.classList.remove('loading');    loginBtn.classList.remove('loading');

        signupLink.addEventListener('click', function(e) {

            e.preventDefault();    loginBtn.disabled = false;    loginBtn.disabled = false;

            showMessage('Tính năng đăng ký đang được phát triển!', 'info');

        });        

    }

}    // Hide overlay    // Hide overlay



// ===== ANIMATIONS =====    const overlay = document.getElementById('loadingOverlay');    const overlay = document.getElementById('loadingOverlay');

function animateOnLoad() {

    // Animate panels    if (overlay) {    if (overlay) {

    const panels = document.querySelectorAll('.branding-panel, .login-panel');

    panels.forEach((panel, index) => {        overlay.classList.remove('show');        overlay.classList.remove('show');

        panel.style.opacity = '0';

        panel.style.transform = index === 0 ? 'translateX(-50px)' : 'translateX(50px)';    }    }

        

        setTimeout(() => {}}

            panel.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';

            panel.style.opacity = '1';

            panel.style.transform = 'translateX(0)';

        }, 300 + index * 200);// ===== SMOOTH ANIMATIONS =====// ===== SMOOTH ANIMATIONS =====

    });

    function initSmoothAnimations() {function initSmoothAnimations() {

    // Animate form elements

    const formElements = document.querySelectorAll('.form-group, .social-login, .demo-accounts');    // Add focus animations to inputs    // Add focus animations to inputs

    formElements.forEach((element, index) => {

        element.style.opacity = '0';    const inputs = document.querySelectorAll('.form-input');    const inputs = document.querySelectorAll('.form-input');

        element.style.transform = 'translateY(30px)';

            inputs.forEach(input => {    inputs.forEach(input => {

        setTimeout(() => {

            element.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';        input.addEventListener('focus', function() {        input.addEventListener('focus', function() {

            element.style.opacity = '1';

            element.style.transform = 'translateY(0)';            this.parentElement.style.transform = 'scale(1.02)';            this.parentElement.style.transform = 'scale(1.02)';

        }, 800 + index * 100);

    });            this.parentElement.style.transition = 'transform 0.2s ease';            this.parentElement.style.transition = 'transform 0.2s ease';

    

    // Animate features        });        });

    const features = document.querySelectorAll('.feature-item');

    features.forEach((feature, index) => {                

        feature.style.opacity = '0';

        feature.style.transform = 'translateY(30px)';        input.addEventListener('blur', function() {        input.addEventListener('blur', function() {

        

        setTimeout(() => {            this.parentElement.style.transform = 'scale(1)';            this.parentElement.style.transform = 'scale(1)';

            feature.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';

            feature.style.opacity = '1';        });        });

            feature.style.transform = 'translateY(0)';

        }, 1000 + index * 150);    });    });

    });

}        



function shakeForm() {    // Add hover effects to cards    // Add hover effects to cards

    loginForm.style.animation = 'shake 0.5s ease-in-out';

        const cards = document.querySelectorAll('.demo-card, .feature-item');    const cards = document.querySelectorAll('.demo-card, .feature-item');

    setTimeout(() => {

        loginForm.style.animation = '';    cards.forEach(card => {    cards.forEach(card => {

    }, 500);

}        card.addEventListener('mouseenter', function() {        card.addEventListener('mouseenter', function() {



// ===== MESSAGES =====            this.style.transform = 'translateY(-5px) scale(1.02)';            this.style.transform = 'translateY(-5px) scale(1.02)';

function showMessage(message, type) {

    const container = document.querySelector('.flash-container') || createFlashContainer();            this.style.boxShadow = '0 20px 40px rgba(0,0,0,0.1)';            this.style.boxShadow = '0 20px 40px rgba(0,0,0,0.1)';

    

    const messageDiv = document.createElement('div');        });        });

    messageDiv.className = `flash-message flash-${type}`;

    messageDiv.innerHTML = `                

        <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i>

        <span>${message}</span>        card.addEventListener('mouseleave', function() {        card.addEventListener('mouseleave', function() {

        <button class="flash-close" onclick="this.parentElement.remove()">

            <i class="fas fa-times"></i>            this.style.transform = 'translateY(0) scale(1)';            this.style.transform = 'translateY(0) scale(1)';

        </button>

    `;            this.style.boxShadow = '';            this.style.boxShadow = '';

    

    container.appendChild(messageDiv);        });        });

    

    // Auto remove after 5 seconds    });    });

    setTimeout(() => {

        if (messageDiv.parentElement) {}}

            messageDiv.style.opacity = '0';

            messageDiv.style.transform = 'translateX(100%)';

            

            setTimeout(() => {// ===== INTERACTIONS =====// ===== INTERACTIONS =====

                messageDiv.remove();

            }, 300);function initInteractions() {function initInteractions() {

        }

    }, 5000);    // Social login buttons    // Social login buttons

}

    const socialBtns = document.querySelectorAll('.social-btn');    const socialBtns = document.querySelectorAll('.social-btn');

function createFlashContainer() {

    const container = document.createElement('div');    socialBtns.forEach(btn => {    socialBtns.forEach(btn => {

    container.className = 'flash-container';

    document.body.appendChild(container);        btn.addEventListener('click', function() {        btn.addEventListener('click', function() {

    return container;

}            const platform = this.classList.contains('google-btn') ? 'Google' : 'GitHub';            const platform = this.classList.contains('google-btn') ? 'Google' : 'GitHub';



// ===== UTILITY FUNCTIONS =====            showMessage(`Đăng nhập với ${platform} đang được phát triển!`, 'info');            showMessage(`Đăng nhập với ${platform} đang được phát triển!`, 'info');

function addCSSRule(selector, rules) {

    const style = document.createElement('style');        });        });

    style.textContent = `${selector} { ${rules} }`;

    document.head.appendChild(style);    });    });

}

        

// Add CSS animations

addCSSRule('@keyframes shake', `    // Forgot password    // Forgot password

    0%, 100% { transform: translateX(0); }

    25% { transform: translateX(-10px); }    const forgotLink = document.querySelector('.forgot-password');    const forgotLink = document.querySelector('.forgot-password');

    75% { transform: translateX(10px); }

`);    if (forgotLink) {    if (forgotLink) {



addCSSRule('.form-input.success', `        forgotLink.addEventListener('click', function(e) {        forgotLink.addEventListener('click', function(e) {

    border-color: #10b981 !important;

    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1) !important;            e.preventDefault();            e.preventDefault();

`);

            showMessage('Tính năng quên mật khẩu đang được phát triển!', 'info');            showMessage('Tính năng quên mật khẩu đang được phát triển!', 'info');

// ===== KEYBOARD SHORTCUTS =====

document.addEventListener('keydown', function(e) {        });        });

    // Enter key on demo cards

    if (e.key === 'Enter' && e.target.classList.contains('demo-card')) {    }    }

        e.target.click();

    }        

    

    // Escape to close messages    // Signup link    // Signup link

    if (e.key === 'Escape') {

        const messages = document.querySelectorAll('.flash-message');    const signupLink = document.querySelector('.signup-link');    const signupLink = document.querySelector('.signup-link');

        messages.forEach(msg => msg.remove());

    }    if (signupLink) {    if (signupLink) {

    

    // Ctrl + Enter to submit form        signupLink.addEventListener('click', function(e) {        signupLink.addEventListener('click', function(e) {

    if (e.ctrlKey && e.key === 'Enter' && loginForm) {

        loginForm.dispatchEvent(new Event('submit'));            e.preventDefault();            e.preventDefault();

    }

});            showMessage('Tính năng đăng ký đang được phát triển!', 'info');            showMessage('Tính năng đăng ký đang được phát triển!', 'info');



// ===== EASTER EGGS =====        });        });

let clickCount = 0;

const logoIcon = document.querySelector('.logo-icon');    }    }

if (logoIcon) {

    logoIcon.addEventListener('click', function() {}}

        clickCount++;

        if (clickCount === 5) {

            this.style.animation = 'pulse 0.5s ease-in-out 3';

            showMessage('🎉 Bạn đã tìm ra easter egg! Chúc mừng!', 'success');// ===== DEMO ACCOUNTS =====// ===== DEMO ACCOUNTS =====

            

            // Create confetti effectfunction fillDemoAccount(email, password) {function fillDemoAccount(email, password) {

            for (let i = 0; i < 20; i++) {

                createConfetti();    // Animate the filling    // Animate the filling

            }

                emailInput.style.transform = 'scale(1.05)';    emailInput.style.transform = 'scale(1.05)';

            clickCount = 0;

        }    passwordInput.style.transform = 'scale(1.05)';    passwordInput.style.transform = 'scale(1.05)';

    });

}        



function createConfetti() {    setTimeout(() => {    setTimeout(() => {

    const confetti = document.createElement('div');

    confetti.style.cssText = `        emailInput.value = email;        emailInput.value = email;

        position: fixed;

        width: 10px;        emailInput.style.transform = 'scale(1)';        emailInput.style.transform = 'scale(1)';

        height: 10px;

        background: ${['#ff6b6b', '#4ecdc4', '#45b7d1', '#feca57', '#ff9ff3'][Math.floor(Math.random() * 5)]};                

        left: ${Math.random() * window.innerWidth}px;

        top: -10px;        setTimeout(() => {        setTimeout(() => {

        z-index: 10000;

        pointer-events: none;            passwordInput.value = password;            passwordInput.value = password;

        animation: confetti-fall 3s linear forwards;

    `;            passwordInput.style.transform = 'scale(1)';            passwordInput.style.transform = 'scale(1)';

    

    document.body.appendChild(confetti);                        

    

    setTimeout(() => {            // Validate fields            // Validate fields

        confetti.remove();

    }, 3000);            validateEmail();            validateEmail();

}

            validatePassword();            validatePassword();

addCSSRule('@keyframes confetti-fall', `

    to {                        

        transform: translateY(100vh) rotate(360deg);

        opacity: 0;            // Focus submit button            // Focus submit button

    }

`);            loginBtn.focus();            loginBtn.focus();



console.log('🎯 Fun Work Hub PRO Login ready! Features:');            loginBtn.style.transform = 'scale(1.05)';            loginBtn.style.transform = 'scale(1.05)';

console.log('• Real-time form validation');

console.log('• Smooth animations & transitions');                        

console.log('• Demo account quick-fill');

console.log('• Loading states & feedback');            setTimeout(() => {            setTimeout(() => {

console.log('• Keyboard shortcuts (Ctrl+Enter to submit)');

console.log('• Easter eggs (click logo 5 times!)');                loginBtn.style.transform = 'scale(1)';                loginBtn.style.transform = 'scale(1)';

console.log('• Auto-save email');

console.log('• Password visibility toggle');            }, 200);            }, 200);

                        

        }, 300);        }, 300);

    }, 200);    }, 200);

        

    // Show success message    // Show success message

    showMessage('Đã điền thông tin demo! Click "Đăng nhập" để tiếp tục.', 'success');    showMessage('Đã điền thông tin demo! Click "Đăng nhập" để tiếp tục.', 'success');

}}

                    

// ===== PASSWORD TOGGLE =====                    // Focus on submit button

function togglePassword() {                    const submitBtn = document.querySelector('.btn-submit');

    const passwordInput = document.getElementById('password');                    if (submitBtn) {

    const eyeIcon = document.getElementById('password-eye');                        submitBtn.focus();

                        }

    if (passwordInput.type === 'password') {                }

        passwordInput.type = 'text';            }

        eyeIcon.classList.remove('fa-eye');        });

        eyeIcon.classList.add('fa-eye-slash');        

    } else {        // Add pointer cursor

        passwordInput.type = 'password';        item.style.cursor = 'pointer';

        eyeIcon.classList.remove('fa-eye-slash');        item.title = 'Click để điền vào form';

        eyeIcon.classList.add('fa-eye');    });

    }});

    

    // Add little animation// Simple utility functions

    eyeIcon.style.transform = 'scale(1.2)';function showMessage(message, type = 'success') {

    setTimeout(() => {    const messagesContainer = document.querySelector('.flash-messages') || createMessagesContainer();

        eyeIcon.style.transform = 'scale(1)';    

    }, 150);    const alertDiv = document.createElement('div');

}    alertDiv.className = `alert alert-${type}`;

    alertDiv.textContent = message;

// ===== AUTO COMPLETE =====    

function initAutoComplete() {    messagesContainer.appendChild(alertDiv);

    // Remember email    

    const savedEmail = localStorage.getItem('fun_work_hub_email');    // Auto remove after 5 seconds

    if (savedEmail && emailInput) {    setTimeout(() => {

        emailInput.value = savedEmail;        alertDiv.style.opacity = '0';

        validateEmail();        setTimeout(() => {

    }            alertDiv.remove();

            }, 300);

    // Save email on input    }, 5000);

    emailInput?.addEventListener('change', function() {}

        if (this.value && validateEmail()) {

            localStorage.setItem('fun_work_hub_email', this.value);function createMessagesContainer() {

        }    const container = document.createElement('div');

    });    container.className = 'flash-messages';

}    document.querySelector('.main-content').prepend(container);

    return container;

// ===== ANIMATIONS =====}

function animateOnLoad() {

    // Animate panels// Fun animations and effects

    const panels = document.querySelectorAll('.branding-panel, .login-panel');function initFunEffects() {

    panels.forEach((panel, index) => {    // Add bounce effect to memes

        panel.style.opacity = '0';    const memes = document.querySelectorAll('.meme-img');

        panel.style.transform = index === 0 ? 'translateX(-50px)' : 'translateX(50px)';    memes.forEach(meme => {

                meme.addEventListener('mouseenter', function() {

        setTimeout(() => {            this.style.transform = 'scale(1.05) rotate(2deg)';

            panel.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';            this.style.transition = 'transform 0.3s ease';

            panel.style.opacity = '1';        });

            panel.style.transform = 'translateX(0)';        

        }, 300 + index * 200);        meme.addEventListener('mouseleave', function() {

    });            this.style.transform = 'scale(1) rotate(0deg)';

            });

    // Animate form elements    });

    const formElements = document.querySelectorAll('.form-group, .social-login, .demo-accounts');    

    formElements.forEach((element, index) => {    // Add shake effect to feature cards

        element.style.opacity = '0';    const featureCards = document.querySelectorAll('.feature-card');

        element.style.transform = 'translateY(30px)';    featureCards.forEach(card => {

                card.addEventListener('mouseenter', function() {

        setTimeout(() => {            this.style.animation = 'shake 0.5s ease-in-out';

            element.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';        });

            element.style.opacity = '1';        

            element.style.transform = 'translateY(0)';        card.addEventListener('animationend', function() {

        }, 800 + index * 100);            this.style.animation = '';

    });        });

        });

    // Animate features    

    const features = document.querySelectorAll('.feature-item');    // Add rainbow effect to submit button

    features.forEach((feature, index) => {    const submitBtn = document.querySelector('.btn-submit');

        feature.style.opacity = '0';    if (submitBtn) {

        feature.style.transform = 'translateY(30px)';        submitBtn.addEventListener('mouseenter', function() {

                    this.style.background = 'linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4, #ffeaa7, #dda0dd)';

        setTimeout(() => {            this.style.backgroundSize = '400% 400%';

            feature.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';            this.style.animation = 'rainbow 2s ease infinite';

            feature.style.opacity = '1';        });

            feature.style.transform = 'translateY(0)';        

        }, 1000 + index * 150);        submitBtn.addEventListener('mouseleave', function() {

    });            this.style.background = '#6366f1';

}            this.style.animation = '';

        });

function shakeForm() {    }

    loginForm.style.animation = 'shake 0.5s ease-in-out';    

        // Easter egg: Konami code

    setTimeout(() => {    let konamiCode = '';

        loginForm.style.animation = '';    const targetCode = 'ArrowUpArrowUpArrowDownArrowDownArrowLeftArrowRightArrowLeftArrowRightKeyBKeyA';

    }, 500);    

}    document.addEventListener('keydown', function(e) {

        konamiCode += e.code;

// ===== MESSAGES =====        if (konamiCode.length > targetCode.length) {

function showMessage(message, type = 'success') {            konamiCode = konamiCode.slice(-targetCode.length);

    const container = document.querySelector('.flash-container') || createFlashContainer();        }

            

    const messageDiv = document.createElement('div');        if (konamiCode === targetCode) {

    messageDiv.className = `flash-message flash-${type}`;            triggerEasterEgg();

    messageDiv.innerHTML = `        }

        <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i>    });

        <span>${message}</span>}

        <button class="flash-close" onclick="this.parentElement.remove()">

            <i class="fas fa-times"></i>function triggerEasterEgg() {

        </button>    // Create floating memes

    `;    for (let i = 0; i < 10; i++) {

            setTimeout(() => {

    container.appendChild(messageDiv);            createFloatingMeme();

            }, i * 200);

    // Auto remove after 5 seconds    }

    setTimeout(() => {    

        if (messageDiv.parentElement) {    // Show special message

            messageDiv.style.opacity = '0';    showMessage('🎉 KONAMI CODE ACTIVATED! You found the secret! 🎉', 'success');

            messageDiv.style.transform = 'translateX(100%)';    

                // Play celebration sound (if user allows)

            setTimeout(() => {    try {

                messageDiv.remove();        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+HqwW0gBSuBzvLZeiQHL4DK79iGNAYYZrjt559NEAxPpuHwtmMcBjiR2O');

            }, 300);        audio.play();

        }    } catch (e) {

    }, 5000);        console.log('Audio not supported, but that\'s okay!');

}    }

}

function createFlashContainer() {

    const container = document.createElement('div');function createFloatingMeme() {

    container.className = 'flash-container';    const memeEmojis = ['😂', '🚀', '💯', '🎯', '🎉', '😎', '🤖', '📊', '🎭', '⚡'];

    document.body.appendChild(container);    const emoji = memeEmojis[Math.floor(Math.random() * memeEmojis.length)];

    return container;    

}    const floatingMeme = document.createElement('div');

    floatingMeme.textContent = emoji;

// ===== UTILITY FUNCTIONS =====    floatingMeme.style.cssText = `

function addCSSRule(selector, rules) {        position: fixed;

    const style = document.createElement('style');        font-size: 3rem;

    style.textContent = `${selector} { ${rules} }`;        pointer-events: none;

    document.head.appendChild(style);        z-index: 9999;

}        left: ${Math.random() * window.innerWidth}px;

        top: ${window.innerHeight}px;

// Add CSS animations        animation: float-up 3s ease-out forwards;

addCSSRule('@keyframes shake', `    `;

    0%, 100% { transform: translateX(0); }    

    25% { transform: translateX(-10px); }    document.body.appendChild(floatingMeme);

    75% { transform: translateX(10px); }    

`);    setTimeout(() => {

        floatingMeme.remove();

addCSSRule('.form-input.success', `    }, 3000);

    border-color: #10b981 !important;}

    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1) !important;

`);// Add CSS animations

const style = document.createElement('style');

// ===== KEYBOARD SHORTCUTS =====style.textContent = `

document.addEventListener('keydown', function(e) {    @keyframes shake {

    // Enter key on demo cards        0%, 100% { transform: translateX(0); }

    if (e.key === 'Enter' && e.target.classList.contains('demo-card')) {        25% { transform: translateX(-5px); }

        e.target.click();        75% { transform: translateX(5px); }

    }    }

        

    // Escape to close messages    @keyframes rainbow {

    if (e.key === 'Escape') {        0% { background-position: 0% 50%; }

        const messages = document.querySelectorAll('.flash-message');        50% { background-position: 100% 50%; }

        messages.forEach(msg => msg.remove());        100% { background-position: 0% 50%; }

    }    }

        

    // Ctrl + Enter to submit form    @keyframes float-up {

    if (e.ctrlKey && e.key === 'Enter' && loginForm) {        0% {

        loginForm.dispatchEvent(new Event('submit'));            transform: translateY(0) rotate(0deg);

    }            opacity: 1;

});        }

        100% {

// ===== EASTER EGGS =====            transform: translateY(-100vh) rotate(360deg);

let clickCount = 0;            opacity: 0;

document.querySelector('.logo-icon')?.addEventListener('click', function() {        }

    clickCount++;    }

    if (clickCount === 5) {`;

        this.style.animation = 'pulse 0.5s ease-in-out 3';document.head.appendChild(style);

        showMessage('🎉 Bạn đã tìm ra easter egg! Chúc mừng!', 'success');

        // Initialize fun effects when DOM is loaded

        // Create confetti effectdocument.addEventListener('DOMContentLoaded', function() {

        for (let i = 0; i < 20; i++) {    initFunEffects();

            createConfetti();    

        }    // Add some random fun facts

            const funFacts = [

        clickCount = 0;        "💡 Fun fact: Người dùng Fun Work Hub tăng 200% hiệu suất!",

    }        "🎯 Pro tip: Click vào meme để có thêm may mắn!",

});        "🚀 Easter egg: Thử nhập Konami code xem sao...",

        "😎 Tip: Hover chuột lên các thẻ feature để xem magic!"

function createConfetti() {    ];

    const confetti = document.createElement('div');    

    confetti.style.cssText = `    // Show random fun fact after 10 seconds

        position: fixed;    setTimeout(() => {

        width: 10px;        const randomFact = funFacts[Math.floor(Math.random() * funFacts.length)];

        height: 10px;        showMessage(randomFact, 'success');

        background: ${['#ff6b6b', '#4ecdc4', '#45b7d1', '#feca57', '#ff9ff3'][Math.floor(Math.random() * 5)]};    }, 10000);

        left: ${Math.random() * window.innerWidth}px;});
        top: -10px;
        z-index: 10000;
        pointer-events: none;
        animation: confetti-fall 3s linear forwards;
    `;
    
    document.body.appendChild(confetti);
    
    setTimeout(() => {
        confetti.remove();
    }, 3000);
}

addCSSRule('@keyframes confetti-fall', `
    to {
        transform: translateY(100vh) rotate(360deg);
        opacity: 0;
    }
`);

console.log('🎯 Fun Work Hub PRO Login ready! Features:');
console.log('• Real-time form validation');
console.log('• Smooth animations & transitions');
console.log('• Demo account quick-fill');
console.log('• Loading states & feedback');
console.log('• Keyboard shortcuts (Ctrl+Enter to submit)');
console.log('• Easter eggs (click logo 5 times!)');
console.log('• Auto-save email');
console.log('• Password visibility toggle');