/* 
   ORIGINAL UI RESTORED + AI INTEGRATION
   - Uses your exact HTML structure for nodes
   - Includes AI Workflow Loading logic
   - Uses 'var' to prevent browser console crashes
*/

// --- 1. MODULE CATALOG (Original) ---
if (typeof moduleCatalog === 'undefined') {
    var moduleCatalog = [
        { id: 'shopify-new-order', name: 'Shopify - New Order', vendor: 'Shopify', group: 'trigger', color: '#ec4899', icon: 'fas fa-shopping-bag', info: 'Triggered when a new order is created' },
        { id: 'stripe-payment', name: 'Stripe - Payment Succeeded', vendor: 'Stripe', group: 'trigger', color: '#6366f1', icon: 'fas fa-credit-card', info: 'Track successful payments' },
        { id: 'gmail-send', name: 'Gmail - Send Email', vendor: 'Google', group: 'action', color: '#f97316', icon: 'fas fa-envelope', info: 'Send personalized email' },
        { id: 'notion-create', name: 'Notion - Create Record', vendor: 'Notion', group: 'action', color: '#14b8a6', icon: 'fas fa-book', info: 'Create a record in database' },
        { id: 'slack-message', name: 'Slack - Post Message', vendor: 'Slack', group: 'action', color: '#a855f7', icon: 'fab fa-slack-hash', info: 'Notify a channel' },
        { id: 'google-sheets', name: 'Google Sheets', vendor: 'Google', group: 'data', color: '#22d3ee', icon: 'fas fa-table', info: 'Append data to Google Sheet' },
        { id: 'airtable-sync', name: 'Airtable - Sync', vendor: 'Airtable', group: 'data', color: '#f59e0b', icon: 'fas fa-database', info: 'Sync CRM table' },
        // Added Filter/Custom for AI compatibility
        { id: 'filter', name: 'Logic - Filter', vendor: 'System', group: 'logic', color: '#fbbf24', icon: 'fas fa-filter', info: 'Filter data stream' },
        { id: 'custom-module', name: 'Generic Action', vendor: 'System', group: 'action', color: '#64748b', icon: 'fas fa-cogs', info: 'Generic Action' }
    ];
}

if (typeof APP_CONFIG === 'undefined') {
    var APP_CONFIG = window.APP_CONFIG || { projectName: 'Project Store', locale: 'en-US', currency: 'VND' }; 
}

var PROJECT_NAME = APP_CONFIG.projectName || 'Project Store';

// --- 2. STATE VARIABLES ---
var scenarioNodes = (typeof scenarioNodes !== 'undefined') ? scenarioNodes : [];
var scenarioConnections = (typeof scenarioConnections !== 'undefined') ? scenarioConnections : [];
var selectedNodeId = null;
var moduleFilter = 'all';
var runHistory = [];
var canvasScale = 1;
var dragState = { active: false, nodeId: null, offsetX: 0, offsetY: 0 };
var draggedModuleId = null;
var nodeCounter = 0;

// --- 3. INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    initScenarioUI();
    checkAndLoadWorkflow(); // AI Loader
});

function initScenarioUI() {
    if (window.scenarioUIInitialized) return;
    window.scenarioUIInitialized = true;

    renderModuleLibrary();
    renderCanvas();
    renderInspector();
    renderRunHistory();
    
    const surface = document.getElementById('canvasSurface');
    if (surface) {
        surface.addEventListener('dragover', handleCanvasDragOver);
        surface.addEventListener('drop', handleCanvasDrop);
        surface.addEventListener('dragleave', handleCanvasDragLeave);
        surface.addEventListener('mousedown', (e) => {
            if(e.target === surface) { selectedNodeId = null; renderCanvas(); renderInspector(); }
        });
    }
}

// --- 4. AI WORKFLOW LOADER (The Only New Logic) ---
async function checkAndLoadWorkflow() {
    const urlParams = new URLSearchParams(window.location.search);
    const loadId = urlParams.get('load');
    
    if (loadId) {
        try {
            if(typeof showToast === 'function') showToast('Loading workflow from AI...', 'info');
            const res = await fetch(`/api/workflows/${loadId}`);
            const data = await res.json();
            
            if (data.success && data.data) {
                const flow = data.data;
                
                // Map Nodes
                if (flow.nodes) {
                    scenarioNodes = flow.nodes.map((n, index) => ({
                        id: ensureNodeId(n.id),
                        module: mapAiTypeToUiModule(n.type),
                        x: n.position?.x || n.x || (150 + (index * 280)),
                        y: n.position?.y || n.y || 200,
                        config: n.config || {},
                        status: index === 0 ? 'trigger' : 'action'
                    }));
                }

                // Map Connections
                if (flow.edges) {
                    scenarioConnections = flow.edges.map(e => ({
                        from: ensureNodeId(e.from),
                        to: ensureNodeId(e.to)
                    }));
                } else if (flow.connections) {
                    scenarioConnections = flow.connections;
                }

                nodeCounter = scenarioNodes.length;
                renderCanvas();
                if(typeof showToast === 'function') showToast('Workflow loaded successfully!', 'success');
                
                const nameInput = document.querySelector('.workflow-name-input');
                if(nameInput && data.name) nameInput.value = data.name;
            }
        } catch (e) {
            console.error("Load Error:", e);
        }
    }
}

function ensureNodeId(id) {
    const strId = String(id);
    return strId.startsWith('node-') ? strId : `node-${strId}`;
}

function mapAiTypeToUiModule(aiType) {
    if (!aiType) return 'custom-module';
    const t = aiType.toLowerCase();
    if (t.includes('sheet')) return 'google-sheets';
    if (t.includes('mail')) return 'gmail-send';
    if (t.includes('slack')) return 'slack-message';
    if (t.includes('shopify')) return 'shopify-new-order';
    if (t.includes('filter')) return 'filter';
    return 'custom-module';
}

// --- 5. RENDERER (Original UI Structure) ---
function renderCanvas() {
    const surface = document.getElementById('canvasSurface');
    if (!surface) return;

    const maxX = Math.max(1600, ...scenarioNodes.map(node => node.x + 300));
    const maxY = Math.max(900, ...scenarioNodes.map(node => node.y + 200));
    surface.style.width = `${maxX}px`;
    surface.style.height = `${maxY}px`;

    drawConnections();
    
    // Clear old nodes
    surface.querySelectorAll('.scenario-node').forEach(el => el.remove());

    scenarioNodes.forEach(node => {
        const module = moduleCatalog.find(m => m.id === node.module) || { name: node.module, color: '#64748b', icon: 'fas fa-cube', info: 'Action' };
        
        const nodeEl = document.createElement('div');
        nodeEl.className = 'scenario-node';
        if (node.id === selectedNodeId) nodeEl.classList.add('active');
        nodeEl.dataset.nodeId = node.id;
        nodeEl.style.left = `${node.x}px`;
        nodeEl.style.top = `${node.y}px`;

        // --- ORIGINAL HTML STRUCTURE ---
        nodeEl.innerHTML = `
            <div class="node-actions">
                <button type="button" class="node-action-btn" title="Delete module" onclick="event.stopPropagation(); deleteNode('${node.id}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="node-icon" style="background:${module.color}33; color:${module.color};">
                <i class="${module.icon}"></i>
            </div>
            <div class="node-badge">${node.status === 'trigger' ? 'Trigger' : 'Action'}</div>
            <strong class="d-block mt-2">${module.name}</strong>
            <small class="text-muted">${module.info || ''}</small>
        `;

        nodeEl.onclick = () => selectNode(node.id);
        nodeEl.onpointerdown = (event) => startNodeDrag(event, node.id);
        surface.appendChild(nodeEl);
    });

    surface.style.transform = `scale(${canvasScale})`;
    
    // Update clear button
    const clearBtn = document.getElementById('clearCanvasBtn');
    if (clearBtn) clearBtn.disabled = scenarioNodes.length === 0;
}

function drawConnections() {
    const svg = document.getElementById('canvasConnections');
    if (!svg) return;
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
            const control = Math.abs(endX - startX) / 2;
            
            path.setAttribute('d', `M ${startX} ${startY} C ${startX + control} ${startY}, ${endX - control} ${endY}, ${endX} ${endY}`);
            path.setAttribute('stroke', 'rgba(129, 140, 248, 0.8)');
            path.setAttribute('stroke-width', '3');
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke-linecap', 'round');
            svg.appendChild(path);
        }
    });
}

// --- 6. INTERACTION LOGIC (Original) ---
function renderModuleLibrary() {
    const listEl = document.getElementById('moduleLibrary');
    if (!listEl) return;
    
    const searchInput = document.getElementById('moduleSearch');
    const keyword = (searchInput ? searchInput.value : '').toLowerCase();
    
    listEl.innerHTML = '';

    moduleCatalog
        .filter(item => moduleFilter === 'all' || item.group === moduleFilter)
        .filter(item => item.name.toLowerCase().includes(keyword))
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

function deleteNode(nodeId) {
    scenarioNodes = scenarioNodes.filter(n => n.id !== nodeId);
    scenarioConnections = scenarioConnections.filter(c => c.from !== nodeId && c.to !== nodeId);
    renderCanvas();
    renderInspector();
    showToast('Module removed');
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
    
    if (!node) {
        panel.innerHTML = '<p class="text-muted">Select a module to view configuration details.</p>';
        return;
    }
    
    const module = moduleCatalog.find(m => m.id === node.module) || { name: node.module };

    panel.innerHTML = `
        <h5>${module.name}</h5>
        <p class="text-muted">${module.info || ''}</p>
        <div class="mb-3">
            <label class="form-label">Config JSON</label>
            <pre class="bg-dark text-success p-2 rounded" style="font-size:11px; overflow:auto;">${JSON.stringify(node.config, null, 2)}</pre>
        </div>
        <button class="btn btn-danger btn-sm w-100" onclick="deleteNode('${node.id}')">Delete Node</button>
    `;
}

// --- 7. DRAG & DROP ---
function startNodeDrag(event, nodeId) {
    dragState.active = true;
    dragState.nodeId = nodeId;
    const node = scenarioNodes.find(n => n.id === nodeId);
    const rect = document.getElementById('canvasSurface').getBoundingClientRect();
    dragState.offsetX = (event.clientX - rect.left) / canvasScale - node.x;
    dragState.offsetY = (event.clientY - rect.top) / canvasScale - node.y;
    document.addEventListener('mousemove', handleNodeDrag);
    document.addEventListener('mouseup', stopNodeDrag);
}

function handleNodeDrag(event) {
    if (!dragState.active) return;
    const rect = document.getElementById('canvasSurface').getBoundingClientRect();
    const node = scenarioNodes.find(n => n.id === dragState.nodeId);
    node.x = (event.clientX - rect.left) / canvasScale - dragState.offsetX;
    node.y = (event.clientY - rect.top) / canvasScale - dragState.offsetY;
    renderCanvas();
}

function stopNodeDrag() {
    dragState.active = false;
    document.removeEventListener('mousemove', handleNodeDrag);
    document.removeEventListener('mouseup', stopNodeDrag);
}

function handleModuleDragStart(e, id) { draggedModuleId = id; }
function handleModuleDragEnd() { draggedModuleId = null; }
function handleCanvasDragOver(e) { e.preventDefault(); }
function handleCanvasDrop(e) {
    e.preventDefault();
    if (!draggedModuleId) return;
    const rect = document.getElementById('canvasSurface').getBoundingClientRect();
    addModuleToCanvas(draggedModuleId, { 
        x: (e.clientX - rect.left) / canvasScale, 
        y: (e.clientY - rect.top) / canvasScale 
    });
}
function handleCanvasDragLeave(e) {}

// --- 8. BUTTON HANDLERS ---
function runScenarioNow() {
    showToast('Starting workflow execution...', 'info');
    setTimeout(() => {
        runHistory.unshift({ time: new Date().toLocaleTimeString(), status: 'success', duration: '1.2s' });
        renderRunHistory();
        showToast('Workflow completed successfully', 'success');
    }, 1500);
}

function saveScenario() {
    showToast('Scenario saved (draft)', 'success');
}

function clearAllNodes() {
    if (!confirm('Clear canvas?')) return;
    scenarioNodes = [];
    scenarioConnections = [];
    renderCanvas();
    showToast('Canvas cleared', 'info');
}

function renderRunHistory() {
    const list = document.getElementById('runHistoryList');
    if (!list) return;
    list.innerHTML = runHistory.map(run => `<li>${run.time} - ${run.status}</li>`).join('');
}

function showToast(message, type = 'info') {
    // Simple console fallback if toast UI missing
    console.log(`[TOAST] ${message}`);
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : 'info'} alert-dismissible fade show`;
    toast.style.cssText = 'position:fixed; top:20px; right:20px; z-index:9999;';
    toast.innerHTML = `${message} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}