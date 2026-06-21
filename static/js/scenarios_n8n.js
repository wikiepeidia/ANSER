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
                statusTxt.textContent = 'n8n Online';
            } else {
                statusEl.className = 'sc-status offline';
                statusTxt.textContent = 'n8n Offline';
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
                            ${wf.active ? 'Active' : 'Inactive'}
                        </button>
                    </div>
                    <div class="sc-wf-meta">
                        <span class="sc-wf-meta-item"><i class="fas fa-project-diagram"></i> ${wf.nodes} nodes</span>
                        <span class="sc-wf-meta-item"><i class="fas fa-clock"></i> ${timeAgo(wf.updatedAt)}</span>
                        ${wf.tags.length ? wf.tags.map(t => `<span class="sc-wf-meta-item"><i class="fas fa-tag"></i> ${esc(t)}</span>`).join('') : ''}
                    </div>
                    <div class="sc-wf-actions">
                        <button class="sc-wf-btn run" onclick="runWorkflow('${wf.id}', this)">
                            <i class="fas fa-play"></i> Run
                        </button>
                        <button class="sc-wf-btn edit" onclick="openEditor('${wf.id}', '${esc(wf.name)}')">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="sc-wf-btn history" onclick="toggleHistory('${wf.id}', this)">
                            <i class="fas fa-history"></i> History
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
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
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
            try { d = JSON.parse(text); } catch { d = { success: false, error: 'Response không phải JSON: ' + text.substring(0, 100) }; }
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
                showToast(d.active ? 'Đã kích hoạt workflow' : 'Đã tắt workflow', true);
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

        panel.innerHTML = '<div style="padding:8px 0;color:#aaa;font-size:.78rem;"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
        panel.classList.add('open');

        try {
            const r = await fetch(`/api/n8n/workflows/${id}/executions`);
            const d = await r.json();

            if (!d.success || !d.executions.length) {
                panel.innerHTML = '<div class="sc-exec-empty">Chưa có execution nào</div>';
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

    // ── Editor panel ─────────────────────────────────────
    window.openEditor = function(id, name) {
        document.getElementById('editorTitle').textContent = name || 'n8n Editor';
        document.getElementById('editorFrame').src = id ? '/n8n/workflow/' + id : '/n8n/workflows';
        document.getElementById('editorPanel').style.display = 'block';
    };

    window.closeEditor = function() {
        document.getElementById('editorPanel').style.display = 'none';
        document.getElementById('editorFrame').src = '';
        loadWorkflows();
    };

    // ── Delete workflow ─────────────────────────────────
    window.deleteWorkflow = async function(id, name) {
        if (!confirm('Xóa workflow "' + name + '"? Không thể hoàn tác.')) return;
        try {
            const r = await fetch('/api/n8n/workflows/' + id, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrfToken },
            });
            const d = await r.json();
            if (d.success) {
                showToast('Đã xóa workflow', true);
                loadWorkflows();
            } else {
                showToast('Lỗi: ' + (d.error || 'Unknown'), false);
            }
        } catch {
            showToast('Không kết nối được n8n', false);
        }
    };

    // ── Templates ────────────────────────────────────────
    window.toggleTemplates = function() {
        const panel = document.getElementById('tplPanel');
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    };

    async function loadTemplates() {
        try {
            const r = await fetch('/api/n8n/templates');
            const d = await r.json();
            if (!d.success || !d.templates.length) {
                tplGrid.innerHTML = '<div style="color:#aaa;font-size:.85rem;">Không có template</div>';
                return;
            }
            tplGrid.innerHTML = d.templates.map(t => `
                <div class="sc-tpl-card" data-slug="${t.slug}" onclick="deployTemplate(this, '${t.slug}')">
                    <div class="sc-tpl-icon" style="background:${t.color}">
                        <i class="fas ${t.icon}"></i>
                    </div>
                    <div>
                        <div class="sc-tpl-name">${esc(t.label)}</div>
                        <div class="sc-tpl-desc">${esc(t.desc)}</div>
                    </div>
                </div>
            `).join('');
        } catch {
            tplGrid.innerHTML = '<div style="color:#F44336;font-size:.85rem;">Lỗi tải templates</div>';
        }
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
                showToast(d.existing ? 'Workflow đã có trong n8n' : 'Deploy thành công!', true);
                loadWorkflows();
            } else {
                showToast('Lỗi: ' + (d.error || 'Unknown'), false);
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
