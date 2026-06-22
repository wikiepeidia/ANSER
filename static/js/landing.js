<<<<<<< HEAD
document.addEventListener('DOMContentLoaded', () => {
    // Wait a brief moment to ensure fonts and layout are rendered
    setTimeout(() => {
        gsap.from(".hero-text-anim", {
            y: 100,              // Start 100px below normal position
            opacity: 0,          // Start completely transparent
            duration: 1.2,       // Take 1.2 seconds to animate
            stagger: 0.15,       // Wait 0.15 seconds between each line
            ease: "power4.out",  // Start fast, end very smoothly (The Apple feel)
        });
    }, 100);
});
=======
/**
 * landing.js — Toàn bộ logic tương tác của Landing Page
 *
 * Mục lục:
 *   1. Smooth scroll cho anchor links
 *   2. Navbar đổi nền khi cuộn qua Hero (class "scrolled")
 *   3. Active state cho nav link theo section đang xem
 *   4. Theme toggle (dark/light)
 *   5. Contact modal
 *   6. Button ripple effect
 *   7. Form validate (email regex + inline error)
 */
(function () {
    'use strict';

    /* ──────────────────────────────────────────
       1. SMOOTH SCROLL — anchor links
       ────────────────────────────────────────── */

    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
        link.addEventListener('click', function (e) {
            var href = link.getAttribute('href');
            if (href === '#') return;

            var target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                var headerHeight = 70;
                var top = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;
                window.scrollTo({ top: top, behavior: 'smooth' });
            }
        });
    });

    /* ──────────────────────────────────────────
       2. NAVBAR — đổi nền khi cuộn qua Hero
       ────────────────────────────────────────── */

    var header = document.querySelector('.header');
    var hero = document.querySelector('.hero');

    function updateNavbar() {
        if (!header) return;
        var threshold = hero ? hero.offsetHeight * 0.8 : 300;
        if (window.scrollY > threshold) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    }

    if (header) {
        window.addEventListener('scroll', updateNavbar, { passive: true });
        updateNavbar();
    }

    /* ──────────────────────────────────────────
       3. ACTIVE STATE — nav link theo section đang xem
       ────────────────────────────────────────── */

    var navLinks = document.querySelectorAll('.header__nav-link[href^="#"]');
    var sections = [];

    navLinks.forEach(function (link) {
        var href = link.getAttribute('href');
        if (href && href !== '#') {
            var section = document.querySelector(href);
            if (section) {
                sections.push({ el: section, link: link });
            }
        }
    });

    if (sections.length > 0) {
        var sectionObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                var match = sections.find(function (s) { return s.el === entry.target; });
                if (!match) return;

                if (entry.isIntersecting) {
                    navLinks.forEach(function (l) { l.classList.remove('active'); });
                    match.link.classList.add('active');
                }
            });
        }, {
            threshold: 0.15,
            rootMargin: '-70px 0px -40% 0px'
        });

        sections.forEach(function (s) {
            sectionObserver.observe(s.el);
        });
    }

    /* ──────────────────────────────────────────
       4. THEME TOGGLE — dark / light
       ────────────────────────────────────────── */

    var toggleBtn = document.getElementById('landing-theme-toggle');
    var themeIcon = document.getElementById('theme-icon');

    if (toggleBtn && themeIcon) {
        function syncIcon() {
            var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            themeIcon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
        }

        toggleBtn.addEventListener('click', function () {
            var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme-preference', next);
            syncIcon();
        });

        syncIcon();
    }

    /* ──────────────────────────────────────────
       5. CONTACT MODAL
       ────────────────────────────────────────── */

    var modal = document.getElementById('contact-modal');
    var contactLink = document.getElementById('contact-link');
    var closeBtn = document.getElementById('modal-close-btn');

    if (modal && contactLink) {
        contactLink.addEventListener('click', function (e) {
            e.preventDefault();
            modal.classList.add('active');
        });
    }

    if (modal && closeBtn) {
        closeBtn.addEventListener('click', function () {
            modal.classList.remove('active');
        });
    }

    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) modal.classList.remove('active');
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') modal.classList.remove('active');
        });
    }

    /* ──────────────────────────────────────────
       6. BUTTON RIPPLE EFFECT
       ────────────────────────────────────────── */

    document.querySelectorAll('.landing-page .btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            var r = document.createElement('span');
            r.className = 'ripple';
            var rect = btn.getBoundingClientRect();
            var size = Math.max(rect.width, rect.height);
            r.style.cssText = 'width:' + size + 'px;height:' + size + 'px;'
                + 'left:' + (e.clientX - rect.left - size / 2) + 'px;'
                + 'top:' + (e.clientY - rect.top - size / 2) + 'px;';
            btn.appendChild(r);
            r.addEventListener('animationend', function () { r.remove(); });
        });
    });

    /* ──────────────────────────────────────────
       7. FORM VALIDATE — email regex + inline error
       ────────────────────────────────────────── */

    var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    document.querySelectorAll('.landing-page form').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            var valid = true;

            var emailInputs = form.querySelectorAll('input[type="email"]');
            emailInputs.forEach(function (input) {
                var errorEl = input.parentElement.querySelector('.field-error');

                if (!errorEl) {
                    errorEl = document.createElement('span');
                    errorEl.className = 'field-error';
                    errorEl.style.cssText = 'color:#ef4444;font-size:0.82rem;display:block;margin-top:4px;';
                    input.parentElement.appendChild(errorEl);
                }

                if (!input.value.trim()) {
                    errorEl.textContent = 'Vui lòng nhập email.';
                    input.style.borderColor = '#ef4444';
                    valid = false;
                } else if (!EMAIL_RE.test(input.value.trim())) {
                    errorEl.textContent = 'Email không hợp lệ.';
                    input.style.borderColor = '#ef4444';
                    valid = false;
                } else {
                    errorEl.textContent = '';
                    input.style.borderColor = '';
                }
            });

            if (!valid) {
                e.preventDefault();
            }
        });

        form.querySelectorAll('input[type="email"]').forEach(function (input) {
            input.addEventListener('input', function () {
                var errorEl = input.parentElement.querySelector('.field-error');
                if (errorEl && input.value.trim() && EMAIL_RE.test(input.value.trim())) {
                    errorEl.textContent = '';
                    input.style.borderColor = '';
                }
            });
        });
    });

})();
>>>>>>> 440f07aaf3d3a32f5782a445371070ca2340fb0b
