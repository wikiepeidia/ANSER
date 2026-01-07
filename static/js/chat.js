document.addEventListener('DOMContentLoaded', function() {
    const chatWidget = document.getElementById('ai-chat-widget');
    const toggleBtn = document.getElementById('ai-chat-toggle');
    const chatWindow = document.getElementById('ai-chat-window');
    const closeBtn = document.getElementById('ai-chat-minimize');
    const input = document.getElementById('ai-chat-input');
    const sendBtn = document.getElementById('ai-chat-send');
    const messagesContainer = document.getElementById('ai-chat-messages');

    // Toggle Chat Window
    function toggleChat() {
        const isHidden = chatWindow.hasAttribute('hidden');
        if (isHidden) {
            chatWindow.removeAttribute('hidden');
            input.focus();
        } else {
            chatWindow.setAttribute('hidden', '');
        }
    }

    toggleBtn.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    // Auto-resize textarea
    input.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value === '') {
            this.style.height = 'auto';
        }
    });

    // Send Message Logic
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Add User Message
        addMessage(text, 'user');
        input.value = '';
        input.style.height = 'auto';
        input.disabled = true; // Disable input while waiting

        showTypingIndicator();

        try {
            // Get CSRF Token
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

            const response = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();
            removeTypingIndicator();

            if (response.ok) {
                // Handle different action types
                if (data.action === 'chat') {
                    addMessage(data.response, 'bot');
                } else if (data.action === 'data') {
                    addMessage(data.response, 'bot');
                    // Optionally render a table or chart here if data.meta contains structured data
                } else if (data.action === 'automation') {
                    addMessage(data.response, 'bot');
                    addMessage("🤖 Automation Blueprint Created! Check your workflows.", 'bot');
                } else {
                    // Fallback
                    addMessage(data.response || "Received response", 'bot');
                }
            } else {
                addMessage("Sorry, I encountered an error connecting to the AI service.", 'bot');
                console.error('AI Error:', data);
            }

        } catch (error) {
            removeTypingIndicator();
            addMessage("Network error. Please try again later.", 'bot');
            console.error('Network Error:', error);
        } finally {
            input.disabled = false;
            input.focus();
        }
    }

    sendBtn.addEventListener('click', sendMessage);

    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Helper: Add Message to UI
    function addMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `ai-message ai-message-${sender}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'ai-message-content';
        contentDiv.textContent = text;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'ai-message-time';
        const now = new Date();
        timeDiv.textContent = `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;
        
        msgDiv.appendChild(contentDiv);
        msgDiv.appendChild(timeDiv);
        
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    // Helper: Scroll to bottom
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Helper: Typing Indicator
    let typingDiv = null;
    function showTypingIndicator() {
        typingDiv = document.createElement('div');
        typingDiv.className = 'ai-message ai-message-bot';
        typingDiv.innerHTML = `
            <div class="ai-message-content" style="padding: 8px 12px;">
                <i class="fas fa-ellipsis-h fa-fade"></i>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        if (typingDiv) {
            typingDiv.remove();
            typingDiv = null;
        }
    }
});
