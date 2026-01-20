document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 Chat Script Final Loaded");

    const input = document.getElementById('ai-chat-input');
    const sendBtn = document.getElementById('ai-chat-send');
    const messagesContainer = document.getElementById('ai-chat-messages');
    const toggleBtn = document.getElementById('ai-chat-toggle');
    const chatWindow = document.getElementById('ai-chat-window');
    const closeBtn = document.getElementById('ai-chat-minimize');
    
    // File Upload Elements
    const fileInput = document.getElementById('ai-chat-file-input');
    const attachBtn = document.getElementById('ai-chat-attach-btn');
    const filePreview = document.getElementById('ai-chat-file-preview');
    const fileNameDisplay = document.getElementById('ai-chat-file-name');
    const clearFileBtn = document.getElementById('ai-chat-clear-file');

    let isProcessing = false;
    let currentFile = null;

    // --- 1. HISTORY LOADER ---
    async function loadHistory() {
        if (!messagesContainer) return;
        try {
            const res = await fetch('/api/ai/history');
            const data = await res.json();
            if (data.history && data.history.length > 0) {
                messagesContainer.innerHTML = ''; 
                data.history.forEach(msg => {
                    const role = (msg.role === 'user') ? 'user' : 'bot';
                    addMessage(msg.content, role);
                });
                scrollToBottom();
            }
        } catch(e) { console.error("History Error:", e); }
    }
    loadHistory();

    // --- 2. TOGGLE ---
    function toggleChat() {
        if(!chatWindow) return;
        chatWindow.hasAttribute('hidden') ? chatWindow.removeAttribute('hidden') : chatWindow.setAttribute('hidden', '');
    }
    if(toggleBtn) toggleBtn.addEventListener('click', toggleChat);
    if(closeBtn) closeBtn.addEventListener('click', toggleChat);

    // --- 3. FILE UPLOAD ---
    if (attachBtn && fileInput) {
        attachBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            filePreview.style.display = 'flex';
            fileNameDisplay.innerHTML = '⏳ Uploading...';
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
                const res = await fetch('/api/ai/upload', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken || '' },
                    body: formData
                });
                const data = await res.json();
                if (res.ok) {
                    currentFile = data.filename;
                    fileNameDisplay.innerHTML = '✅ ' + file.name;
                } else {
                    fileNameDisplay.innerHTML = '❌ Failed';
                }
            } catch (e) {
                fileNameDisplay.innerHTML = '❌ Error';
            }
        });
        if (clearFileBtn) clearFileBtn.addEventListener('click', () => {
            fileInput.value = '';
            filePreview.style.display = 'none';
            currentFile = null;
        });
    }

    // --- 4. UI HELPERS ---
    function scrollToBottom() {
        if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function addMessage(text, role) {
        // Try parsing JSON for Workflow cards (only for bot)
        if (role === 'bot') {
            try {
                if (typeof text === 'string' && text.trim().startsWith('{')) {
                    const data = JSON.parse(text);
                    if (data.action === 'create_workflow') {
                        renderWorkflowCard(data.text || `Created workflow: ${data.name}`, data.id);
                        return;
                    }
                }
            } catch(e) {}
        }

        const div = document.createElement('div');
        div.className = `ai-message ai-message-${role}`;
        div.innerHTML = typeof marked !== 'undefined' ? marked.parse(text) : text;
        messagesContainer.appendChild(div);
        scrollToBottom();
    }

    // THIS IS THE LOGIC THAT PREVENTS JSON DUMPING
    function renderWorkflowCard(text, id) {
        let btnHtml = '';
        if (id && id !== 'undefined') {
            btnHtml = `<a href="/workspace/builder?load=${id}" class="wf-btn">Open Builder</a>`;
        } else {
            btnHtml = `<span class="wf-btn" style="opacity:0.5; cursor:not-allowed;">ID Missing - Check History</span>`;
        }

        const div = document.createElement('div');
        div.className = 'ai-message ai-message-bot';
        div.innerHTML = `
            <div class="workflow-card">
                <div class="wf-title">✅ Automation Created</div>
                <div class="wf-desc">${typeof marked !== 'undefined' ? marked.parse(text) : text}</div>
                ${btnHtml}
            </div>`;
        messagesContainer.appendChild(div);
        scrollToBottom();
    }

    // --- 5. DEEP RESEARCH UI ---
    const RESEARCH_STEPS = [
        { icon: "🧠", text: "Analyzing Intent..." },
        { icon: "🗄️", text: "Querying Database..." },
        { icon: "📝", text: "Designing Workflow..." },
        { icon: "⚙️", text: "Writing Code..." },
        { icon: "💾", text: "Saving Workspace..." }
    ];

    function showDeepResearchUI() {
        const id = 'process-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'agent-process-container';
        div.style.display = 'block';
        div.innerHTML = `
            <div class="process-header">
                <div class="spinner-ring"></div>
                <span id="${id}-status">Thinking...</span>
            </div>
            <div class="process-steps" id="${id}-steps"></div>
        `;
        messagesContainer.appendChild(div);
        scrollToBottom();
        return id;
    }

    function updateDeepResearchStep(id, stepIndex) {
        const container = document.getElementById(id + '-steps');
        const status = document.getElementById(id + '-status');
        if (!container) return;
        if (stepIndex < RESEARCH_STEPS.length) {
            const step = RESEARCH_STEPS[stepIndex];
            if(status) status.innerText = step.text;
            const stepDiv = document.createElement('div');
            stepDiv.className = 'step-item active';
            stepDiv.innerHTML = `<span class="step-icon">${step.icon}</span> <span>${step.text}</span>`;
            container.appendChild(stepDiv);
            if (container.children.length > 1) {
                const prev = container.children[container.children.length - 2];
                prev.classList.remove('active');
                prev.querySelector('.step-icon').innerText = '✅';
            }
            scrollToBottom();
        }
    }

    function removeUI(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    // --- 6. POLLING LOGIC ---
    async function pollJob(jobId, uiId, uiTimer) {
        const pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/ai/status/${jobId}`);
                const data = await res.json();

                if (data.status === 'completed') {
                    // DONE
                    clearInterval(pollInterval);
                    if (uiTimer) clearInterval(uiTimer);
                    removeUI(uiId);
                    isProcessing = false;
                    input.disabled = false;
                    
                    // SMART SWITCH: JSON vs Card
                    if (data.action && data.action.action === 'workflow_created') {
                        renderWorkflowCard(data.response, data.action.id);
                    } else {
                        addMessage(data.response, 'bot');
                    }
                    input.focus();
                } 
                else if (data.status === 'failed') {
                    // FAILED
                    clearInterval(pollInterval);
                    if (uiTimer) clearInterval(uiTimer);
                    removeUI(uiId);
                    isProcessing = false;
                    input.disabled = false;
                    addMessage(`❌ Error: ${data.error}`, 'bot');
                }
            } catch(e) { console.error(e); }
        }, 1500);
    }

    // --- 7. SEND LOGIC ---
    async function sendMessage() {
        const text = input.value.trim();
        if(!text && !currentFile) return;
        if (isProcessing) return;

        addMessage(text || (currentFile ? '[Sent File]' : ''), 'user');
        input.value = '';
        input.disabled = true;
        isProcessing = true;
        if(fileInput) fileInput.value = '';
        if(filePreview) filePreview.style.display = 'none';

        // UI Choice
        const complexKeywords = /tạo|create|build|workflow|quy trình|tự động|auto|doanh thu|sales/i;
        let uiId = null;
        let uiTimer = null;
        let step = 0;

        if (complexKeywords.test(text)) {
            uiId = showDeepResearchUI();
            uiTimer = setInterval(() => updateDeepResearchStep(uiId, step++), 1500);
        } else {
            // Simple typing indicator
            uiId = 'typing-' + Date.now();
            const div = document.createElement('div');
            div.id = uiId;
            div.className = 'ai-message ai-message-bot';
            div.style.color = '#888';
            div.style.fontStyle = 'italic';
            div.innerHTML = `<span class="spinner-ring" style="display:inline-block; width:10px; height:10px; border-width:1px; margin-right:5px;"></span> Project A is typing...`;
            messagesContainer.appendChild(div);
            scrollToBottom();
        }

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            const res = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken || '' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();

            if (data.status === 'completed') {
                // Instant
                if (uiTimer) clearInterval(uiTimer);
                removeUI(uiId);
                isProcessing = false;
                input.disabled = false;
                addMessage(data.response, 'bot');
            } else if (data.job_id) {
                // Async
                pollJob(data.job_id, uiId, uiTimer);
            } else {
                throw new Error("Invalid response");
            }
        } catch (e) {
            if (uiTimer) clearInterval(uiTimer);
            removeUI(uiId);
            isProcessing = false;
            input.disabled = false;
            addMessage(`❌ Error: ${e.message}`, 'bot');
        }
    }

    if(sendBtn) sendBtn.addEventListener('click', sendMessage);
    if(input) input.addEventListener('keypress', e => { if(e.key==='Enter') sendMessage(); });
});