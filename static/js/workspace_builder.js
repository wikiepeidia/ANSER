document.addEventListener('DOMContentLoaded', () => {
    const toolSearch = document.getElementById('toolSearch');
    const toolItems = Array.from(document.querySelectorAll('.tool-item'));
    const propertyPanel = document.getElementById('propertyPanel');
    const selectedNodeTitle = document.getElementById('selectedNodeTitle');
    const closePropertyPanel = document.getElementById('closePropertyPanel');
    const nodeNameInput = document.getElementById('nodeName');
    const nodeDescriptionInput = document.getElementById('nodeDescription');
    const canvas = document.getElementById('workflowCanvas');
    const dropZone = document.getElementById('dropZone');
    const builderState = {
        nodeCounter: 0,
        selectedNode: null,
        history: [],
        redo: [],
        connections: []
    };
    const categoryColors = {
        trigger: '#8bc34a',
        ai: '#00bcd4',
        logic: '#ff9800',
        integration: '#9c27b0',
        custom: '#667eea'
    };

    // Notification function for workspace builder
    // Uses global showNotification from script.js


    function pushHistory(action) {
        builderState.history.push(action);
        builderState.redo = [];
    }

    function undo() {
        const last = builderState.history.pop();
        if (!last) return;
        builderState.redo.push(last);
        switch (last.type) {
            case 'create': {
                const created = document.querySelector(`.workflow-node[data-node-id="${last.nodeId}"]`);
                if (created) created.remove();
                break;
            }
            case 'delete': {
                if (!canvas) {
                    showNotification('Canvas not available for undo', 'error');
                    return;
                }
                const wrap = document.createElement('div');
                wrap.innerHTML = last.snapshot;
                const restored = wrap.firstElementChild;
                canvas.appendChild(restored);
                attachNodeInteractions(restored);
                break;
            }
            case 'move': {
                const moved = document.querySelector(`.workflow-node[data-node-id="${last.nodeId}"]`);
                if (moved) {
                    moved.style.left = `${last.from.left}px`;
                    moved.style.top = `${last.from.top}px`;
                }
                break;
            }
            case 'edit': {
                const edited = document.querySelector(`.workflow-node[data-node-id="${last.nodeId}"]`);
                if (edited) {
                    edited.dataset.title = last.from.title;
                    edited.querySelector('.node-title').textContent = last.from.title;
                    edited.querySelector('.node-content').textContent = last.from.description;
                }
                if (builderState.selectedNode && builderState.selectedNode.dataset.nodeId === last.nodeId) {
                    nodeNameInput.value = last.from.title;
                    nodeDescriptionInput.value = last.from.description;
                }
                break;
            }
            case 'connect': {
                const svg = document.getElementById('connectionLines');
                const toRemove = [...svg.querySelectorAll('.connection-line')].find((line) => line.dataset.source === last.source && line.dataset.target === last.target);
                if (toRemove) toRemove.remove();
                builderState.connections = builderState.connections.filter((c) => !(c.source === last.source && c.target === last.target));
                break;
            }
            default:
                break;
        }
    }

    if (toolSearch) {
        toolSearch.addEventListener('input', (event) => {
            const term = event.target.value.toLowerCase();
            toolItems.forEach((item) => {
                const matches = item.textContent.toLowerCase().includes(term);
                item.style.display = matches ? 'flex' : 'none';
            });
        });
    }

    function serializeTool(tool) {
        return {
            name: tool.querySelector('.tool-name')?.textContent.trim() || 'Custom block',
            description: tool.querySelector('.tool-description')?.textContent.trim() || 'Describe this step...',
            icon: tool.querySelector('.tool-icon i')?.className || 'fas fa-puzzle-piece',
            category: tool.dataset.category || 'custom',
            type: tool.dataset.type || 'custom'
        };
    }

    function getCategoryColor(category) {
        return categoryColors[category] || categoryColors.custom;
    }

    function updateDropZoneVisibility() {
        if (!dropZone || !canvas) {
            return;
        }
        const hasNodes = canvas.querySelectorAll('.workflow-node').length > 0;
        dropZone.style.display = hasNodes ? 'none' : 'flex';
    }

    function attachNodeInteractions(node) {
        if (!node) {
            return;
        }

        const menuBtn = node.querySelector('.node-menu');
        if (menuBtn) {
            menuBtn.addEventListener('click', (event) => {
                event.stopPropagation();
                showNodeMenu(node);
            });
        }

        node.addEventListener('click', (event) => {
            if (event.target.closest('.node-menu')) {
                return;
            }
            selectNode(node);
        });

        // Attach click handlers to connection points so connect mode acts on the exact point
        const connectionPoints = node.querySelectorAll('.connection-point');
        if (connectionPoints && connectionPoints.length) {
            connectionPoints.forEach((cp) => {
                cp.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    handleConnectionMode(node, cp);
                });
            });
        }

        enableNodeDragging(node);
    }

    function showNodeMenu(node) {
        document.querySelectorAll('.node-context-menu').forEach((menu) => menu.remove());

        const menu = document.createElement('div');
        menu.className = 'node-context-menu';
        menu.innerHTML = `
            <div class="context-menu-item" data-action="edit">
                <i class="fas fa-edit"></i> Edit
            </div>
            <div class="context-menu-item" data-action="duplicate">
                <i class="fas fa-copy"></i> Duplicate
            </div>
            <div class="context-menu-item" data-action="delete">
                <i class="fas fa-trash"></i> Delete
            </div>
        `;

        document.body.appendChild(menu);

        const nodeRect = node.getBoundingClientRect();
        menu.style.top = `${nodeRect.top + 10}px`;
        menu.style.left = `${nodeRect.right + 10}px`;

        menu.querySelectorAll('.context-menu-item').forEach((item) => {
            item.addEventListener('click', function () {
                const action = this.dataset.action;
                handleNodeAction(node, action);
                menu.remove();
            });
        });

        setTimeout(() => {
            document.addEventListener('click', function closeMenu(event) {
                if (!menu.contains(event.target)) {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 10);
    }

    function handleNodeAction(node, action) {
        switch (action) {
            case 'edit':
                selectNode(node);
                showNotification('Edit mode activated', 'info');
                break;
            case 'duplicate': {
                const clone = node.cloneNode(true);
                clone.style.left = `${parseInt(node.style.left, 10) + 30}px`;
                clone.style.top = `${parseInt(node.style.top, 10) + 30}px`;
                if (canvas) {
                    canvas.appendChild(clone);
                    attachNodeInteractions(clone);
                    showNotification('Node duplicated', 'success');
                } else {
                    showNotification('Canvas not found', 'error');
                }
                break;
            }
            case 'delete':
                if (confirm('Delete this node?')) {
                    const nodeId = node.dataset.nodeId;
                    const snapshot = node.outerHTML;
                    node.remove();
                    pushHistory({ type: 'delete', nodeId, snapshot });
                    showNotification('Node deleted', 'success');
                    if (builderState.selectedNode === node) {
                        builderState.selectedNode = null;
                        if (propertyPanel) propertyPanel.classList.remove('open');
                    }
                }
                break;
            default:
                break;
        }
    }

    function enableNodeDragging(node) {
        const handle = node.querySelector('.node-header');
        if (!handle || !canvas) {
            return;
        }

        handle.addEventListener('mousedown', (event) => {
            if (event.button !== 0) {
                return;
            }
            event.preventDefault();
            const canvasRect = canvas.getBoundingClientRect();
            const nodeRect = node.getBoundingClientRect();
            const offsetX = event.clientX - nodeRect.left;
            const offsetY = event.clientY - nodeRect.top;
            const startLeft = parseInt(node.style.left, 10) || 0;
            const startTop = parseInt(node.style.top, 10) || 0;

            node.classList.add('dragging');

            function onMouseMove(moveEvent) {
                const currentCanvasRect = canvas.getBoundingClientRect();
                const newLeft = moveEvent.clientX - currentCanvasRect.left - offsetX;
                const newTop = moveEvent.clientY - currentCanvasRect.top - offsetY;
                node.style.left = `${Math.max(0, newLeft)}px`;
                node.style.top = `${Math.max(0, newTop)}px`;
                
                // Update connections while dragging
                updateNodeConnections(node);
            }

            function onMouseUp() {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
                node.classList.remove('dragging');
                const endLeft = parseInt(node.style.left, 10) || 0;
                const endTop = parseInt(node.style.top, 10) || 0;
                if (startLeft !== endLeft || startTop !== endTop) {
                    pushHistory({ type: 'move', nodeId: node.dataset.nodeId, from: { left: startLeft, top: startTop }, to: { left: endLeft, top: endTop } });
                }
            }

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }

    function bindPropertyInputs() {
        if (nodeNameInput) {
            nodeNameInput.addEventListener('input', (event) => {
                if (!builderState.selectedNode) {
                    return;
                }
                const value = event.target.value || 'Untitled block';
                const titleEl = builderState.selectedNode.querySelector('.node-title');
                if (titleEl) {
                    titleEl.textContent = value;
                }
                builderState.selectedNode.dataset.title = value;
                if (selectedNodeTitle) {
                    selectedNodeTitle.textContent = value;
                }
            });
        }

        if (nodeDescriptionInput) {
            nodeDescriptionInput.addEventListener('input', (event) => {
                if (!builderState.selectedNode) {
                    return;
                }
                const value = event.target.value || 'Describe this step...';
                const contentEl = builderState.selectedNode.querySelector('.node-content');
                if (contentEl) {
                    contentEl.textContent = value;
                }
            });
        }
    }

    function createWorkflowNode(toolData, position) {
        if (!canvas) {
            return null;
        }

        // Reset connection state if we were in the middle of connecting
        if (builderMode.current === 'connect' && builderMode.connectionStart) {
            resetConnectionState();
            showNotification('Connection cancelled due to new node', 'info');
        }

        const node = document.createElement('div');
        node.className = 'workflow-node';
        node.dataset.title = toolData.name;
        node.dataset.category = toolData.category;
        node.dataset.type = toolData.type;
        node.dataset.config = JSON.stringify({}); // Init empty config
        node.style.top = `${position.y - 40}px`;
        node.style.left = `${position.x - 100}px`;
        node.style.position = 'absolute';

        node.innerHTML = `
            <div class="node-header">
                <div class="node-icon" style="background: ${getCategoryColor(toolData.category)};">
                    <i class="${toolData.icon}"></i>
                </div>
                <div class="node-title">${toolData.name}</div>
                <div class="node-menu">
                    <i class="fas fa-ellipsis-h"></i>
                </div>
            </div>
            <div class="node-content">${toolData.description}</div>
            <div class="node-connections">
                <div class="connection-point input"></div>
                <div class="connection-point output"></div>
            </div>
        `;

        builderState.nodeCounter += 1;
        node.dataset.nodeId = `node-${builderState.nodeCounter}`;
        canvas.appendChild(node);
        attachNodeInteractions(node);
        pushHistory({ type: 'create', nodeId: node.dataset.nodeId });
        updateDropZoneVisibility();
        selectNode(node);
        return node;
    }

    function handleDrop(event) {
        event.preventDefault();
        if (!canvas) {
            return;
        }

        const payload = event.dataTransfer.getData('application/json');
        if (!payload) {
            return;
        }
        const toolData = JSON.parse(payload);
        const canvasRect = canvas.getBoundingClientRect();
        const position = {
            x: event.clientX - canvasRect.left,
            y: event.clientY - canvasRect.top
        };
        createWorkflowNode(toolData, position);
    }

    if (canvas) {
        canvas.addEventListener('dragover', (event) => {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'copy';
        });
        canvas.addEventListener('drop', handleDrop);
    }

    if (dropZone) {
        dropZone.addEventListener('dragover', (event) => {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'copy';
        });
        dropZone.addEventListener('drop', handleDrop);
    }

    toolItems.forEach((tool) => {
        tool.addEventListener('dragstart', (event) => {
            const payload = serializeTool(tool);
            event.dataTransfer.setData('application/json', JSON.stringify(payload));
            event.dataTransfer.effectAllowed = 'copy';
            canvas?.classList.add('drag-active');
        });

        tool.addEventListener('dragend', () => {
            canvas?.classList.remove('drag-active');
        });
    });

    if (closePropertyPanel && propertyPanel) {
        closePropertyPanel.addEventListener('click', () => {
            propertyPanel.classList.remove('open');
            if (builderState.selectedNode) {
                builderState.selectedNode.classList.remove('selected');
                builderState.selectedNode = null;
            }
        });
    }

    const builderMode = {
        current: 'cursor',
        scale: 1.0,
        isConnecting: false,
        connectionStart: null
    };

    document.querySelectorAll('.toolbar-btn').forEach((btn) => {
        btn.setAttribute('role', 'button');
        btn.setAttribute('aria-pressed', 'false');
        btn.addEventListener('click', function () {
            const action = this.dataset.action;
            document.querySelectorAll('.toolbar-btn').forEach((item) => {
                item.classList.remove('active');
                item.setAttribute('aria-pressed', 'false');
            });
            this.classList.add('active');
            this.setAttribute('aria-pressed', 'true');
            builderMode.current = action;

            if (action === 'cursor') {
                if (canvas) {
                    canvas.classList.remove('connect-mode', 'zoom-mode');
                    canvas.classList.add('cursor-mode');
                }
                builderMode.isConnecting = false;
                resetConnectionState();
                showNotification('Select mode activated - Click nodes to select and edit', 'info');
            } else if (action === 'connect') {
                if (canvas) {
                    canvas.classList.remove('cursor-mode', 'zoom-mode');
                    canvas.classList.add('connect-mode');
                }
                builderMode.isConnecting = true;
                showNotification('Connect mode activated - Click nodes to connect them', 'info');
            } else if (action === 'zoom') {
                if (canvas) {
                    canvas.classList.remove('cursor-mode', 'connect-mode');
                    canvas.classList.add('zoom-mode');
                }
                resetConnectionState();
                showNotification('Zoom mode activated - Use mouse wheel to zoom in/out', 'info');
                showZoomControls();
            } else {
                hideZoomControls();
            }
        });
    });

    // Zoom control panel
    function createZoomControls() {
        const toolbar = document.querySelector('.floating-toolbar');
        if (!toolbar) return null;
        let wrapper = document.querySelector('.zoom-controls');
        if (wrapper) return wrapper;
        wrapper = document.createElement('div');
        wrapper.className = 'zoom-controls';
        wrapper.innerHTML = `
            <button class="zoom-btn zoom-in" aria-label="Zoom in">+</button>
            <button class="zoom-btn zoom-out" aria-label="Zoom out">−</button>
            <button class="zoom-btn zoom-reset" aria-label="Reset zoom">Reset</button>
        `;
        toolbar.appendChild(wrapper);
        wrapper.querySelector('.zoom-in').addEventListener('click', () => {
            builderMode.scale = Math.min(2.0, builderMode.scale + 0.1);
            if (canvas) {
                canvas.style.transform = `scale(${builderMode.scale})`;
                canvas.style.transformOrigin = 'center center';
            }
        });
        wrapper.querySelector('.zoom-out').addEventListener('click', () => {
            builderMode.scale = Math.max(0.5, builderMode.scale - 0.1);
            if (canvas) {
                canvas.style.transform = `scale(${builderMode.scale})`;
                canvas.style.transformOrigin = 'center center';
            }
        });
        wrapper.querySelector('.zoom-reset').addEventListener('click', () => {
            builderMode.scale = 1.0;
            if (canvas) {
                canvas.style.transform = `scale(${builderMode.scale})`;
            }
        });
        return wrapper;
    }

    function showZoomControls() {
        const wrapper = createZoomControls();
        if (wrapper) wrapper.style.display = 'flex';
    }

    function hideZoomControls() {
        const wrapper = document.querySelector('.zoom-controls');
        if (wrapper) wrapper.style.display = 'none';
    }

    if (canvas) {
        canvas.addEventListener('wheel', (event) => {
            if (builderMode.current === 'zoom') {
                event.preventDefault();
                const delta = event.deltaY > 0 ? -0.1 : 0.1;
                builderMode.scale = Math.max(0.5, Math.min(2.0, builderMode.scale + delta));
                canvas.style.transform = `scale(${builderMode.scale})`;
                canvas.style.transformOrigin = 'center center';
            }
        });
    }

    function handleConnectionMode(node, cp) {
        if (builderMode.current !== 'connect') {
            return;
        }

        if (!builderMode.connectionStart) {
            // Start connection
            builderMode.connectionStart = { node, cp };
            node.classList.add('connection-source');
            
            // Highlight valid targets (all other nodes)
            document.querySelectorAll('.workflow-node').forEach(n => {
                if (n !== node) {
                    n.classList.add('valid-target');
                }
            });

            showNotification('Select target node to connect', 'info');
        } else {
            // Complete connection
            if (builderMode.connectionStart.node === node) {
                showNotification('Cannot connect node to itself', 'warning');
                resetConnectionState();
                return;
            }

            // Check if connection already exists
            const exists = builderState.connections.some(c => 
                (c.source === builderMode.connectionStart.node.dataset.nodeId && c.target === node.dataset.nodeId)
            );
            
            if (exists) {
                showNotification('Connection already exists', 'warning');
            } else {
                drawConnection(builderMode.connectionStart.node, node);
                showNotification('Connection created!', 'success');
            }

            resetConnectionState();
        }
    }

    function resetConnectionState() {
        if (builderMode.connectionStart && builderMode.connectionStart.node) {
            builderMode.connectionStart.node.classList.remove('connection-source');
        }
        builderMode.connectionStart = null;
        
        // Remove valid-target class from all nodes
        document.querySelectorAll('.workflow-node').forEach(n => {
            n.classList.remove('valid-target');
        });
    }

    function getConnectionPath(sourceNode, targetNode) {
        const sourcePoint = sourceNode.querySelector('.connection-point.output') || sourceNode;
        const targetPoint = targetNode.querySelector('.connection-point.input') || targetNode;

        const canvasRect = canvas.getBoundingClientRect();
        const sourceRect = sourcePoint.getBoundingClientRect();
        const targetRect = targetPoint.getBoundingClientRect();
        const scale = builderMode.scale || 1;

        const x1 = (sourceRect.left - canvasRect.left + sourceRect.width / 2) / scale;
        const y1 = (sourceRect.top - canvasRect.top + sourceRect.height / 2) / scale;
        const x2 = (targetRect.left - canvasRect.left + targetRect.width / 2) / scale;
        const y2 = (targetRect.top - canvasRect.top + targetRect.height / 2) / scale;

        const cx1 = x1;
        const cy1 = y1 + Math.abs(y2 - y1) * 0.5 + 20;
        const cx2 = x2;
        const cy2 = y2 - Math.abs(y2 - y1) * 0.5 - 20;

        return `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;
    }

    function updateNodeConnections(node) {
        const nodeId = node.dataset.nodeId;
        const svg = document.getElementById('connectionLines');
        if (!svg) return;

        const lines = svg.querySelectorAll(`.connection-line[data-source="${nodeId}"], .connection-line[data-target="${nodeId}"]`);
        
        lines.forEach(line => {
            const sourceId = line.dataset.source;
            const targetId = line.dataset.target;
            const sourceNode = document.querySelector(`.workflow-node[data-node-id="${sourceId}"]`);
            const targetNode = document.querySelector(`.workflow-node[data-node-id="${targetId}"]`);

            if (sourceNode && targetNode) {
                const d = getConnectionPath(sourceNode, targetNode);
                line.setAttribute('d', d);
            }
        });
    }

    function drawConnection(sourceNode, targetNode) {
        const svg = document.getElementById('connectionLines');
        if (!svg) {
            showNotification('SVG element not found - cannot draw connections', 'error');
            console.error('SVG element not found');
            return;
        }

        const d = getConnectionPath(sourceNode, targetNode);

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        line.setAttribute('d', d);
        line.setAttribute('stroke', '#667eea');
        line.setAttribute('stroke-width', '3');
        line.setAttribute('fill', 'none');
        line.setAttribute('stroke-linecap', 'round');
        line.classList.add('connection-line');

        // Ensure arrow marker exists on the svg defs once
        if (!svg.__arrowCreated) {
            createArrowMarker(svg);
            svg.__arrowCreated = true;
        }
        line.setAttribute('marker-end', 'url(#arrowhead)');
        svg.appendChild(line);
        line.dataset.source = sourceNode.dataset.nodeId;
        line.dataset.target = targetNode.dataset.nodeId;
        builderState.connections.push({ source: line.dataset.source, target: line.dataset.target });

        const length = line.getTotalLength();
        line.style.strokeDasharray = length;
        line.style.strokeDashoffset = length;

        setTimeout(() => {
            line.style.transition = 'stroke-dashoffset 0.6s ease';
            line.style.strokeDashoffset = '0';
            
            // Remove dash array after animation to allow flexible length
            setTimeout(() => {
                line.style.strokeDasharray = 'none';
                line.style.strokeDashoffset = 'none';
                line.style.transition = 'none';
            }, 600);
        }, 50);
    }

    // Bind undo and save workflow actions in canvas header
    const headerUndoBtn = document.querySelector('.canvas-header .canvas-actions [data-action="undo"]');
    const headerSaveBtn = document.querySelector('.canvas-header .canvas-actions [data-action="save-workflow"]');
    const headerClearBtn = document.querySelector('.canvas-header .canvas-actions [data-action="clear-canvas"]');
    const headerRunBtn = document.querySelector('.canvas-header .canvas-actions [data-action="run-workflow"]');

    if (headerUndoBtn) headerUndoBtn.addEventListener('click', () => undo());
    if (headerSaveBtn) headerSaveBtn.addEventListener('click', () => saveWorkflow());
    if (headerRunBtn) headerRunBtn.addEventListener('click', () => runWorkflow());

    // Load Workflow Logic
    const headerLoadBtn = document.querySelector('.canvas-header .canvas-actions [data-action="load-workflow"]');
    if (headerLoadBtn) headerLoadBtn.addEventListener('click', () => openLoadModal());

    // Modal Elements
    const loadModal = document.getElementById('loadWorkflowModal');
    const closeModalBtn = loadModal?.querySelector('.close-modal');
    const workflowListContainer = document.getElementById('workflowList');

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            loadModal.style.display = 'none';
        });
    }

    window.addEventListener('click', (event) => {
        if (event.target === loadModal) {
            loadModal.style.display = 'none';
        }
    });

    function openLoadModal() {
        if (!loadModal) return;
        loadModal.style.display = 'block';
        loadWorkflowsList();
    }

    function loadWorkflowsList() {
        if (!workflowListContainer) return;
        workflowListContainer.innerHTML = '<div class="loading-spinner">Loading...</div>';
        
        fetch('/api/workflows')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    renderWorkflowList(data.workflows);
                } else {
                    workflowListContainer.innerHTML = '<div class="error-message">Failed to load workflows</div>';
                }
            })
            .catch(error => {
                console.error('Error loading workflows:', error);
                workflowListContainer.innerHTML = '<div class="error-message">Network error</div>';
            });
    }

    function renderWorkflowList(workflows) {
        if (!workflows || workflows.length === 0) {
            workflowListContainer.innerHTML = '<div class="empty-message">No saved workflows found</div>';
            return;
        }

        workflowListContainer.innerHTML = '';
        workflows.forEach(workflow => {
            const item = document.createElement('div');
            item.className = 'workflow-item';
            
            const date = new Date(workflow.updated_at || workflow.created_at).toLocaleDateString();
            
            item.innerHTML = `
                <div class="workflow-item-info">
                    <h4>${workflow.name}</h4>
                    <div class="workflow-item-date">Last updated: ${date}</div>
                </div>
                <div class="workflow-item-actions">
                    <button class="delete-workflow-btn" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;

            // Click to load
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.delete-workflow-btn')) {
                    loadWorkflow(workflow.id);
                    loadModal.style.display = 'none';
                }
            });

            // Delete button
            const deleteBtn = item.querySelector('.delete-workflow-btn');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm(`Delete workflow "${workflow.name}"?`)) {
                    deleteWorkflow(workflow.id);
                }
            });

            workflowListContainer.appendChild(item);
        });
    }

    function deleteWorkflow(id) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        fetch(`/api/workflows/${id}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Workflow deleted', 'success');
                loadWorkflowsList(); // Refresh list
            } else {
                showNotification('Error deleting workflow', 'error');
            }
        });
    }

    function loadWorkflow(id) {
        // Redirect to load via URL
        window.location.href = `/workspace/builder?id=${id}`;
    }

    if (headerClearBtn) {
        headerClearBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to clear the entire workflow?')) {
                document.querySelectorAll('.workflow-node').forEach(n => n.remove());
                document.querySelectorAll('.connection-line').forEach(l => l.remove());
                builderState.connections = [];
                builderState.history = [];
                builderState.redo = [];
                updateDropZoneVisibility();
                showNotification('Canvas cleared', 'info');
            }
        });
    }

    async function runWorkflow() {
        showNotification('Executing workflow...', 'info');
        if (window.ConsoleManager) window.ConsoleManager.log('Starting workflow execution...', 'system');
        
        const nodes = [];
        document.querySelectorAll('.workflow-node').forEach((node) => {
            nodes.push({
                id: node.dataset.nodeId.replace('node-', ''),
                type: node.dataset.type,
                config: node.dataset.config ? JSON.parse(node.dataset.config) : {}
            });
        });

        const edges = [];
        const svg = document.getElementById('connectionLines');
        if (svg) {
            svg.querySelectorAll('.connection-line').forEach((line) => {
                edges.push({ 
                    from: line.dataset.source.replace('node-', ''), 
                    to: line.dataset.target.replace('node-', '') 
                });
            });
        }

        const payload = { nodes, edges };
        console.log("Executing Payload:", payload);
        if (window.ConsoleManager) window.ConsoleManager.log(`Payload prepared: ${nodes.length} nodes, ${edges.length} edges`, 'debug');

        try {
            const response = await fetch('/api/workflow/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            console.log("Execution Result:", result);
            if (window.ConsoleManager) window.ConsoleManager.log(`Execution finished. Status: ${result.status}`, result.status === 'completed' ? 'success' : 'error');
            if (window.ConsoleManager && result.logs) {
                 result.logs.forEach(log => window.ConsoleManager.log(log, 'info'));
            }

            if (result.status === 'completed') {
                showNotification('Workflow completed successfully!', 'success');
            } else {
                showNotification('Workflow failed: ' + (result.message || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Error executing workflow:', error);
            showNotification('Network error executing workflow', 'error');
        }
    }

    function saveWorkflow() {
        const nodes = [];
        document.querySelectorAll('.workflow-node').forEach((node) => {
            nodes.push({
                id: node.dataset.nodeId,
                title: node.dataset.title,
                category: node.dataset.category,
                left: parseInt(node.style.left, 10) || 0,
                top: parseInt(node.style.top, 10) || 0,
                description: node.querySelector('.node-content')?.textContent.trim() || ''
            });
        });

        const svg = document.getElementById('connectionLines');
        const connections = [];
        if (svg) {
            svg.querySelectorAll('.connection-line').forEach((line) => {
                connections.push({ source: line.dataset.source, target: line.dataset.target });
            });
        }

        const payload = { nodes, connections };
        
        // Get workflow ID from URL if exists
        const urlParams = new URLSearchParams(window.location.search);
        const workflowId = urlParams.get('id');
        
        let name = 'Untitled Workflow';
        if (!workflowId) {
            name = prompt('Enter workflow name:', 'My Workflow');
            if (!name) return;
        }

        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

        fetch('/api/workflows', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                id: workflowId,
                name: name,
                data: payload
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Workflow saved successfully', 'success');
                if (!workflowId) {
                    // Update URL without reload
                    const newUrl = new URL(window.location);
                    newUrl.searchParams.set('id', data.id);
                    window.history.pushState({}, '', newUrl);
                }
            } else {
                showNotification('Error saving workflow: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Network error saving workflow', 'error');
        });
    }

    // Load workflow if ID is present
    const urlParams = new URLSearchParams(window.location.search);
    const workflowId = urlParams.get('id');
    if (workflowId) {
        // We need to implement a way to load the specific workflow data
        // For now, we can fetch all and filter, or add a specific endpoint
        // Since we added /api/workflows (GET all), let's use that for now or assume the page might inject it
        // Better: Let's fetch the list and find it, or update the API to get one.
        // I'll assume the user will implement GET /api/workflows/<id> later or we use the list.
        // Actually, let's just fetch the list and find it for simplicity as per current API.
        
        fetch('/api/workflows')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const workflow = data.workflows.find(w => w.id == workflowId);
                if (workflow && workflow.data) {
                    loadWorkflowData(workflow.data);
                    showNotification(`Loaded workflow: ${workflow.name}`, 'success');
                }
            }
        });
    }

    function loadWorkflowData(data) {
        // Clear canvas
        document.querySelectorAll('.workflow-node').forEach(n => n.remove());
        document.querySelectorAll('.connection-line').forEach(l => l.remove());
        builderState.connections = [];
        
        // Restore nodes
        if (data.nodes) {
            data.nodes.forEach(nodeData => {
                const node = createWorkflowNode({
                    name: nodeData.title,
                    category: nodeData.category,
                    description: nodeData.description,
                    icon: getIconForCategory(nodeData.category) // Helper needed
                }, { x: nodeData.left + 100, y: nodeData.top + 40 }); // Adjust for offset in createWorkflowNode
                
                // Restore ID to maintain connections
                // Note: createWorkflowNode generates new ID. We might need to map old IDs to new IDs or force ID.
                // For simplicity, let's update the dataset ID after creation if we want to keep history, 
                // but connections rely on these IDs.
                // A better approach is to allow createWorkflowNode to accept an ID.
                // Let's hack it: update the ID after creation.
                if (node) {
                    node.dataset.nodeId = nodeData.id;
                    // Update counter to avoid collision
                    const numId = parseInt(nodeData.id.replace('node-', ''));
                    if (!isNaN(numId) && numId > builderState.nodeCounter) {
                        builderState.nodeCounter = numId;
                    }
                }
            });
        }
        
        // Restore connections
        if (data.connections) {
            setTimeout(() => {
                data.connections.forEach(conn => {
                    const source = document.querySelector(`.workflow-node[data-node-id="${conn.source}"]`);
                    const target = document.querySelector(`.workflow-node[data-node-id="${conn.target}"]`);
                    if (source && target) {
                        drawConnection(source, target);
                    }
                });
            }, 100);
        }
    }

    function getIconForCategory(category) {
        // Simple mapping or default
        const map = {
            'trigger': 'fas fa-bolt',
            'ai': 'fas fa-robot',
            'logic': 'fas fa-random',
            'integration': 'fas fa-plug',
            'custom': 'fas fa-puzzle-piece'
        };
        return map[category] || 'fas fa-puzzle-piece';
    }

    function createArrowMarker(svg) {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        marker.setAttribute('id', 'arrowhead');
        marker.setAttribute('markerWidth', '10');
        marker.setAttribute('markerHeight', '10');
        marker.setAttribute('refX', '9');
        marker.setAttribute('refY', '3');
        marker.setAttribute('orient', 'auto');

        const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        polygon.setAttribute('points', '0 0, 10 3, 0 6');
        polygon.setAttribute('fill', '#667eea');

        marker.appendChild(polygon);
        defs.appendChild(marker);
        svg.appendChild(defs);
        return defs;
    }

    function selectNode(node) {
        if (!node) {
            return;
        }

        if (builderMode.current === 'connect') {
            handleConnectionMode(node);
            return;
        }

        document.querySelectorAll('.workflow-node').forEach((item) => {
            item.classList.remove('selected');
        });
        node.classList.add('selected');
        builderState.selectedNode = node;

        if (selectedNodeTitle) {
            selectedNodeTitle.textContent = node.dataset.title || 'Node properties';
        }

        if (nodeNameInput) {
            nodeNameInput.value = node.dataset.title || '';
        }

        if (nodeDescriptionInput) {
            nodeDescriptionInput.value = node.querySelector('.node-content')?.textContent.trim() || '';
        }

        // --- Dynamic Settings Generation ---
        const settingsContainer = document.getElementById('nodeSettings');
        if (settingsContainer) {
            settingsContainer.innerHTML = ''; // Clear previous settings
            const type = node.dataset.type;
            const config = node.dataset.config ? JSON.parse(node.dataset.config) : {};

            let html = '';
            
            if (type === 'google_sheet_read') {
                html = `
                    <label>Spreadsheet ID</label>
                    <input type="text" id="cfg-sheet-id" value="${config.sheetId || ''}">
                    <label>Range</label>
                    <input type="text" id="cfg-range" value="${config.range || 'Sheet1!A1:B10'}">
                `;
            } else if (type === 'google_sheet_write') {
                html = `
                    <label>Spreadsheet ID</label>
                    <input type="text" id="cfg-sheet-id" value="${config.sheetId || ''}">
                    <label>Range</label>
                    <input type="text" id="cfg-range" value="${config.range || 'Sheet1!A1'}">
                    <label>Write Mode</label>
                    <select id="cfg-write-mode">
                        <option value="json" ${config.writeMode === 'json' ? 'selected' : ''}>JSON (List of Lists)</option>
                        <option value="row" ${config.writeMode === 'row' ? 'selected' : ''}>Row (Comma Separated)</option>
                        <option value="column" ${config.writeMode === 'column' ? 'selected' : ''}>Column (Newline Separated)</option>
                        <option value="cell" ${config.writeMode === 'cell' ? 'selected' : ''}>Single Cell</option>
                    </select>
                    <label>Data</label>
                    <textarea id="cfg-data" style="height: 80px;">${config.data || ''}</textarea>
                    <small>Use {{nodeId}} to reference other nodes.</small>
                `;
            } else if (type === 'google_doc_read') {
                html = `
                    <label>Document ID</label>
                    <input type="text" id="cfg-doc-id" value="${config.docId || ''}">
                `;
            } else if (type === 'gmail_send') {
                html = `
                    <label>To</label>
                    <input type="text" id="cfg-to" value="${config.to || ''}">
                    <label>Subject</label>
                    <input type="text" id="cfg-subject" value="${config.subject || ''}">
                    <label>Body</label>
                    <textarea id="cfg-body" style="height: 100px;">${config.body || ''}</textarea>
                `;
            } else if (type === 'make_webhook' || type === 'slack_notify' || type === 'discord_notify') {
                html = `
                    <label>Webhook URL</label>
                    <input type="text" id="cfg-url" value="${config.url || ''}">
                    <label>Message/Body</label>
                    <textarea id="cfg-message" style="height: 80px;">${config.message || config.body || ''}</textarea>
                `;
            } else if (type === 'filter') {
                html = `
                    <label>Contains Keyword</label>
                    <input type="text" id="cfg-keyword" value="${config.keyword || ''}">
                `;
            }

            settingsContainer.innerHTML = html;
        }

        propertyPanel?.classList.add('open');
    }

    // Assign node IDs for static nodes loaded in HTML so they are part of the history and connections
    document.querySelectorAll('.workflow-node').forEach((node) => {
        if (!node.dataset.nodeId) {
            builderState.nodeCounter += 1;
            node.dataset.nodeId = `node-${builderState.nodeCounter}`;
        }
        attachNodeInteractions(node);
    });

    bindPropertyInputs();
    // Save node properties from the property panel
    const saveNodeBtn = document.getElementById('saveNodeBtn');
    if (saveNodeBtn) {
        saveNodeBtn.addEventListener('click', () => {
            if (!builderState.selectedNode) {
                showNotification('No node selected', 'warning');
                return;
            }
            const node = builderState.selectedNode;
            const oldTitle = node.dataset.title;
            const oldDescription = node.querySelector('.node-content')?.textContent || '';
            const newTitle = nodeNameInput.value || oldTitle;
            const newDescription = nodeDescriptionInput.value || oldDescription;
            
            // Save basic info
            node.dataset.title = newTitle;
            const titleEl = node.querySelector('.node-title');
            if (titleEl) titleEl.textContent = newTitle;
            const contentEl = node.querySelector('.node-content');
            if (contentEl) contentEl.textContent = newDescription;

            // Save Config
            const config = node.dataset.config ? JSON.parse(node.dataset.config) : {};
            const type = node.dataset.type;

            if (type === 'google_sheet_read') {
                config.sheetId = document.getElementById('cfg-sheet-id')?.value;
                config.range = document.getElementById('cfg-range')?.value;
            } else if (type === 'google_sheet_write') {
                config.sheetId = document.getElementById('cfg-sheet-id')?.value;
                config.range = document.getElementById('cfg-range')?.value;
                config.writeMode = document.getElementById('cfg-write-mode')?.value;
                config.data = document.getElementById('cfg-data')?.value;
            } else if (type === 'google_doc_read') {
                config.docId = document.getElementById('cfg-doc-id')?.value;
            } else if (type === 'gmail_send') {
                config.to = document.getElementById('cfg-to')?.value;
                config.subject = document.getElementById('cfg-subject')?.value;
                config.body = document.getElementById('cfg-body')?.value;
            } else if (type === 'make_webhook') {
                config.url = document.getElementById('cfg-url')?.value;
                config.body = document.getElementById('cfg-message')?.value;
            } else if (type === 'slack_notify' || type === 'discord_notify') {
                config.url = document.getElementById('cfg-url')?.value;
                config.message = document.getElementById('cfg-message')?.value;
            } else if (type === 'filter') {
                config.keyword = document.getElementById('cfg-keyword')?.value;
            }

            node.dataset.config = JSON.stringify(config);

            pushHistory({ type: 'edit', nodeId: node.dataset.nodeId, from: { title: oldTitle, description: oldDescription }, to: { title: newTitle, description: newDescription } });
            showNotification('Node updated', 'success');
        });
    }

    // Initially hide zoom controls until user clicks zoom mode
    hideZoomControls();
    updateDropZoneVisibility();

    // Console Manager Logic
    const consolePanel = document.getElementById('consolePanel');
    const consoleContent = document.getElementById('consoleContent');
    const toggleConsoleBtn = document.getElementById('toggleConsole');
    const clearConsoleBtn = document.getElementById('clearConsole');
    const consoleResizer = document.getElementById('consoleResizer');
    const consoleHeader = document.getElementById('consoleHeader');

    const MINIMIZED_CONSOLE_HEIGHT = 48;
    let consoleHeight = 320;
    if (consolePanel && !consolePanel.classList.contains('minimized')) {
        consoleHeight = consolePanel.getBoundingClientRect().height || consoleHeight;
    }
    // Track console position for drag; start bottom-left with an offset
    let consolePos = { left: 16, top: (window.innerHeight - consoleHeight - 16) };
    let isResizingConsole = false;
    let resizeStartY = 0;
    let resizeStartHeight = 0;
    let isDraggingConsole = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let dragStartLeft = 0;
    let dragStartTop = 0;

    const clampConsolePosition = () => {
        if (!consolePanel) return;
        const rect = consolePanel.getBoundingClientRect();
        const maxLeft = Math.max(8, window.innerWidth - rect.width - 8);
        const maxTop = Math.max(8, window.innerHeight - rect.height - 8);
        consolePos.left = Math.min(Math.max(8, consolePos.left), maxLeft);
        consolePos.top = Math.min(Math.max(8, consolePos.top), maxTop);
    };

    const applyConsolePosition = () => {
        if (!consolePanel) return;
        clampConsolePosition();
        consolePanel.style.left = `${consolePos.left}px`;
        consolePanel.style.top = `${consolePos.top}px`;
        consolePanel.style.bottom = 'auto';
    };

    const ConsoleManager = {
        log: (message, type = 'info') => {
            if (!consoleContent) return;
            const line = document.createElement('div');
            line.className = `console-line ${type}`;
            const time = new Date().toLocaleTimeString();
            // Escape HTML in message to prevent XSS if message comes from user input
            const safeMessage = typeof message === 'string' ? message.replace(/</g, '&lt;').replace(/>/g, '&gt;') : JSON.stringify(message);
            line.innerHTML = `<span class="timestamp">[${time}]</span> <span class="message">${safeMessage}</span>`;
            consoleContent.appendChild(line);
            consoleContent.scrollTop = consoleContent.scrollHeight;
            
            // Auto-open on error or start
            if (type === 'error' || (typeof message === 'string' && message.includes('Executing workflow'))) {
                if (consolePanel) {
                    consolePanel.classList.remove('minimized');
                    consolePanel.style.height = `${consoleHeight}px`;
                    applyConsolePosition();
                }
                if (toggleConsoleBtn) toggleConsoleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
            }
        },
        clear: () => {
            if (consoleContent) consoleContent.innerHTML = '<div class="console-line system">Console cleared.</div>';
        },
        toggle: () => {
            if (consolePanel) {
                const isMin = consolePanel.classList.contains('minimized');
                if (isMin) {
                    consolePanel.classList.remove('minimized');
                    consolePanel.style.height = `${consoleHeight}px`;
                    applyConsolePosition();
                } else {
                    consoleHeight = consolePanel.getBoundingClientRect().height || consoleHeight;
                    consolePanel.style.height = `${MINIMIZED_CONSOLE_HEIGHT}px`;
                    consolePanel.classList.add('minimized');
                }
                if (toggleConsoleBtn) toggleConsoleBtn.innerHTML = consolePanel.classList.contains('minimized') ? '<i class="fas fa-chevron-up"></i>' : '<i class="fas fa-chevron-down"></i>';
            }
        }
    };

    if (toggleConsoleBtn) toggleConsoleBtn.addEventListener('click', ConsoleManager.toggle);
    if (clearConsoleBtn) clearConsoleBtn.addEventListener('click', ConsoleManager.clear);
    if (consoleResizer && consolePanel) {
        const handleConsoleResize = (event) => {
            if (!isResizingConsole) return;
            event.preventDefault();
            const clientY = event.clientY ?? event.touches?.[0]?.clientY;
            const delta = resizeStartY - clientY;
            const maxHeight = Math.min(window.innerHeight * 0.8, window.innerHeight - 80);
            let nextHeight = resizeStartHeight + delta;
            nextHeight = Math.max(160, Math.min(maxHeight, nextHeight));
            consoleHeight = nextHeight;
            consolePanel.style.height = `${nextHeight}px`;
            clampConsolePosition();
        };

        const stopConsoleResize = (event) => {
            if (!isResizingConsole) return;
            isResizingConsole = false;
            consoleHeight = consolePanel.getBoundingClientRect().height || consoleHeight;
            clampConsolePosition();
            applyConsolePosition();
            document.removeEventListener('pointermove', handleConsoleResize);
            document.removeEventListener('pointerup', stopConsoleResize);
            document.removeEventListener('pointercancel', stopConsoleResize);
            if (event?.pointerId !== undefined) {
                try { consoleResizer.releasePointerCapture(event.pointerId); } catch (err) {}
            }
        };

        consoleResizer.addEventListener('pointerdown', (event) => {
            if (consolePanel.classList.contains('minimized')) {
                consolePanel.classList.remove('minimized');
                consolePanel.style.height = `${consoleHeight}px`;
                if (toggleConsoleBtn) toggleConsoleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
            }
            event.preventDefault();
            isResizingConsole = true;
            resizeStartY = event.clientY;
            resizeStartHeight = consolePanel.getBoundingClientRect().height;
            if (event.pointerId !== undefined) {
                try { consoleResizer.setPointerCapture(event.pointerId); } catch (err) {}
            }
            document.addEventListener('pointermove', handleConsoleResize);
            document.addEventListener('pointerup', stopConsoleResize);
            document.addEventListener('pointercancel', stopConsoleResize);
        });
    }

    // Dragging the console via header
    if (consoleHeader && consolePanel) {
        const stopConsoleDrag = (event) => {
            if (!isDraggingConsole) return;
            isDraggingConsole = false;
            document.removeEventListener('pointermove', handleConsoleDrag);
            document.removeEventListener('pointerup', stopConsoleDrag);
            document.removeEventListener('pointercancel', stopConsoleDrag);
            if (event?.pointerId !== undefined) {
                try { consoleHeader.releasePointerCapture(event.pointerId); } catch (err) {}
            }
        };

        const handleConsoleDrag = (event) => {
            if (!isDraggingConsole) return;
            event.preventDefault();
            const clientX = event.clientX ?? event.touches?.[0]?.clientX;
            const clientY = event.clientY ?? event.touches?.[0]?.clientY;
            const deltaX = clientX - dragStartX;
            const deltaY = clientY - dragStartY;
            consolePos.left = dragStartLeft + deltaX;
            consolePos.top = dragStartTop + deltaY;
            applyConsolePosition();
        };

        consoleHeader.addEventListener('pointerdown', (event) => {
            // Skip drag when clicking action buttons
            if (event.target.closest('.console-action-btn')) return;
            event.preventDefault();
            if (consolePanel.classList.contains('minimized')) {
                consolePanel.classList.remove('minimized');
                consolePanel.style.height = `${consoleHeight}px`;
                if (toggleConsoleBtn) toggleConsoleBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
            }
            isDraggingConsole = true;
            dragStartX = event.clientX;
            dragStartY = event.clientY;
            const rect = consolePanel.getBoundingClientRect();
            dragStartLeft = rect.left;
            dragStartTop = rect.top;
            if (event.pointerId !== undefined) {
                try { consoleHeader.setPointerCapture(event.pointerId); } catch (err) {}
            }
            document.addEventListener('pointermove', handleConsoleDrag);
            document.addEventListener('pointerup', stopConsoleDrag);
            document.addEventListener('pointercancel', stopConsoleDrag);
        });
    }

    // Apply initial position
    applyConsolePosition();
    
    // Make it available globally for runWorkflow
    window.ConsoleManager = ConsoleManager;
});
