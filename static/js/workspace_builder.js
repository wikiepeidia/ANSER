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
            category: tool.dataset.category || 'custom'
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
                // showNotification('Edit mode activated', 'info');
                break;
            case 'duplicate': {
                const clone = node.cloneNode(true);
                clone.style.left = `${parseInt(node.style.left, 10) + 30}px`;
                clone.style.top = `${parseInt(node.style.top, 10) + 30}px`;
                canvas?.appendChild(clone);
                attachNodeInteractions(clone);
                // showNotification('Node duplicated', 'success');
                break;
            }
            case 'delete':
                if (confirm('Delete this node?')) {
                    const nodeId = node.dataset.nodeId;
                    const snapshot = node.outerHTML;
                    node.remove();
                    pushHistory({ type: 'delete', nodeId, snapshot });
                    // showNotification('Node deleted', 'success');
                    if (builderState.selectedNode === node) {
                        builderState.selectedNode = null;
                        propertyPanel?.classList.remove('open');
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

        const node = document.createElement('div');
        node.className = 'workflow-node';
        node.dataset.title = toolData.name;
        node.dataset.category = toolData.category;
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
                canvas?.classList.remove('connect-mode', 'zoom-mode');
                canvas?.classList.add('cursor-mode');
                builderMode.isConnecting = false;
                builderMode.connectionStart = null;
                // showNotification('Select mode activated - Click nodes to select and edit', 'info');
            } else if (action === 'connect') {
                canvas?.classList.remove('cursor-mode', 'zoom-mode');
                canvas?.classList.add('connect-mode');
                builderMode.isConnecting = true;
                // showNotification('Connect mode activated - Click nodes to connect them', 'info');
            } else if (action === 'zoom') {
                canvas?.classList.remove('cursor-mode', 'connect-mode');
                canvas?.classList.add('zoom-mode');
                // showNotification('Zoom mode activated - Use mouse wheel to zoom in/out', 'info');
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
            canvas.style.transform = `scale(${builderMode.scale})`;
            canvas.style.transformOrigin = 'center center';
        });
        wrapper.querySelector('.zoom-out').addEventListener('click', () => {
            builderMode.scale = Math.max(0.5, builderMode.scale - 0.1);
            canvas.style.transform = `scale(${builderMode.scale})`;
            canvas.style.transformOrigin = 'center center';
        });
        wrapper.querySelector('.zoom-reset').addEventListener('click', () => {
            builderMode.scale = 1.0;
            canvas.style.transform = `scale(${builderMode.scale})`;
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
            builderMode.connectionStart = { node, cp };
            node.classList.add('connection-source');
            // showNotification('Click another node to create connection', 'info');
        } else {
            if (builderMode.connectionStart.node !== node) {
                drawConnection(builderMode.connectionStart.node, node);
                // showNotification('Connection created!', 'success');
            }
            builderMode.connectionStart.node.classList.remove('connection-source');
            builderMode.connectionStart = null;
        }
    }

    function drawConnection(sourceNode, targetNode) {
        const svg = document.getElementById('connectionLines');
        if (!svg) {
            console.error('SVG element not found');
            return;
        }

        const sourceRect = sourceNode.getBoundingClientRect();
        const targetRect = targetNode.getBoundingClientRect();

        const x1 = sourceRect.left + sourceRect.width / 2;
        const y1 = sourceRect.bottom;
        const x2 = targetRect.left + targetRect.width / 2;
        const y2 = targetRect.top;

        const cx1 = x1;
        const cy1 = y1 + Math.abs(y2 - y1) * 0.5;
        const cx2 = x2;
        const cy2 = y1 + Math.abs(y2 - y1) * 0.5;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        line.setAttribute('d', `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`);
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
        }, 50);
    }

    // Bind undo and save workflow actions in canvas header
    const headerUndoBtn = document.querySelector('.canvas-header .canvas-actions [data-action="undo"]');
    const headerSaveBtn = document.querySelector('.canvas-header .canvas-actions [data-action="save-workflow"]');
    if (headerUndoBtn) headerUndoBtn.addEventListener('click', () => undo());
    if (headerSaveBtn) headerSaveBtn.addEventListener('click', () => saveWorkflow());

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
        // Show payload in console or show a notification for now.
        console.log('Workflow to save:', payload);
        if (typeof showNotification === 'function') {
            showNotification('Workflow saved locally (client-side)', 'success');
        } else {
            alert('Workflow saved locally (check console).');
        }
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
                if (typeof showNotification === 'function') showNotification('No node selected', 'warning');
                return;
            }
            const node = builderState.selectedNode;
            const oldTitle = node.dataset.title;
            const oldDescription = node.querySelector('.node-content')?.textContent || '';
            const newTitle = nodeNameInput.value || oldTitle;
            const newDescription = nodeDescriptionInput.value || oldDescription;
            node.dataset.title = newTitle;
            const titleEl = node.querySelector('.node-title');
            if (titleEl) titleEl.textContent = newTitle;
            const contentEl = node.querySelector('.node-content');
            if (contentEl) contentEl.textContent = newDescription;
            pushHistory({ type: 'edit', nodeId: node.dataset.nodeId, from: { title: oldTitle, description: oldDescription }, to: { title: newTitle, description: newDescription } });
            if (typeof showNotification === 'function') showNotification('Node updated', 'success');
        });
    }

    // Initially hide zoom controls until user clicks zoom mode
    hideZoomControls();
    updateDropZoneVisibility();
});
