/**
 * reveal.js — Scroll reveal dùng IntersectionObserver
 *
 * Cách dùng:
 *   1. Link file animations.css trong <head>
 *   2. Link file reveal.js trước </body>
 *   3. Gắn class "reveal" vào element muốn có animation
 *      Ví dụ: <section class="reveal">...</section>
 *
 * Khi element cuộn vào viewport → tự động thêm class "visible"
 * → CSS transition trong animations.css sẽ chạy animation.
 */
(function () {
    'use strict';

    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                entry.target.classList.add('revealed');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.12,
        rootMargin: '0px 0px -40px 0px'
    });

    function init() {
        var elements = document.querySelectorAll('.reveal, .reveal-left, .reveal-right, [data-reveal]');
        elements.forEach(function (el) {
            observer.observe(el);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
