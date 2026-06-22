document.addEventListener('DOMContentLoaded', () => {
    const REFRESH_INTERVAL = 30_000;

    let currentOffset = 0;
    let currentTotal  = 0;
    let currentLimit  = 50;
    let refreshTimer  = null;

    const elTotal       = document.getElementById('statTotal');
    const elRevenue     = document.getElementById('statRevenue');
    const elDevices     = document.getElementById('statDevices');
    const elToday       = document.getElementById('statToday');
    const eventsBody    = document.getElementById('eventsBody');
    const eventsTable   = document.getElementById('eventsTable');
    const loadingRow    = document.getElementById('loadingRow');
    const emptyRow      = document.getElementById('emptyRow');
    const filterDevice  = document.getElementById('filterDevice');
    const filterType    = document.getElementById('filterEventType');
    const filterLimit   = document.getElementById('filterLimit');
    const applyBtn      = document.getElementById('applyFilter');
    const refreshBtn    = document.getElementById('refreshBtn');
    const pagination    = document.getElementById('pagination');

    function fmt(n) {
        return new Intl.NumberFormat('vi-VN').format(Math.round(n)) + ' ₫';
    }

    function badgeClass(type) {
        if (['sale_completed', 'payment_received'].includes(type)) return 'sale';
        if (type === 'cash_low') return 'cash';
        if (type === 'invoice') return 'invoice';
        return 'default';
    }

    function fmtDate(iso) {
        if (!iso) return '—';
        const d = new Date(iso);
        return d.toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'medium' });
    }

    async function loadStats() {
        try {
            const res  = await fetch('/api/iot-events/stats');
            const data = await res.json();
            if (!data.success) return;
            const s = data.summary;
            elTotal.textContent   = s.total_events.toLocaleString('vi-VN');
            elRevenue.textContent = fmt(s.total_revenue);
            elDevices.textContent = s.device_count;
            elToday.textContent   = s.today_events.toLocaleString('vi-VN');

            // Populate device filter
            const current = filterDevice.value;
            filterDevice.innerHTML = '<option value="">Tất cả thiết bị</option>';
            data.by_device.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.device_id;
                opt.textContent = `${d.device_id} (${d.count})`;
                filterDevice.appendChild(opt);
            });
            if (current) filterDevice.value = current;
        } catch (_) {}
    }

    async function loadEvents(offset = 0) {
        loadingRow.style.display = 'block';
        eventsTable.style.display = 'none';
        emptyRow.style.display = 'none';

        const device = filterDevice.value;
        const type   = filterType.value;
        const limit  = parseInt(filterLimit.value) || 50;
        currentLimit = limit;

        const params = new URLSearchParams({ limit, offset });
        if (device) params.set('device_id', device);
        if (type)   params.set('event_type', type);

        try {
            const res  = await fetch('/api/iot-events?' + params);
            const data = await res.json();
            loadingRow.style.display = 'none';

            if (!data.success || !data.events?.length) {
                emptyRow.style.display = 'block';
                return;
            }

            currentTotal  = data.total;
            currentOffset = offset;

            eventsBody.innerHTML = data.events.map(ev => {
                const amount = ev.payload?.amount ? fmt(ev.payload.amount) : '—';
                const payloadStr = JSON.stringify(ev.payload || {});
                return `<tr>
                    <td><span style="font-weight:600; color:#FF6B35;">#${ev.id}</span></td>
                    <td>${ev.device_id}</td>
                    <td><span class="iot-badge ${badgeClass(ev.event_type)}">${ev.event_type}</span></td>
                    <td>${amount}</td>
                    <td><div class="iot-payload" title="${payloadStr.replace(/"/g, '&quot;')}">${payloadStr}</div></td>
                    <td>${fmtDate(ev.created_at)}</td>
                </tr>`;
            }).join('');

            eventsTable.style.display = 'table';
            renderPagination();
        } catch (e) {
            loadingRow.style.display = 'none';
            emptyRow.style.display = 'block';
        }
    }

    function renderPagination() {
        const totalPages = Math.ceil(currentTotal / currentLimit);
        const curPage    = Math.floor(currentOffset / currentLimit);
        if (totalPages <= 1) { pagination.innerHTML = ''; return; }

        let html = '';
        if (curPage > 0) {
            html += `<button class="iot-page-btn" data-page="${curPage - 1}">&#8249; Trước</button>`;
        }
        for (let i = 0; i < totalPages; i++) {
            html += `<button class="iot-page-btn ${i === curPage ? 'active' : ''}" data-page="${i}">${i + 1}</button>`;
        }
        if (curPage < totalPages - 1) {
            html += `<button class="iot-page-btn" data-page="${curPage + 1}">Tiếp &#8250;</button>`;
        }
        pagination.innerHTML = html;
        pagination.querySelectorAll('.iot-page-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = parseInt(btn.dataset.page);
                loadEvents(page * currentLimit);
            });
        });
    }

    function startAutoRefresh() {
        clearInterval(refreshTimer);
        refreshTimer = setInterval(() => {
            loadStats();
            loadEvents(currentOffset);
        }, REFRESH_INTERVAL);
    }

    applyBtn.addEventListener('click', () => loadEvents(0));
    refreshBtn.addEventListener('click', () => { loadStats(); loadEvents(0); });

    loadStats();
    loadEvents(0);
    startAutoRefresh();
});
