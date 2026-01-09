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
    const googleConnected = document.querySelector('.builder-container')?.dataset.googleConnected === 'true';
    let googleWarningShown = false;
    const googlePickerState = {
        targetInputId: null,
        type: 'sheets',
        selected: null,
        nextPageToken: null,
        loading: false,
        currentQuery: ''
    };
    const categoryColors = {
        trigger: '#8bc34a',
        ai: '#00bcd4',
        logic: '#ff9800',
        integration: '#9c27b0',
        custom: '#667eea'
    };

    // --- Templates Logic ---
    const templates = {
        invoice_scan: {
            nodes: [
                { id: 'node-1', title: 'Upload Invoice', category: 'trigger', type: 'manual_trigger', left: 100, top: 100, description: 'Start by uploading an invoice file' },
                { id: 'node-2', title: 'OCR Processing', category: 'ai', type: 'ocr_service', left: 400, top: 100, description: 'Extract text from image (DL Service)' },
                { id: 'node-3', title: 'AI Analysis', category: 'ai', type: 'ai_service', left: 700, top: 100, description: 'Analyze invoice content' },
                { id: 'node-4', title: 'Notify Slack', category: 'integration', type: 'slack_notify', left: 1000, top: 100, description: 'Send results to team' }
            ],
            connections: [
                { source: 'node-1', target: 'node-2' },
                { source: 'node-2', target: 'node-3' },
                { source: 'node-3', target: 'node-4' }
            ]
        },
        customer_feedback: {
            nodes: [
                { id: 'node-1', title: 'Read Feedback', category: 'integration', type: 'google_sheet_read', left: 100, top: 100, description: 'Fetch new rows from Sheets' },
                { id: 'node-2', title: 'Sentiment Analysis', category: 'ai', type: 'ai_service', left: 400, top: 100, description: 'Analyze sentiment (Positive/Negative)' },
                { id: 'node-3', title: 'Filter Negative', category: 'logic', type: 'filter', left: 700, top: 100, description: 'Continue if sentiment is Negative' },
                { id: 'node-4', title: 'Alert Manager', category: 'integration', type: 'gmail_send', left: 1000, top: 100, description: 'Email support manager' }
            ],
            connections: [
                { source: 'node-1', target: 'node-2' },
                { source: 'node-2', target: 'node-3' },
                { source: 'node-3', target: 'node-4' }
            ]
        },
        low_stock_alert: {
            nodes: [
                { id: 'node-1', title: 'Check Stock', category: 'trigger', type: 'schedule_trigger', left: 100, top: 100, description: 'Run daily at 9 AM' },
                { id: 'node-2', title: 'Read Inventory', category: 'integration', type: 'google_sheet_read', left: 400, top: 100, description: 'Get stock levels' },
                { id: 'node-3', title: 'Filter Low Stock', category: 'logic', type: 'filter', left: 700, top: 100, description: 'Continue if stock < 10' },
                { id: 'node-4', title: 'Email Purchasing', category: 'integration', type: 'gmail_send', left: 1000, top: 100, description: 'Send reorder list' }
            ],
            connections: [
                { source: 'node-1', target: 'node-2' },
                { source: 'node-2', target: 'node-3' },
                { source: 'node-3', target: 'node-4' }
            ]
        },
        daily_report: {
            nodes: [
                { id: 'node-1', title: 'Daily Trigger', category: 'trigger', type: 'schedule_trigger', left: 100, top: 100, description: 'Run every day' },
                { id: 'node-2', title: 'Fetch Sales', category: 'integration', type: 'google_sheet_read', left: 400, top: 100, description: 'Get daily sales data' },
                { id: 'node-3', title: 'Summarize AI', category: 'ai', type: 'ai_service', left: 700, top: 100, description: 'Generate summary report' },
                { id: 'node-4', title: 'Send Report', category: 'integration', type: 'gmail_send', left: 1000, top: 100, description: 'Email to stakeholders' }
            ],
            connections: [
                { source: 'node-1', target: 'node-2' },
                { source: 'node-2', target: 'node-3' },
                { source: 'node-3', target: 'node-4' }
            ]
        },
        social_media_monitor: {
            nodes: [
                { id: 'node-1', title: 'New Mention', category: 'trigger', type: 'webhook_trigger', left: 100, top: 100, description: 'Webhook from social tool' },
                { id: 'node-2', title: 'Analyze Sentiment', category: 'ai', type: 'ai_service', left: 400, top: 100, description: 'Positive/Negative/Neutral' },
                { id: 'node-3', title: 'Log to Sheet', category: 'integration', type: 'google_sheet_write', left: 700, top: 100, description: 'Save for analysis' }
            ],
            connections: [
                { source: 'node-1', target: 'node-2' },
                { source: 'node-2', target: 'node-3' }
            ]
        }
    };

    document.querySelectorAll('.template-item').forEach(item => {
        item.addEventListener('click', () => {
            const templateId = item.dataset.template;
            if (templates[templateId]) {
                if (confirm('Load template? This will clear the current canvas.')) {
                    loadWorkflowData(templates[templateId]);
                    showNotification(`Loaded template: ${item.querySelector('.tool-name').textContent}`, 'success');
                }
            }
        });
    });

    // Notification function for workspace builder
    // Uses global showNotification from script.js

    function isGoogleNodeType(type) {
        return ['google_sheet_read', 'google_sheet_write', 'google_doc_read', 'gmail_send'].includes(type);
    }

    function warnIfGoogleNode(type) {
        if (!googleConnected && isGoogleNodeType(type) && !googleWarningShown) {
            showNotification('Google login required: connect your account to run this node.', 'warning');
            googleWarningShown = true;
        }
    }

    // --- Google Drive Picker ---
    const pickerModal = document.getElementById('googlePickerModal');
    const pickerList = document.getElementById('googlePickerList');
    const pickerSearch = document.getElementById('googlePickerSearch');
    const pickerType = document.getElementById('googlePickerType');
    const pickerStatus = document.getElementById('googlePickerStatus');
    const pickerSelectBtn = document.getElementById('googlePickerSelect');
    const pickerLoadMoreBtn = document.getElementById('googlePickerLoadMore');

    function closePicker() {
        if (pickerModal) pickerModal.style.display = 'none';
        googlePickerState.targetInputId = null;
        googlePickerState.selected = null;
        googlePickerState.nextPageToken = null;
        googlePickerState.currentQuery = '';
        if (pickerSelectBtn) pickerSelectBtn.disabled = true;
    }

    function renderPickerLoading({ append = false } = {}) {
        if (!pickerList || append) return;
        pickerList.innerHTML = '';
        for (let i = 0; i < 3; i++) {
            const skeleton = document.createElement('div');
            skeleton.className = 'workflow-item skeleton';
            skeleton.innerHTML = `
                <div>
                    <div class="skeleton-line" style="width: 180px;"></div>
                    <div class="skeleton-line" style="width: 120px; margin-top: 6px;"></div>
                </div>
                <div class="skeleton-line" style="width: 90px;"></div>
            `;
            pickerList.appendChild(skeleton);
        }
    }

    function renderPickerList(files, append = false) {
        if (!pickerList) return;
        if (!append) pickerList.innerHTML = '';
        if (!files || files.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'workflow-empty';
            empty.textContent = 'No files found';
            pickerList.appendChild(empty);
            return;
        }
        files.forEach((file) => {
            const item = document.createElement('div');
            item.className = 'workflow-item';
            item.dataset.fileId = file.id;
            item.dataset.fileName = file.name;
            item.innerHTML = `
                <div>
                    <div style="font-weight:600;">${file.name}</div>
                    <div style="font-size:12px;color:#666;">${file.mimeType || ''}</div>
                </div>
                <div style="font-size:12px;color:#777;">${file.modifiedTime ? new Date(file.modifiedTime).toLocaleString() : ''}</div>
            `;
            item.addEventListener('click', () => {
                pickerList.querySelectorAll('.workflow-item').forEach(el => el.classList.remove('selected'));
                item.classList.add('selected');
                googlePickerState.selected = { id: file.id, name: file.name, mimeType: file.mimeType };
                if (pickerSelectBtn) pickerSelectBtn.disabled = false;
            });
            pickerList.appendChild(item);
        });
    }

    function setPickerLoading(isLoading, { append = false } = {}) {
        googlePickerState.loading = isLoading;
        if (pickerStatus) pickerStatus.style.display = isLoading ? 'block' : 'none';
        if (isLoading) {
            renderPickerLoading({ append });
        }
    }

    function fetchPickerFiles({ query = '', pageToken = null, append = false } = {}) {
        if (!googleConnected) {
            showNotification('Connect Google to browse Drive.', 'warning');
            return;
        }
        if (!pickerModal) return;
        const type = pickerType?.value || 'sheets';
        googlePickerState.type = type;
        googlePickerState.currentQuery = query;
        setPickerLoading(true, { append });
        pickerLoadMoreBtn && (pickerLoadMoreBtn.style.display = 'none');

        const params = new URLSearchParams();
        params.set('type', type);
        if (query) params.set('q', query);
        params.set('pageSize', '50');
        if (pageToken) params.set('pageToken', pageToken);

        fetch(`/api/google/files?${params.toString()}`)
            .then(res => res.json())
            .then(data => {
                if (!data.success) {
                    showNotification(data.message || 'Failed to load files', 'error');
                    return;
                }
                renderPickerList(data.files || [], append);
                googlePickerState.nextPageToken = data.nextPageToken || null;
                if (pickerLoadMoreBtn) {
                    pickerLoadMoreBtn.style.display = googlePickerState.nextPageToken ? 'inline-block' : 'none';
                }
            })
            .catch(() => {
                showNotification('Network error while loading Drive files', 'error');
            })
            .finally(() => setPickerLoading(false, { append }));
    }

    function openGooglePicker(options) {
        if (!googleConnected) {
            showNotification('Connect Google to browse Drive.', 'warning');
            return;
        }
        googlePickerState.targetInputId = options?.targetInputId || null;
        if (pickerType && options?.type) pickerType.value = options.type;
        googlePickerState.type = pickerType?.value || 'sheets';
        googlePickerState.selected = null;
        pickerSelectBtn && (pickerSelectBtn.disabled = true);
        if (pickerModal) pickerModal.style.display = 'block';
        setPickerLoading(true);
        fetchPickerFiles();
    }

    if (pickerSelectBtn) {
        pickerSelectBtn.addEventListener('click', () => {
            const selected = googlePickerState.selected;
            if (!selected || !googlePickerState.targetInputId) return;
            const target = document.getElementById(googlePickerState.targetInputId);
            if (target) {
                target.value = selected.id;
                target.dataset.displayName = selected.name;
            }
            closePicker();
        });
    }

    if (pickerLoadMoreBtn) {
        pickerLoadMoreBtn.addEventListener('click', () => {
            if (googlePickerState.nextPageToken) {
                fetchPickerFiles({ query: googlePickerState.currentQuery, pageToken: googlePickerState.nextPageToken, append: true });
            }
        });
    }

    if (pickerSearch) {
        let searchDebounce;
        pickerSearch.addEventListener('input', (e) => {
            const q = e.target.value || '';
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(() => fetchPickerFiles({ query: q }), 250);
        });
    }

    if (pickerType) {
        pickerType.addEventListener('change', () => fetchPickerFiles({ query: pickerSearch?.value || '' }));
    }

    document.querySelectorAll('[data-close="googlePickerModal"]').forEach(btn => {
        btn.addEventListener('click', closePicker);
    });

    window.addEventListener('click', (event) => {
        if (event.target === pickerModal) {
            closePicker();
        }
    });


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
                const toRemove = [...svg.querySelectorAll('.connection-wrapper')].find((g) => g.dataset.source === last.source && g.dataset.target === last.target);
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
            if (event.target.closest('.node-menu') || event.target.closest('.connection-point')) {
                return;
            }
            selectNode(node);
        });

        // Attach click handlers to connection points
        const connectionPoints = node.querySelectorAll('.connection-point');
        if (connectionPoints && connectionPoints.length) {
            connectionPoints.forEach((cp) => {
                cp.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    handlePointClick(node, cp);
                });
            });
        }

        enableNodeDragging(node);
    }

    // New Connection Logic
    const connectionState = {
        active: false,
        sourceNode: null,
        sourcePoint: null
    };

    function handlePointClick(node, point) {
        const isOutput = point.classList.contains('output');
        const isInput = point.classList.contains('input');
        const nodeId = node.dataset.nodeId;

        // Check if point is already connected
        const isConnected = builderState.connections.some(c => 
            (isOutput && c.source === nodeId) || (isInput && c.target === nodeId)
        );

        // Scenario: Disconnect if clicking an already connected point
        if (isConnected) {
            if (confirm('Disconnect this node?')) {
                // Remove all connections involving this point
                const wrappersToRemove = [];
                const svg = document.getElementById('connectionLines');
                
                if (isOutput) {
                    // Remove all outgoing from this node
                    builderState.connections = builderState.connections.filter(c => {
                        if (c.source === nodeId) {
                            const w = svg.querySelector(`.connection-wrapper[data-source="${c.source}"][data-target="${c.target}"]`);
                            if (w) wrappersToRemove.push(w);
                            
                            // Remove 'connected' from the target input point
                            const targetNode = document.querySelector(`.workflow-node[data-node-id="${c.target}"]`);
                            if (targetNode) {
                                const targetPoint = targetNode.querySelector('.connection-point.input');
                                if (targetPoint) targetPoint.classList.remove('connected');
                            }
                            
                            return false;
                        }
                        return true;
                    });
                } else {
                    // Remove all incoming to this node
                    builderState.connections = builderState.connections.filter(c => {
                        if (c.target === nodeId) {
                            const w = svg.querySelector(`.connection-wrapper[data-source="${c.source}"][data-target="${c.target}"]`);
                            if (w) wrappersToRemove.push(w);

                            // Remove 'connected' from the source output point
                            const sourceNode = document.querySelector(`.workflow-node[data-node-id="${c.source}"]`);
                            if (sourceNode) {
                                const sourcePoint = sourceNode.querySelector('.connection-point.output');
                                if (sourcePoint) sourcePoint.classList.remove('connected');
                            }

                            return false;
                        }
                        return true;
                    });
                }
                
                wrappersToRemove.forEach(w => w.remove());
                point.classList.remove('connected');
                point.classList.remove('connecting'); // Ensure connecting state is also cleared
                showNotification('Disconnected', 'info');
            }
            // Reset any active connection state just in case
            resetConnectionState();
            return;
        }

        // Scenario: Start or Complete Connection
        if (!connectionState.active) {
            // Start connecting (must start from Output usually, but let's allow flexible start)
            if (isOutput) {
                connectionState.active = true;
                connectionState.sourceNode = node;
                connectionState.sourcePoint = point;
                point.classList.add('connecting');
                showNotification('Select an input to connect', 'info');
            } else {
                showNotification('Start connection from an Output point (Right side)', 'warning');
            }
        } else {
            // Complete connection
            if (connectionState.sourceNode === node) {
                // Cancel if clicking same node
                resetConnectionState();
                showNotification('Connection cancelled', 'info');
                return;
            }

            // If user clicks another Output point while active, restart connection from there
            if (isOutput) {
                resetConnectionState();
                connectionState.active = true;
                connectionState.sourceNode = node;
                connectionState.sourcePoint = point;
                point.classList.add('connecting');
                showNotification('New connection started', 'info');
                return;
            }

            if (isInput) {
                // Valid connection: Output -> Input
                drawConnection(connectionState.sourceNode, node);
                showNotification('Connected!', 'success');
                
                // Mark points as connected
                connectionState.sourcePoint.classList.add('connected');
                point.classList.add('connected');
                
                resetConnectionState();
            } else {
                showNotification('Connect to an Input point (Left side)', 'warning');
            }
        }
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
                    
                    // Remove associated connections
                    const wrappersToRemove = [];
                    document.querySelectorAll('.connection-wrapper').forEach(wrapper => {
                        if (wrapper.dataset.source === nodeId || wrapper.dataset.target === nodeId) {
                            wrappersToRemove.push(wrapper);
                        }
                    });
                    wrappersToRemove.forEach(w => w.remove());
                    
                    // Update builderState.connections
                    builderState.connections = builderState.connections.filter(c => c.source !== nodeId && c.target !== nodeId);

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
        if (!node || !canvas) {
            return;
        }

        node.addEventListener('mousedown', (event) => {
            // Ignore clicks on inputs, buttons, or connection points
            if (event.target.closest('input, button, .connection-point, .node-menu')) return;

            if (event.button !== 0) {
                return;
            }
            event.preventDefault();
            
            const scale = builderMode.scale || 1;
            const startLeft = parseInt(node.style.left, 10) || 0;
            const startTop = parseInt(node.style.top, 10) || 0;
            const startX = event.clientX;
            const startY = event.clientY;

            node.classList.add('dragging');

            function onMouseMove(moveEvent) {
                const dx = (moveEvent.clientX - startX) / scale;
                const dy = (moveEvent.clientY - startY) / scale;
                
                const newLeft = startLeft + dx;
                const newTop = startTop + dy;
                
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
        let isComposing = false;

        if (nodeNameInput) {
            nodeNameInput.addEventListener('compositionstart', () => { isComposing = true; });
            nodeNameInput.addEventListener('compositionend', (event) => {
                isComposing = false;
                // Trigger input event manually to update model
                nodeNameInput.dispatchEvent(new Event('input'));
            });

            nodeNameInput.addEventListener('input', (event) => {
                if (isComposing || !builderState.selectedNode) {
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
            nodeDescriptionInput.addEventListener('compositionstart', () => { isComposing = true; });
            nodeDescriptionInput.addEventListener('compositionend', (event) => {
                isComposing = false;
                nodeDescriptionInput.dispatchEvent(new Event('input'));
            });

            nodeDescriptionInput.addEventListener('input', (event) => {
                if (isComposing || !builderState.selectedNode) {
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
        if (connectionState.active) {
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

        builderState.nodeCounter += 1; // Increment before creating HTML

        node.innerHTML = `
            <div class="node-header">
                <div class="node-icon" style="background: ${getCategoryColor(toolData.category)};">
                    <i class="${toolData.icon}"></i>
                </div>
                <div class="node-title">
                    <span class="node-id-badge" style="font-size:0.8em; opacity:0.6; margin-right:4px;">#${builderState.nodeCounter}</span>
                    ${toolData.name}
                </div>
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

        node.dataset.nodeId = `node-${builderState.nodeCounter}`;
        canvas.appendChild(node);
        attachNodeInteractions(node);
        pushHistory({ type: 'create', nodeId: node.dataset.nodeId });
        updateDropZoneVisibility();
        selectNode(node);
        warnIfGoogleNode(toolData.type);
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
        translateX: 0,
        translateY: 0,
        isConnecting: false,
        connectionStart: null
    };

    document.querySelectorAll('.toolbar-btn').forEach((btn) => {
        btn.setAttribute('role', 'button');
        btn.setAttribute('aria-pressed', 'false');
        btn.style.display = 'none'; // Hide buttons as modes are removed
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
                    canvas.classList.remove('zoom-mode');
                    canvas.classList.add('cursor-mode');
                }
                resetConnectionState();
                showNotification('Select mode activated', 'info');
            } else if (action === 'connect') {
                // Legacy connect button - now just informs user
                showNotification('Click the big circles on nodes to connect!', 'info');
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
            // Only zoom if Ctrl key is pressed
            if (event.ctrlKey) {
                event.preventDefault();
                const delta = event.deltaY > 0 ? -0.1 : 0.1;
                builderMode.scale = Math.max(0.5, Math.min(2.0, builderMode.scale + delta));
                canvas.style.transform = `translate(${builderMode.translateX}px, ${builderMode.translateY}px) scale(${builderMode.scale})`;
                canvas.style.transformOrigin = '0 0';
            } else {
                // Normal scrolling behavior (let the browser handle it or implement pan if needed)
                // If we want infinite canvas panning:
                event.preventDefault();
                builderMode.translateX -= event.deltaX;
                builderMode.translateY -= event.deltaY;
                canvas.style.transform = `translate(${builderMode.translateX}px, ${builderMode.translateY}px) scale(${builderMode.scale})`;
                canvas.style.transformOrigin = '0 0';
            }
        });
        
        // Mouse drag to pan
        let isPanning = false;
        let startX, startY;

        canvas.addEventListener('mousedown', (e) => {
            // Only pan if clicking on background (not on a node)
            if (e.target === canvas || e.target.id === 'dropZone') {
                isPanning = true;
                startX = e.clientX - builderMode.translateX;
                startY = e.clientY - builderMode.translateY;
                canvas.style.cursor = 'grabbing';

                // Reset connection state if clicking background
                if (connectionState.active) {
                    resetConnectionState();
                    showNotification('Connection cancelled', 'info');
                }
            }
        });

        window.addEventListener('mousemove', (e) => {
            if (!isPanning) return;
            e.preventDefault();
            builderMode.translateX = e.clientX - startX;
            builderMode.translateY = e.clientY - startY;
            canvas.style.transform = `translate(${builderMode.translateX}px, ${builderMode.translateY}px) scale(${builderMode.scale})`;
        });

        window.addEventListener('mouseup', () => {
            isPanning = false;
            canvas.style.cursor = 'default';
        });

        // Add click listener to reset connection state when clicking on empty canvas
        canvas.addEventListener('click', (event) => {
            // Check if clicking directly on canvas or dropZone (background)
            if (event.target === canvas || event.target.id === 'dropZone') {
                resetConnectionState();
            }
        });
    }

    function resetConnectionState() {
        if (connectionState.sourcePoint) {
            connectionState.sourcePoint.classList.remove('connecting');
        }
        connectionState.active = false;
        connectionState.sourceNode = null;
        connectionState.sourcePoint = null;
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

        const wrappers = svg.querySelectorAll(`.connection-wrapper[data-source="${nodeId}"], .connection-wrapper[data-target="${nodeId}"]`);
        
        wrappers.forEach(wrapper => {
            const sourceId = wrapper.dataset.source;
            const targetId = wrapper.dataset.target;
            const sourceNode = document.querySelector(`.workflow-node[data-node-id="${sourceId}"]`);
            const targetNode = document.querySelector(`.workflow-node[data-node-id="${targetId}"]`);

            if (sourceNode && targetNode) {
                const d = getConnectionPath(sourceNode, targetNode);
                wrapper.querySelectorAll('path').forEach(p => p.setAttribute('d', d));
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

        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.classList.add('connection-wrapper');
        group.dataset.source = sourceNode.dataset.nodeId;
        group.dataset.target = targetNode.dataset.nodeId;
        group.style.cursor = 'pointer';

        // Hit area path (invisible, wide)
        const hitPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        hitPath.setAttribute('d', d);
        hitPath.setAttribute('stroke', 'transparent');
        hitPath.setAttribute('stroke-width', '20');
        hitPath.setAttribute('fill', 'none');
        hitPath.classList.add('connection-hit');

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        
        // Group handles events now
        group.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            group.remove();
            builderState.connections = builderState.connections.filter(c => c.source !== sourceNode.dataset.nodeId || c.target !== targetNode.dataset.nodeId);
            showNotification('Connection removed', 'info');
        });

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
        
        group.appendChild(hitPath);
        group.appendChild(line);
        svg.appendChild(group);
        
        builderState.connections.push({ source: sourceNode.dataset.nodeId, target: targetNode.dataset.nodeId });

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
    if (headerClearBtn) headerClearBtn.addEventListener('click', () => clearCanvas());

    // Load Workflow Logic - DEPRECATED (Replaced by new Scenario Loader below)
    // const headerLoadBtn = document.querySelector('.canvas-header .canvas-actions [data-action="load-workflow"]');
    // if (headerLoadBtn) headerLoadBtn.addEventListener('click', () => openLoadModal());

    // Modal Elements
    const loadModal = document.getElementById('loadWorkflowModal');
    const closeModalBtn = loadModal?.querySelector('.builder-close-modal');
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

    function clearCanvas() {
        if (confirm('Are you sure you want to clear the entire workflow?')) {
            document.querySelectorAll('.workflow-node').forEach(n => n.remove());
            document.querySelectorAll('.connection-line').forEach(l => l.remove());
            builderState.connections = [];
            builderState.history = [];
            builderState.redo = [];
            updateDropZoneVisibility();
            showNotification('Canvas cleared', 'info');
        }
    }

    async function runWorkflow() {
        showNotification('Executing workflow...', 'info');
        if (window.ConsoleManager) window.ConsoleManager.log('Starting workflow execution...', 'system');
        
        const nodes = [];
        let missingData = false;

        document.querySelectorAll('.workflow-node').forEach((node) => {
            const config = node.dataset.config ? JSON.parse(node.dataset.config) : {};
            const type = node.dataset.type;
            const title = node.dataset.title || 'Untitled Node';
            const nodeId = node.dataset.nodeId;

            // Check for missing data
            if (type === 'google_sheet_read' && !config.sheetId) {
                missingData = true;
                if (window.ConsoleManager) window.ConsoleManager.log(`Node '${title}' (${nodeId}) missing Sheet ID. Using mock data.`, 'warning');
            }
            if (type === 'google_sheet_write' && !config.sheetId) {
                missingData = true;
                if (window.ConsoleManager) window.ConsoleManager.log(`Node '${title}' (${nodeId}) missing Sheet ID. Using mock data.`, 'warning');
            }
            if (type === 'google_doc_read' && !config.docId) {
                missingData = true;
                if (window.ConsoleManager) window.ConsoleManager.log(`Node '${title}' (${nodeId}) missing Doc ID. Using mock data.`, 'warning');
            }

            nodes.push({
                id: node.dataset.nodeId.replace('node-', ''),
                type: node.dataset.type,
                config: config
            });
        });

        if (missingData) {
            console.warn("Some nodes are missing configuration. System will use mock data.");
            if (window.ConsoleManager) window.ConsoleManager.log("Warning: Some nodes are missing configuration. System will use mock data.", 'warning');
        }

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
            
            // Log server-side logs
            if (window.ConsoleManager && result.logs) {
                 result.logs.forEach(log => window.ConsoleManager.log(log, 'info'));
            }

            if (window.ConsoleManager) window.ConsoleManager.log(`Execution finished. Status: ${result.status}`, result.status === 'completed' ? 'success' : 'error');

            if (result.status === 'completed') {
                showNotification('Workflow completed successfully!', 'success');
            } else {
                showNotification('Workflow failed: ' + (result.message || 'Unknown error'), 'error');
                if (window.ConsoleManager) window.ConsoleManager.log(`Error details: ${result.message || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Error executing workflow:', error);
            showNotification('Network error executing workflow', 'error');
            if (window.ConsoleManager) window.ConsoleManager.log(`Network error: ${error.message}`, 'error');
        }
    }

    // Refactored save logic to support both direct updates and modal-based creation
    function performScenarioSave(name, description, scenarioId) {
        const nodes = [];
        const nodeElements = document.querySelectorAll('.workflow-node');
        
        // Check if canvas is empty
        if (nodeElements.length === 0) {
            showNotification('Cannot save empty workflow. Add at least one node.', 'warning');
            return;
        }
        
        nodeElements.forEach((node) => {
            nodes.push({
                id: node.dataset.nodeId,
                title: node.dataset.title,
                category: node.dataset.category,
                type: node.dataset.type,
                config: node.dataset.config ? JSON.parse(node.dataset.config) : {},
                left: parseInt(node.style.left, 10) || 0,
                top: parseInt(node.style.top, 10) || 0,
                description: node.querySelector('.node-content')?.textContent.trim() || ''
            });
        });

        let connections = [];
        if (builderState.connections && builderState.connections.length > 0) {
            connections = [...builderState.connections];
        } else {
            const svg = document.getElementById('connectionLines');
            if (svg) {
                // Try wrappers first (new style)
                svg.querySelectorAll('.connection-wrapper').forEach((wrapper) => {
                    connections.push({ source: wrapper.dataset.source, target: wrapper.dataset.target });
                });
                // Fallback to lines (old style) if no wrappers found
                if (connections.length === 0) {
                    svg.querySelectorAll('.connection-line').forEach((line) => {
                        connections.push({ source: line.dataset.source, target: line.dataset.target });
                    });
                }
            }
        }

        // Ensure payload is valid
        const payload = { nodes: nodes || [], connections: connections || [] };
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const method = scenarioId ? 'PUT' : 'POST';
        const url = scenarioId ? `/api/scenarios/${scenarioId}` : '/api/scenarios';

        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                name: name,
                steps: JSON.stringify(payload),
                description: description || 'Created via Workspace Builder'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Saved successfully', 'success');
                const currentNameInput = document.querySelector('.workflow-name-input');
                if (currentNameInput) currentNameInput.value = name;
                
                // If we just created a new scenario, update state and URL
                if (!scenarioId && data.id) {
                    builderState.scenarioId = data.id;
                    const newUrl = new URL(window.location);
                    newUrl.searchParams.set('scenario_id', data.id);
                    // Clean up legacy 'id' param if present to avoid confusion
                    newUrl.searchParams.delete('id');
                    window.history.pushState({}, '', newUrl);
                }
            } else {
                showNotification('Error saving: ' + (data.message || 'Unknown error'), 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Network error saving', 'error');
        });
    }

    window.saveWorkflow = function() {
        // Determine Scenario ID
        // We prioritize builderState.scenarioId, then URL param 'scenario_id', then URL param 'id'
        const urlParams = new URLSearchParams(window.location.search);
        let scenarioId = builderState.scenarioId || urlParams.get('scenario_id') || urlParams.get('id');
        
        const currentNameInput = document.querySelector('.workflow-name-input');
        let defaultName = currentNameInput ? currentNameInput.value : 'Untitled Automation';
        
        if (scenarioId) {
            // Update existing scenario - Show confirmation
            if (!confirm(`Save changes to "${defaultName}"?`)) {
                return;
            }
            performScenarioSave(defaultName, 'Updated via Workspace Builder', scenarioId);
        } else {
            // Create new scenario - Show Modal
            const modalEl = document.getElementById('saveScenarioModal');
            if (modalEl) {
                const nameInput = document.getElementById('saveScenarioName');
                if (nameInput) nameInput.value = defaultName;
                
                // Use Bootstrap modal API
                const modal = new bootstrap.Modal(modalEl);
                modal.show();
                
                // Setup one-time click handler for the save button
                const confirmBtn = document.getElementById('confirmSaveScenarioBtn');
                // Clone to remove old listeners
                const newConfirmBtn = confirmBtn.cloneNode(true);
                confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
                
                newConfirmBtn.addEventListener('click', () => {
                    const newName = document.getElementById('saveScenarioName').value;
                    const newDesc = document.getElementById('saveScenarioDescription').value;
                    
                    if (!newName) {
                        alert('Please enter a name');
                        return;
                    }
                    
                    performScenarioSave(newName, newDesc, null);
                    modal.hide();
                });
            } else {
                // Fallback if modal missing
                const name = prompt('Enter name for this automation:', defaultName);
                if (name) performScenarioSave(name, '', null);
            }
        }
    }

    // Removed window.handleSaveOption and performSave as they are no longer needed


    // Load workflow logic
    const loadBtn = document.querySelector('button[data-action="load-workflow"]');
    if (loadBtn) {
        loadBtn.addEventListener('click', () => {
            // Fetch list of scenarios
            fetch('/api/scenarios')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    if (!data.scenarios || data.scenarios.length === 0) {
                        showNotification('No saved scenarios found.', 'info');
                        return;
                    }
                    
                    showLoadModal(data.scenarios);
                } else {
                    console.error('Server error:', data.message);
                    showNotification('Failed to fetch scenarios: ' + (data.message || 'Unknown error'), 'error');
                }
            })
            .catch(err => {
                console.error(err);
                showNotification('Network error fetching scenarios: ' + err.message, 'error');
            });
        });
    }

    function showLoadModal(scenarios) {
        // Remove existing if any
        const existing = document.getElementById('loadWorkflowModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'loadWorkflowModal';
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5); z-index: 1000;
            display: flex; align-items: center; justify-content: center;
        `;
        
        const content = document.createElement('div');
        content.style.cssText = `
            background: var(--builder-panel); padding: 20px; border-radius: 12px;
            width: 400px; max-height: 80vh; display: flex; flex-direction: column;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        `;
        
        content.innerHTML = `
            <h3 style="margin-top: 0; color: var(--builder-text);">Load Scenario</h3>
            <div style="overflow-y: auto; flex: 1; margin-bottom: 15px; border: 1px solid var(--builder-border); border-radius: 8px; max-height: 400px;">
                ${scenarios.map(s => `
                    <div class="workflow-list-item" data-id="${s.id}" style="padding: 10px; border-bottom: 1px solid var(--builder-border); cursor: pointer; transition: background 0.2s;">
                        <div style="font-weight: bold; color: var(--builder-text);">${s.name}</div>
                        <div style="font-size: 0.8rem; color: var(--builder-muted);">Created: ${new Date(s.created_at).toLocaleString()}</div>
                    </div>
                `).join('')}
            </div>
            <button id="closeLoadModal" class="action-btn" style="align-self: flex-end;">Close</button>
        `;
        
        modal.appendChild(content);
        document.body.appendChild(modal);
        
        // Event listeners
        document.getElementById('closeLoadModal').addEventListener('click', () => modal.remove());
        
        modal.querySelectorAll('.workflow-list-item').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.dataset.id;
                const scenario = scenarios.find(s => s.id == id);
                if (scenario) {
                    if (confirm(`Load "${scenario.name}"? Unsaved changes will be lost.`)) {
                        // Parse steps if string
                        let steps = scenario.steps;
                        if (typeof steps === 'string') {
                            try {
                                steps = JSON.parse(steps);
                            } catch(e) {
                                console.error("Error parsing steps", e);
                                steps = { nodes: [], connections: [] };
                            }
                        }
                        
                        // Update name input BEFORE loading data
                        const nameInput = document.querySelector('.workflow-name-input');
                        if (nameInput) {
                            nameInput.value = scenario.name || 'Untitled Workflow';
                        }
                        
                        loadWorkflowData(steps);
                        showNotification(`Loaded: ${scenario.name}`, 'success');
                        
                        // Update URL
                        const newUrl = new URL(window.location);
                        newUrl.searchParams.set('scenario_id', scenario.id);
                        newUrl.searchParams.delete('id'); // Remove legacy id
                        window.history.pushState({}, '', newUrl);
                        
                        // Update state
                        builderState.scenarioId = scenario.id;
                        
                        modal.remove();
                    }
                }
            });
            
            // Add hover effect manually since inline styles are tricky for hover
            item.addEventListener('mouseenter', () => item.style.background = 'var(--builder-bg)');
            item.addEventListener('mouseleave', () => item.style.background = 'transparent');
        });
    }

    // Load workflow if ID is present
    const urlParams = new URLSearchParams(window.location.search);
    const workflowId = urlParams.get('id');
    
    if (workflowId) {
        // Try to load as Scenario first
        fetch(`/api/scenarios/${workflowId}`)
            .then(res => res.json())
            .then(data => {
                if (data.success && data.scenario) {
                    // It is a scenario
                    const scenario = data.scenario;
                    showNotification(`Loaded Scenario: ${scenario.name}`, 'success');
                    
                    // Update name input
                    const nameInput = document.querySelector('.workflow-name-input');
                    if (nameInput) nameInput.value = scenario.name;
                    
                    // Load data if exists
                    if (scenario.steps) {
                        try {
                            const workflowData = JSON.parse(scenario.steps);
                            loadWorkflowData(workflowData);
                        } catch (e) {
                            console.error('Error parsing scenario steps:', e);
                        }
                    }
                    
                    // Store scenario ID for saving
                    builderState.scenarioId = scenario.id;
                } else {
                    // Fallback to Workflow loading
                    loadWorkflowById(workflowId);
                }
            })
            .catch(() => {
                // Fallback to Workflow loading
                loadWorkflowById(workflowId);
            });
    }

    function loadWorkflowById(id) {
        fetch('/api/workflows')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const workflow = data.workflows.find(w => w.id == id);
                if (workflow && workflow.data) {
                    loadWorkflowData(workflow.data);
                    showNotification(`Loaded workflow: ${workflow.name}`, 'success');
                    const nameInput = document.querySelector('.workflow-name-input');
                    if (nameInput) nameInput.value = workflow.name;
                }
            }
        });
    }

    function loadWorkflowData(data) {
        // Clear canvas
        document.querySelectorAll('.workflow-node').forEach(n => n.remove());
        document.querySelectorAll('.connection-line').forEach(l => l.remove());
        document.querySelectorAll('.connection-wrapper').forEach(w => w.remove());
        builderState.connections = [];
        
        // Handle null or undefined data
        if (!data) {
            console.error('loadWorkflowData: data is null or undefined');
            showNotification('Error loading workflow: Invalid data', 'error');
            return;
        }
        
        // Restore nodes
        if (data.nodes && data.nodes.length > 0) {
            data.nodes.forEach(nodeData => {
                const node = createWorkflowNode({
                    name: nodeData.title,
                    category: nodeData.category,
                    type: nodeData.type,
                    description: nodeData.description,
                    icon: getIconForCategory(nodeData.category)
                }, { x: nodeData.left + 100, y: nodeData.top + 40 }); 
                
                if (node) {
                    node.dataset.nodeId = nodeData.id;
                    // Restore config if present
                    if (nodeData.config) {
                        node.dataset.config = JSON.stringify(nodeData.config);
                    }
                    
                    // Update counter to avoid collision and update visual badge
                    const numId = parseInt(nodeData.id.replace('node-', ''));
                    if (!isNaN(numId)) {
                        if (numId > builderState.nodeCounter) {
                            builderState.nodeCounter = numId;
                        }
                        const badge = node.querySelector('.node-id-badge');
                        if (badge) {
                            badge.textContent = `#${numId}`;
                        }
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
            warnIfGoogleNode(type);

            let html = '';
            
            if (type === 'google_sheet_read') {
                html = `
                    <label>Spreadsheet ID</label>
                    <input type="text" id="cfg-sheet-id" value="${config.sheetId || ''}">
                    <button type="button" class="action-btn" id="cfg-sheet-picker">Browse Drive</button>
                    <label>Range</label>
                    <input type="text" id="cfg-range" value="${config.range || 'Sheet1!A1:B10'}">
                `;
            } else if (type === 'google_sheet_write') {
                html = `
                    <label>Spreadsheet ID</label>
                    <input type="text" id="cfg-sheet-id" value="${config.sheetId || ''}">
                    <button type="button" class="action-btn" id="cfg-sheet-picker">Browse Drive</button>
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
                    <button type="button" class="action-btn" id="cfg-doc-picker">Browse Drive</button>
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
            } else if (type === 'invoice_ocr') {
                html = `
                    <label>File URL / Path</label>
                    <div style="display: flex; gap: 5px;">
                        <input type="text" id="cfg-file-url" value="${config.fileUrl || ''}" placeholder="{{parent.file_url}}" style="flex: 1;">
                        <button id="cfg-upload-btn" class="action-btn" style="width: auto;" title="Upload Invoice"><i class="fas fa-upload"></i></button>
                    </div>
                    <input type="file" id="cfg-file-input" style="display: none;" accept="image/*,application/pdf">
                    <small>Leave empty to use parent output automatically</small>
                `;
            } else if (type === 'invoice_forecast') {
                html = `
                    <label>Sales Data (JSON)</label>
                    <textarea id="cfg-data" style="height: 80px;" placeholder="{{parent.data}}">${config.data || ''}</textarea>
                    <small>JSON object with "series" array</small>
                `;
            }

            settingsContainer.innerHTML = html;

            const uploadBtn = document.getElementById('cfg-upload-btn');
            const fileInput = document.getElementById('cfg-file-input');
            if (uploadBtn && fileInput) {
                uploadBtn.addEventListener('click', () => fileInput.click());
                fileInput.addEventListener('change', () => {
                    if (fileInput.files.length > 0) {
                        const file = fileInput.files[0];
                        const formData = new FormData();
                        formData.append('file', file);
                        
                        // Show loading state
                        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                        uploadBtn.disabled = true;
                        
                        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
                        
                        fetch('/api/workflow/upload_file', {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrfToken
                            },
                            body: formData
                        })
                        .then(res => res.json())
                        .then(data => {
                            if (data.success) {
                                document.getElementById('cfg-file-url').value = data.path;
                                showNotification('File uploaded successfully', 'success');
                            } else {
                                showNotification('Upload failed: ' + data.error, 'error');
                            }
                        })
                        .catch(err => {
                            console.error(err);
                            showNotification('Upload network error', 'error');
                        })
                        .finally(() => {
                            uploadBtn.innerHTML = '<i class="fas fa-upload"></i>';
                            uploadBtn.disabled = false;
                        });
                    }
                });
            }

            const sheetPickerBtn = document.getElementById('cfg-sheet-picker');
            const docPickerBtn = document.getElementById('cfg-doc-picker');
            if (sheetPickerBtn) {
                sheetPickerBtn.addEventListener('click', () => {
                    openGooglePicker({ type: 'sheets', targetInputId: 'cfg-sheet-id' });
                });
            }
            if (docPickerBtn) {
                docPickerBtn.addEventListener('click', () => {
                    openGooglePicker({ type: 'docs', targetInputId: 'cfg-doc-id' });
                });
            }
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
            } else if (type === 'invoice_ocr') {
                config.fileUrl = document.getElementById('cfg-file-url')?.value;
            } else if (type === 'invoice_forecast') {
                config.data = document.getElementById('cfg-data')?.value;
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
            // Do not auto-expand when minimized; allow dragging in minimized state
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

    // --- Tutorial Logic ---
    window.showTutorialModal = function() {
        const modalEl = document.getElementById('tutorialModal');
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
            
            // Handle "Don't show again" checkbox
            const checkbox = document.getElementById('dontShowAgain');
            if (checkbox) {
                checkbox.addEventListener('change', (e) => {
                    if (e.target.checked) {
                        localStorage.setItem('hasSeenBuilderTutorial', 'true');
                    } else {
                        localStorage.removeItem('hasSeenBuilderTutorial');
                    }
                });
            }
            
            modalEl.addEventListener('hidden.bs.modal', () => {
                if (document.getElementById('dontShowAgain')?.checked) {
                    localStorage.setItem('hasSeenBuilderTutorial', 'true');
                }
            });
        }
    };

    window.startInteractiveTutorial = function() {
        const modalEl = document.getElementById('tutorialModal');
        if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }
        localStorage.setItem('hasSeenBuilderTutorial', 'true');
        
        // Show the new tour steps modal
        const tourModalEl = document.getElementById('tourStepsModal');
        if (tourModalEl) {
            const tourModal = new bootstrap.Modal(tourModalEl);
            tourModal.show();
        }
    };

    // Auto-show tutorial
    const hasSeenTutorial = localStorage.getItem('hasSeenBuilderTutorial');
    if (!hasSeenTutorial) {
        setTimeout(() => {
            if (window.showTutorialModal) window.showTutorialModal();
        }, 1000);
    }
});
