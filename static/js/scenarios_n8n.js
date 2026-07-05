document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    const toast     = document.getElementById('scToast');
    const wfGrid    = document.getElementById('wfGrid');
    const wfLoading = document.getElementById('wfLoading');
    const wfEmpty   = document.getElementById('wfEmpty');
    const tplGrid   = document.getElementById('tplGrid');
    const statusEl  = document.getElementById('n8nStatus');
    const statusTxt = document.getElementById('n8nStatusText');

    function showToast(msg, ok) {
        toast.textContent = msg;
        toast.className = 'sc-toast ' + (ok ? 'ok' : 'err') + ' show';
        setTimeout(() => toast.classList.remove('show'), 3500);
    }

    function timeAgo(iso) {
        if (!iso) return '';
        const diff = (Date.now() - new Date(iso).getTime()) / 1000;
        if (diff < 60) return 'vừa xong';
        if (diff < 3600) return Math.floor(diff / 60) + ' phút trước';
        if (diff < 86400) return Math.floor(diff / 3600) + ' giờ trước';
        return Math.floor(diff / 86400) + ' ngày trước';
    }

    // ── Status ───────────────────────────────────────────
    async function checkStatus() {
        try {
            const r = await fetch('/api/n8n/status');
            const d = await r.json();
            if (d.online) {
                statusEl.className = 'sc-status online';
                statusTxt.textContent = 'n8n Trực tuyến';
            } else {
                statusEl.className = 'sc-status offline';
                statusTxt.textContent = 'n8n Ngoại tuyến';
            }
        } catch {
            statusEl.className = 'sc-status offline';
            statusTxt.textContent = 'Không kết nối';
        }
    }

    // ── Workflows ────────────────────────────────────────
    async function loadWorkflows() {
        wfLoading.style.display = 'block';
        wfGrid.style.display = 'none';
        wfEmpty.style.display = 'none';

        try {
            const r = await fetch('/api/n8n/workflows');
            const d = await r.json();
            wfLoading.style.display = 'none';

            if (!d.success || !d.workflows.length) {
                wfEmpty.style.display = 'block';
                return;
            }

            wfGrid.style.display = 'grid';
            wfGrid.innerHTML = d.workflows.map(wf => `
                <div class="sc-wf-card" data-id="${wf.id}">
                    <div class="sc-wf-header">
                        <div class="sc-wf-name">${esc(wf.name)}</div>
                        <button class="sc-wf-badge ${wf.active ? 'on' : 'off'}"
                                onclick="toggleActive('${wf.id}', ${!wf.active})">
                            <i class="fas fa-${wf.active ? 'check-circle' : 'pause-circle'}"></i>
                            ${wf.active ? 'Hoạt động' : 'Tạm dừng'}
                        </button>
                    </div>
                    <div class="sc-wf-meta">
                        <span class="sc-wf-meta-item"><i class="fas fa-project-diagram"></i> ${wf.nodes} nút</span>
                        <span class="sc-wf-meta-item"><i class="fas fa-clock"></i> ${timeAgo(wf.updatedAt)}</span>
                        ${wf.tags.length ? wf.tags.map(t => `<span class="sc-wf-meta-item"><i class="fas fa-tag"></i> ${esc(t)}</span>`).join('') : ''}
                    </div>
                    <div class="sc-wf-actions">
                        <button class="sc-wf-btn run" onclick="runWorkflow('${wf.id}', this)">
                            <i class="fas fa-play"></i> Chạy
                        </button>
                        <button class="sc-wf-btn history" onclick="toggleHistory('${wf.id}', this)">
                            <i class="fas fa-history"></i> Lịch sử
                        </button>
                        <button class="sc-wf-btn delete" onclick="deleteWorkflow('${wf.id}', '${esc(wf.name)}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    <div class="sc-exec-panel" id="exec-${wf.id}"></div>
                </div>
            `).join('');
        } catch {
            wfLoading.style.display = 'none';
            wfEmpty.style.display = 'block';
        }
    }

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    // ── Run workflow ─────────────────────────────────────
    window.runWorkflow = async function(id, btn) {
        const origHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang chạy...';
        btn.classList.add('running');
        btn.disabled = true;

        try {
            const r = await fetch(`/api/n8n/workflows/${id}/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ testData: {
                    device_id: 'ANSER-TEST-01',
                    event_type: 'sale_completed',
                    amount: 150000,
                    source: 'ANSER',
                    test: true
                } }),
            });
            console.log('Run response status:', r.status, r.statusText);
            const text = await r.text();
            console.log('Run response body:', text);
            let d;
            try { d = JSON.parse(text); } catch { d = { success: false, error: 'Phản hồi không phải JSON: ' + text.substring(0, 100) }; }
            btn.innerHTML = origHTML;
            btn.classList.remove('running');
            btn.disabled = false;

            const card = btn.closest('.sc-wf-card');
            const resultId = 'result-' + id;
            let resultEl = document.getElementById(resultId);
            if (!resultEl) {
                resultEl = document.createElement('div');
                resultEl.id = resultId;
                resultEl.className = 'sc-run-result';
                card.appendChild(resultEl);
            }

            if (d.success) {
                let html = '<div class="sc-result-header ok"><i class="fas fa-check-circle"></i> ' + (d.message || 'Thành công') + '</div>';
                if (d.response) {
                    const json = typeof d.response === 'object' ? JSON.stringify(d.response, null, 2) : d.response;
                    html += '<pre class="sc-result-body">' + esc(json) + '</pre>';
                }
                resultEl.innerHTML = html;
            } else {
                resultEl.innerHTML = '<div class="sc-result-header err"><i class="fas fa-times-circle"></i> ' + esc(d.error || 'Lỗi') + '</div>';
            }
            resultEl.style.display = 'block';
            setTimeout(() => { resultEl.style.display = 'none'; }, 15000);
            return;
        } catch {
            showToast('Không kết nối được n8n', false);
        }

        btn.innerHTML = origHTML;
        btn.classList.remove('running');
        btn.disabled = false;
    };

    // ── Toggle active ────────────────────────────────────
    window.toggleActive = async function(id, active) {
        try {
            const r = await fetch(`/api/n8n/workflows/${id}/activate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ active }),
            });
            const d = await r.json();
            if (d.success) {
                showToast(d.active ? 'Đã kích hoạt quy trình' : 'Đã tắt quy trình', true);
                loadWorkflows();
            } else {
                showToast(d.error || 'Không thể kích hoạt', false);
            }
        } catch {
            showToast('Không kết nối được n8n', false);
        }
    };

    // ── Execution history ────────────────────────────────
    window.toggleHistory = async function(id, btn) {
        const panel = document.getElementById('exec-' + id);
        if (panel.classList.contains('open')) {
            panel.classList.remove('open');
            return;
        }

        panel.innerHTML = '<div style="padding:8px 0;color:#aaa;font-size:.78rem;"><i class="fas fa-spinner fa-spin"></i> Đang tải...</div>';
        panel.classList.add('open');

        try {
            const r = await fetch(`/api/n8n/workflows/${id}/executions`);
            const d = await r.json();

            if (!d.success || !d.executions.length) {
                panel.innerHTML = '<div class="sc-exec-empty">Chưa có lần chạy nào</div>';
                return;
            }

            panel.innerHTML = d.executions.map(ex => {
                const status = ex.status || 'unknown';
                const time = ex.startedAt ? new Date(ex.startedAt).toLocaleString('vi-VN') : '';
                return `<div class="sc-exec-item">
                    <span class="sc-exec-dot ${status}"></span>
                    <span>${status}</span>
                    <span style="margin-left:auto;font-size:.72rem;color:#bbb;">${time}</span>
                </div>`;
            }).join('');
        } catch {
            panel.innerHTML = '<div class="sc-exec-empty">Không tải được</div>';
        }
    };

    // ── Delete workflow ─────────────────────────────────
    window.deleteWorkflow = async function(id, name) {
        if (!confirm('Xóa quy trình "' + name + '"? Không thể hoàn tác.')) return;
        try {
            const r = await fetch('/api/n8n/workflows/' + id, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrfToken },
            });
            const d = await r.json();
            if (d.success) {
                showToast('Đã xóa quy trình', true);
                loadWorkflows();
            } else {
                showToast('Lỗi: ' + (d.error || 'Không xác định'), false);
            }
        } catch {
            showToast('Không kết nối được n8n', false);
        }
    };

    // ── Templates ────────────────────────────────────────
    window.toggleTemplates = function() {
        const panel = document.getElementById('tplPanel');
        panel.classList.toggle('is-collapsed');
        // After toggle finishes, refresh arrow visibility
        setTimeout(updateTplNavState, 250);
    };

    async function loadTemplates() {
        // Show skeleton while loading so the row doesn't jump
        tplGrid.innerHTML = `
            <div class="sc-tpl-skeleton">
                <div class="sc-tpl-skel-card"></div>
                <div class="sc-tpl-skel-card"></div>
                <div class="sc-tpl-skel-card"></div>
                <div class="sc-tpl-skel-card"></div>
            </div>`;
        updateTplNavState();

        try {
            const r = await fetch('/api/n8n/templates');
            const d = await r.json();
            if (!d.success || !d.templates.length) {
                tplGrid.innerHTML = `
                    <div class="sc-tpl-empty">
                        <i class="fas fa-inbox" style="font-size:1.4rem;display:block;margin-bottom:8px;opacity:.5;"></i>
                        Chưa có mẫu nào.
                    </div>`;
                updateTplNavState();
                return;
            }
            tplGrid.innerHTML = d.templates.map(t => `
                <div class="sc-tpl-card" tabindex="0" data-slug="${t.slug}" onclick="deployTemplate(this, '${t.slug}')">
                    <div class="sc-tpl-icon" style="background:${t.color}">
                        <i class="fas ${t.icon}"></i>
                    </div>
                    <div>
                        <div class="sc-tpl-name">${esc(t.label)}</div>
                        <div class="sc-tpl-desc">${esc(t.desc)}</div>
                    </div>
                </div>
            `).join('');
            enableDragScroll(tplGrid);
            syncOverflowState(tplGrid);
            updateTplNavState();
        } catch {
            tplGrid.innerHTML = `
                <div class="sc-tpl-empty" style="color:#F44336;border-color:rgba(244,67,54,.3);">
                    <i class="fas fa-triangle-exclamation" style="font-size:1.4rem;display:block;margin-bottom:8px;"></i>
                    Không tải được mẫu. Bấm Làm mới để thử lại.
                </div>`;
            updateTplNavState();
        }
    }

    // ── Drag-to-scroll + vertical wheel => horizontal scroll ──
    function enableDragScroll(el) {
        if (!el || el.__dragScrollBound) return;
        el.__dragScrollBound = true;

        let isDown = false;
        let startX = 0;
        let startScroll = 0;
        let moved = 0;

        const onDown = (e) => {
            if (e.button === 2) return;
            isDown = true;
            moved = 0;
            startX = (e.touches ? e.touches[0].pageX : e.pageX) - el.getBoundingClientRect().left;
            startScroll = el.scrollLeft;
            el.classList.add('is-dragging');
        };
        const onMove = (e) => {
            if (!isDown) return;
            const x = (e.touches ? e.touches[0].pageX : e.pageX) - el.getBoundingClientRect().left;
            const walk = (x - startX) * 1.2;
            moved = Math.abs(walk);
            el.scrollLeft = startScroll - walk;
            if (e.cancelable) e.preventDefault();
        };
        const onUp = () => {
            if (!isDown) return;
            isDown = false;
            el.classList.remove('is-dragging');
            // Suppress click if we actually dragged (so deploy doesn't fire)
            if (moved > 5) {
                el.querySelectorAll('.sc-tpl-card').forEach(card => {
                    const handler = (ev) => {
                        ev.stopPropagation();
                        ev.preventDefault();
                        card.removeEventListener('click', handler, true);
                    };
                    card.addEventListener('click', handler, true);
                });
            }
            syncOverflowState(el);
        };

        el.addEventListener('mousedown', onDown);
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
        el.addEventListener('touchstart', onDown, { passive: true });
        el.addEventListener('touchmove', onMove, { passive: false });
        el.addEventListener('touchend', onUp);

        // Track whether the next focus came from a pointer (click/tap) so we
        // don't fight the scroll position on plain clicks — only auto-scroll
        // into view for keyboard (Tab) focus.
        let focusedViaPointer = false;
        el.addEventListener('mousedown', () => { focusedViaPointer = true; }, true);
        el.addEventListener('touchstart', () => { focusedViaPointer = true; }, true);

        // Keep nav arrow enabled/disabled state in sync
        el.addEventListener('scroll', updateTplNavState, { passive: true });

        // Keyboard navigation when the strip itself is focused
        el.addEventListener('keydown', (e) => {
            const card = e.target.closest('.sc-tpl-card');
            if (!card) return;
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                const next = card.nextElementSibling;
                if (next && next.classList.contains('sc-tpl-card')) {
                    next.focus();
                    next.scrollIntoView({ behavior: 'smooth', inline: 'start', block: 'nearest' });
                }
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                const prev = card.previousElementSibling;
                if (prev && prev.classList.contains('sc-tpl-card')) {
                    prev.focus();
                    prev.scrollIntoView({ behavior: 'smooth', inline: 'start', block: 'nearest' });
                }
            } else if (e.key === 'Home') {
                e.preventDefault();
                el.scrollTo({ left: 0, behavior: 'smooth' });
            } else if (e.key === 'End') {
                e.preventDefault();
                el.scrollTo({ left: el.scrollWidth, behavior: 'smooth' });
            }
        });

        // Prevent focus from scrolling the whole page when tabbing through cards.
        // Skip it for pointer-driven focus (click/tap) so clicking a card
        // doesn't yank the strip's scroll position.
        el.addEventListener('focusin', (e) => {
            const card = e.target.closest('.sc-tpl-card');
            if (card && !focusedViaPointer) {
                card.scrollIntoView({ block: 'nearest', inline: 'start' });
            }
            focusedViaPointer = false;
        });
    }

    // ── Prev/Next arrow buttons for the template strip ──
    function scrollTemplates(dir) {
        if (!tplGrid) return;
        const step = Math.max(240, tplGrid.clientWidth * 0.7);
        tplGrid.scrollBy({ left: dir * step, behavior: 'smooth' });
    }

    function syncOverflowState(el) {
        if (!el) return;
        const overflows = el.scrollWidth > el.clientWidth + 1;
        el.classList.toggle('has-overflow', overflows);
    }

    function updateTplNavState() {
        if (!tplGrid) return;
        const prev = document.querySelector('.sc-tpl-nav.prev');
        const next = document.querySelector('.sc-tpl-nav.next');
        if (!prev || !next) return;
        const max = tplGrid.scrollWidth - tplGrid.clientWidth;
        const hasOverflow = max > 1;
        syncOverflowState(tplGrid);
        prev.disabled  = !hasOverflow || tplGrid.scrollLeft <= 0;
        next.disabled  = !hasOverflow || tplGrid.scrollLeft >= max - 1;
    }

    document.querySelectorAll('.sc-tpl-nav').forEach(btn => {
        btn.addEventListener('click', () => {
            const dir = btn.dataset.tplDir === 'next' ? 1 : -1;
            scrollTemplates(dir);
        });
    });

    // Re-evaluate arrows on resize (cards wrap width changes)
    window.addEventListener('resize', () => {
        syncOverflowState(tplGrid);
        updateTplNavState();
    });

    // Wheel scroll on template grid and its viewport container
    function handleTplWheel(e) {
        if (!tplGrid) return;
        if (tplGrid.scrollWidth <= tplGrid.clientWidth) return;
        if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
            tplGrid.scrollLeft += e.deltaY * 3;
            updateTplNavState();
            if (e.cancelable) e.preventDefault();
        }
    }
    if (tplGrid) {
        tplGrid.addEventListener('wheel', handleTplWheel, { passive: false });
    }
    const tplViewport = document.querySelector('.sc-tpl-viewport');
    if (tplViewport) {
        tplViewport.addEventListener('wheel', handleTplWheel, { passive: false });
    }

    // Sync template strip when sidebar collapses/expands
    const sidebar = document.getElementById('main-sidebar');
    if (sidebar) {
        sidebar.addEventListener('transitionend', () => {
            syncOverflowState(tplGrid);
            updateTplNavState();
        });
    }
    const collapseBtn = document.getElementById('sidebar-collapse-toggle');
    if (collapseBtn) {
        collapseBtn.addEventListener('click', () => {
            setTimeout(() => {
                syncOverflowState(tplGrid);
                updateTplNavState();
            }, 350);
        });
    }

    window.deployTemplate = async function(card, slug) {
        if (card.classList.contains('deploying') || card.classList.contains('deployed')) return;
        card.classList.add('deploying');
        try {
            const r = await fetch('/api/n8n/templates/deploy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ slug }),
            });
            const d = await r.json();
            card.classList.remove('deploying');
            if (d.success) {
                card.classList.add('deployed');
                showToast(d.existing ? 'Quy trình đã có trong n8n' : 'Triển khai thành công!', true);
                loadWorkflows();
            } else {
                showToast('Lỗi: ' + (d.error || 'Không xác định'), false);
            }
        } catch {
            card.classList.remove('deploying');
            showToast('Không kết nối được n8n', false);
        }
    };

    // ── Refresh ──────────────────────────────────────────
    window.refreshAll = function() {
        checkStatus();
        loadWorkflows();
    };

    // ── Init ─────────────────────────────────────────────
    checkStatus();
    loadWorkflows();
    loadTemplates();
});
