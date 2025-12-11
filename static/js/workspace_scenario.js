// moduleCatalog replaced with English descriptions below
const moduleCatalog = [
    { id: 'shopify-new-order', name: 'Shopify - New Order', vendor: 'Shopify', group: 'trigger', color: '#ec4899', icon: 'fas fa-shopping-bag', info: 'Triggered when a new order is created' },
    { id: 'stripe-payment', name: 'Stripe - Payment Succeeded', vendor: 'Stripe', group: 'trigger', color: '#6366f1', icon: 'fas fa-credit-card', info: 'Track successful payments' },
    { id: 'gmail-send', name: 'Gmail - Send Email', vendor: 'Google', group: 'action', color: '#f97316', icon: 'fas fa-envelope', info: 'Send personalized email' },
    { id: 'notion-create', name: 'Notion - Create Record', vendor: 'Notion', group: 'action', color: '#14b8a6', icon: 'fas fa-book', info: 'Create a record in database' },
    { id: 'slack-message', name: 'Slack - Post Message', vendor: 'Slack', group: 'action', color: '#a855f7', icon: 'fab fa-slack-hash', info: 'Notify a channel' },
    { id: 'google-sheets', name: 'Google Sheets - Append Row', vendor: 'Google', group: 'data', color: '#22d3ee', icon: 'fas fa-table', info: 'Append data to Google Sheet' },
    { id: 'airtable-sync', name: 'Airtable - Sync', vendor: 'Airtable', group: 'data', color: '#f59e0b', icon: 'fas fa-database', info: 'Sync CRM table' }
];

const APP_CONFIG = window.APP_CONFIG || { projectName: (document.body && document.body.dataset && document.body.dataset.projectName) || 'Project Store', locale: 'en-US', currency: 'VND' };
const PROJECT_NAME = APP_CONFIG.projectName || 'Project Store';

let scenarioNodes = [
    { id: 'node-1', module: 'shopify-new-order', x: 140, y: 180, status: 'trigger', config: { store: PROJECT_NAME, events: ['paid'] } },
    { id: 'node-2', module: 'google-sheets', x: 420, y: 80, status: 'action', config: { sheet: 'CRM Orders' } },
    { id: 'node-3', module: 'notion-create', x: 700, y: 220, status: 'action', config: { database: 'VIP Customers' } },
    { id: 'node-4', module: 'slack-message', x: 980, y: 160, status: 'action', config: { channel: '#sales-alerts' } }
];

let scenarioConnections = [
    { from: 'node-1', to: 'node-2' },
    { from: 'node-2', to: 'node-3' },
    { from: 'node-3', to: 'node-4' }
];

let selectedNodeId = null;
let moduleFilter = 'all';
let runHistory = [];
let canvasScale = 1;
const dragState = { active: false, nodeId: null, offsetX: 0, offsetY: 0 };
let draggedModuleId = null;
let nodeCounter = scenarioNodes.length;

function initScenarioUI() {
    renderModuleLibrary();
    renderCanvas();
    renderInspector();
    renderRunHistory();
    const surface = document.getElementById('canvasSurface');
    if (surface) {
        surface.addEventListener('dragover', handleCanvasDragOver);
        surface.addEventListener('drop', handleCanvasDrop);
        surface.addEventListener('dragleave', handleCanvasDragLeave);
    }
}

function renderModuleLibrary() {
    const listEl = document.getElementById('moduleLibrary');
    if (!listEl) return;
    const keyword = (document.getElementById('moduleSearch')?.value || '').toLowerCase();
    listEl.innerHTML = '';

    moduleCatalog
        .filter(item => moduleFilter === 'all' || item.group === moduleFilter)
        .filter(item => item.name.toLowerCase().includes(keyword) || item.vendor.toLowerCase().includes(keyword))
        .forEach(item => {
            const div = document.createElement('div');
            div.className = 'module-item';
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6>${item.name}</h6>
                        <small>${item.vendor}</small>
                    </div>
                    <span class="node-badge" style="background:${item.color}33; color:${item.color};">${item.group}</span>
                </div>
                <p class="small text-muted mb-0">${item.info}</p>
            `;
            div.onclick = () => addModuleToCanvas(item.id);
            div.draggable = true;
            div.addEventListener('dragstart', (event) => handleModuleDragStart(event, item.id));
            div.addEventListener('dragend', handleModuleDragEnd);
            listEl.appendChild(div);
        });
}

function switchModuleGroup(event, group) {
    moduleFilter = group;
    document.querySelectorAll('.module-group').forEach(btn => btn.classList.remove('active'));
    event.currentTarget.classList.add('active');
    renderModuleLibrary();
}

function addModuleToCanvas(moduleId, options = {}) {
    const module = moduleCatalog.find(m => m.id === moduleId);
    if (!module) return;
    const lastNode = scenarioNodes[scenarioNodes.length - 1];
    const newNode = {
        id: `node-${++nodeCounter}`,
        module: module.id,
        x: typeof options.x === 'number' ? options.x : (lastNode?.x || 120) + 260,
        y: typeof options.y === 'number' ? options.y : ((scenarioNodes.length % 2 === 0) ? 200 : 80),
        status: 'action',
        config: { note: 'Not configured' }
    };
    scenarioNodes.push(newNode);
    const connectFrom = options.connectFromId ? scenarioNodes.find(n => n.id === options.connectFromId) : (lastNode || null);
    if (connectFrom) {
        scenarioConnections.push({ from: connectFrom.id, to: newNode.id });
    }
    selectedNodeId = newNode.id;
    renderCanvas();
    renderInspector();
    showToast(`${module.name} was added to the scenario`);
}

function handleModuleDragStart(event, moduleId) {
    draggedModuleId = moduleId;
    event.dataTransfer?.setData('text/plain', moduleId);
    event.dataTransfer?.setDragImage(new Image(), 0, 0);
    document.getElementById('scenarioCanvas')?.classList.add('dragging-module');
}

function handleModuleDragEnd() {
    draggedModuleId = null;
    document.getElementById('scenarioCanvas')?.classList.remove('dragging-module');
}

function handleCanvasDragOver(event) {
    if (!draggedModuleId) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
}

function handleCanvasDragLeave(event) {
    if (event.currentTarget?.contains(event.relatedTarget)) return;
    document.getElementById('scenarioCanvas')?.classList.remove('dragging-module');
}

function handleCanvasDrop(event) {
    if (!draggedModuleId) return;
    event.preventDefault();
    const surface = document.getElementById('canvasSurface');
    if (!surface) return;
    const rect = surface.getBoundingClientRect();
    const dropX = (event.clientX - rect.left) / canvasScale;
    const dropY = (event.clientY - rect.top) / canvasScale;
    addModuleToCanvas(draggedModuleId, {
        x: dropX - 95,
        y: dropY - 70,
        connectFromId: selectedNodeId || scenarioNodes[scenarioNodes.length - 1]?.id
    });
    handleModuleDragEnd();
}

function deleteNode(nodeId) {
    const index = scenarioNodes.findIndex(n => n.id === nodeId);
    if (index === -1) return;
    scenarioNodes.splice(index, 1);
    scenarioConnections = scenarioConnections.filter(conn => conn.from !== nodeId && conn.to !== nodeId);
    if (selectedNodeId === nodeId) {
        selectedNodeId = scenarioNodes[scenarioNodes.length - 1]?.id || null;
    }
    renderCanvas();
    renderInspector();
    showToast('Module removed from canvas', 'info');
}

function clearAllNodes() {
    if (!scenarioNodes.length) {
        showToast('Canvas is empty', 'info');
        return;
    }
    if (!confirm('Are you sure you want to delete all modules?')) return;
    scenarioNodes = [];
    scenarioConnections = [];
    selectedNodeId = null;
    nodeCounter = 0;
    renderCanvas();
    renderInspector();
    showToast('All modules removed from canvas', 'info');
}

function drawConnections() {
    const surface = document.getElementById('canvasSurface');
    const svg = document.getElementById('canvasConnections');
    if (!surface || !svg) return;

    const width = parseFloat(surface.style.width) || surface.clientWidth;
    const height = parseFloat(surface.style.height) || surface.clientHeight;
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.innerHTML = '';

    scenarioConnections.forEach(conn => {
        const from = scenarioNodes.find(n => n.id === conn.from);
        const to = scenarioNodes.find(n => n.id === conn.to);
        if (from && to) {
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            const startX = from.x + 190;
            const startY = from.y + 60;
            const endX = to.x;
            const endY = to.y + 50;
            const control = (endX - startX) / 2;
            path.setAttribute('d', `M ${startX} ${startY} C ${startX + control} ${startY}, ${endX - control} ${endY}, ${endX} ${endY}`);
            path.setAttribute('stroke', 'rgba(129, 140, 248, 0.8)');
            path.setAttribute('stroke-width', '3');
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke-linecap', 'round');
            svg.appendChild(path);
        }
    });
}

function renderCanvas() {
    const canvas = document.getElementById('scenarioCanvas');
    const surface = document.getElementById('canvasSurface');
    if (!canvas || !surface) return;

    const maxX = Math.max(0, ...scenarioNodes.map(node => node.x + 260));
    const maxY = Math.max(0, ...scenarioNodes.map(node => node.y + 180));
    surface.style.width = `${Math.max(1600, maxX)}px`;
    surface.style.height = `${Math.max(900, maxY)}px`;

    drawConnections();
    surface.querySelectorAll('.scenario-node').forEach(el => el.remove());

    scenarioNodes.forEach(node => {
        const module = moduleCatalog.find(m => m.id === node.module);
        const nodeEl = document.createElement('div');
        nodeEl.className = 'scenario-node';
        if (node.id === selectedNodeId) nodeEl.classList.add('active');
        nodeEl.dataset.nodeId = node.id;
        nodeEl.style.left = `${node.x}px`;
        nodeEl.style.top = `${node.y}px`;

        nodeEl.innerHTML = `
            <div class="node-actions">
                <button type="button" class="node-action-btn" title="Delete module" onclick="event.stopPropagation(); deleteNode('${node.id}')">
                        showToast('Module removed from canvas', 'info');
                        showToast('Canvas is empty', 'info');
                        if (!confirm('Are you sure you want to delete all modules?')) return;
                        showToast('All modules removed from canvas', 'info');
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="node-icon" style="background:${module?.color || '#64748b'}33; color:${module?.color || '#cbd5ff'};">
                <i class="${module?.icon || 'fas fa-cube'}"></i>
            </div>
            <div class="node-badge">${node.status === 'trigger' ? 'Trigger' : 'Action'}</div>
            <strong class="d-block mt-2">${module?.name || 'Module'}</strong>
            <small class="text-muted">${module?.info || ''}</small>
        `;

        nodeEl.onclick = () => selectNode(node.id);
        nodeEl.onpointerdown = (event) => startNodeDrag(event, node.id);
        surface.appendChild(nodeEl);
    });

    surface.style.transform = `scale(${canvasScale})`;

    const clearBtn = document.getElementById('clearCanvasBtn');
    if (clearBtn) {
        clearBtn.disabled = scenarioNodes.length === 0;
    }
}

function startNodeDrag(event, nodeId) {
    const surface = document.getElementById('canvasSurface');
    const node = scenarioNodes.find(n => n.id === nodeId);
    if (!surface || !node) return;
    event.preventDefault();
    const rect = surface.getBoundingClientRect();
    const pointerX = (event.clientX - rect.left) / canvasScale;
    const pointerY = (event.clientY - rect.top) / canvasScale;
    dragState.active = true;
    dragState.nodeId = nodeId;
    dragState.offsetX = pointerX - node.x;
    dragState.offsetY = pointerY - node.y;
    document.addEventListener('pointermove', handleNodeDrag);
    document.addEventListener('pointerup', stopNodeDrag);
}

function handleNodeDrag(event) {
    if (!dragState.active) return;
    const surface = document.getElementById('canvasSurface');
    const node = scenarioNodes.find(n => n.id === dragState.nodeId);
    if (!surface || !node) return;
    const rect = surface.getBoundingClientRect();
    const pointerX = (event.clientX - rect.left) / canvasScale;
    const pointerY = (event.clientY - rect.top) / canvasScale;
    node.x = pointerX - dragState.offsetX;
    node.y = pointerY - dragState.offsetY;
    clampNodeWithinCanvas(node, surface);
    updateNodeDomPosition(node);
    drawConnections();
}

function stopNodeDrag() {
    dragState.active = false;
    dragState.nodeId = null;
    document.removeEventListener('pointermove', handleNodeDrag);
    document.removeEventListener('pointerup', stopNodeDrag);
}

function clampNodeWithinCanvas(node, surface) {
    const width = parseFloat(surface.style.width) || surface.clientWidth;
    const height = parseFloat(surface.style.height) || surface.clientHeight;
    const maxX = width - 220;
    const maxY = height - 160;
    node.x = Math.max(20, Math.min(node.x, maxX));
    node.y = Math.max(20, Math.min(node.y, maxY));
}

function updateNodeDomPosition(node) {
    const nodeEl = document.querySelector(`.scenario-node[data-node-id="${node.id}"]`);
    if (nodeEl) {
        nodeEl.style.left = `${node.x}px`;
        nodeEl.style.top = `${node.y}px`;
    }
}

function selectNode(nodeId) {
    selectedNodeId = nodeId;
    renderCanvas();
    renderInspector();
}

function renderInspector(tab = 'properties') {
    const panel = document.getElementById('inspectorContent');
    if (!panel) return;
    const node = scenarioNodes.find(n => n.id === selectedNodeId);
    const module = moduleCatalog.find(m => m.id === node?.module);

    if (!node) {
        panel.innerHTML = '<p class="text-muted">Select a module to view configuration details.</p>';
            panel.innerHTML = '<p class="text-muted">Select a module to view configuration details.</p>';
        return;
    }

    if (tab === 'properties') {
        panel.innerHTML = `
            <h5>${module?.name}</h5>
            <p class="text-muted">${module?.info}</p>
            <div class="mb-3">
                <label class="form-label">Display name</label>
                            <label class="form-label">Display name</label>
                <input type="text" class="form-control form-control-sm" value="${module?.name}" readonly>
            </div>
            <div class="mb-3">
                <label class="form-label">Config note</label>
                            <label class="form-label">Config note</label>
                <textarea class="form-control" rows="4" onchange="updateNodeNote('${node.id}', this.value)">${node.config?.note || ''}</textarea>
            </div>
            <div class="mb-3">
                <label class="form-label">Conditions</label>
                            <label class="form-label">Conditions</label>
                <select class="form-select form-select-sm">
                    <option>Run everytime</option>
                    <option>Only if payment > 5M</option>
                </select>
            </div>
        `;
    } else if (tab === 'output') {
        panel.innerHTML = `
            <h5>Output preview</h5>
            <pre class="bg-dark text-success p-3 rounded">${JSON.stringify(node.config, null, 2)}</pre>
        `;
    } else {
        panel.innerHTML = `
            <h5>Versions</h5>
            <ul class="list-unstyled small">
                <li>v1.4-draft · 2 minutes ago · You</li>
                <li>v1.3 · 1 ngày trước · Jenny</li>
            </ul>
        `;
    }
}

function switchInspectorTab(event, tab) {
    document.querySelectorAll('.inspector-tab').forEach(btn => btn.classList.remove('active'));
    event.currentTarget.classList.add('active');
    renderInspector(tab);
}

function updateNodeNote(nodeId, note) {
    const node = scenarioNodes.find(n => n.id === nodeId);
    if (node) node.config.note = note;
}

function renderRunHistory() {
    const list = document.getElementById('runHistoryList');
    const badge = document.getElementById('runCounter');
    if (!list || !badge) return;
    badge.textContent = `${runHistory.length} runs`;
    if (!runHistory.length) {
        list.innerHTML = '<li class="text-muted">No runs yet</li>';
        return;
    }
    list.innerHTML = runHistory.map(run => `
        <li>
            <span>${run.time}</span>
            <span class="text-${run.status === 'success' ? 'success' : 'danger'}">${run.status}</span>
            <span>${run.duration}</span>
        </li>
    `).join('');
}

function runScenarioNow() {
    const start = new Date();
    logToConsole('[INFO] Starting manual run...');
    scenarioNodes.forEach((node, idx) => {
        logToConsole(`[STEP ${idx + 1}] ${node.id} executing... ok`);
    });
    const end = new Date();
    const duration = ((end - start) / 1000).toFixed(2) + 's';
    logToConsole(`[DONE] Scenario completed in ${duration}`);
    const stamp = start.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    runHistory.unshift({ time: stamp, status: 'success', duration });
    document.getElementById('lastRunTime').textContent = stamp;
    document.getElementById('dataProcessed').textContent = `${Math.floor(Math.random() * 50) + 12} records`;
    renderRunHistory();
    showToast('Scenario run successful', 'success');
}

function logToConsole(message) {
    const consoleEl = document.getElementById('consoleOutput');
    if (!consoleEl) return;
    consoleEl.textContent += `\n${message}`;
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

function clearConsole() {
    document.getElementById('consoleOutput').textContent = 'Ready. Waiting for run...';
}

function saveScenario() {
    showToast('Scenario saved (draft)', 'success');
}

function duplicateScenario() {
    showToast('Duplicated scenario: CRM Sync (copy)', 'info');
}

function scheduleScenario() {
    showToast('Scheduler opened — choose a desired schedule', 'info');
}

function requestIntegration() {
    showToast('Integration request received', 'info');
}

function zoomCanvas(direction) {
    if (direction === 'in') canvasScale = Math.min(canvasScale + 0.1, 1.5);
    else if (direction === 'out') canvasScale = Math.max(canvasScale - 0.1, 0.6);
    else canvasScale = 1;
    renderCanvas();
}

function filterModules() {
    renderModuleLibrary();
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : 'info'} alert-dismissible fade show scenario-toast`;
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '30px';
    toast.style.zIndex = '2000';
    toast.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function openScrapingScenario() {
    document.getElementById('scenarioTop')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    showToast('Đang mở workflow Scraping + CRM Sync', 'info');
}

document.addEventListener('DOMContentLoaded', initScenarioUI);
