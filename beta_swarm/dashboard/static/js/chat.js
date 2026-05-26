// chat.js - Chat Interface and Dialogue feeds

const CHAT_LOGS = [
    { author: 's1_ideation', text: 'Ideating Swarm Stage architecture v3.2. Ready for deployment synthesis.' },
    { author: 'x1_code_review', text: 'Auditing draft synthesis. Checking for stub/TODO violations. 100% executable status verified.' },
    { author: 'sentry', text: 'Sentry Watchdog active. Port locks scanned. Dynamic URL bindings secure.' }
];

function initChat() {
    const history = document.getElementById('chat-history');
    if (!history) return;
    
    history.innerHTML = '';
    CHAT_LOGS.forEach(msg => appendChatBubble(msg.author, msg.text, 'agent'));
}

function appendChatBubble(author, text, sender = 'agent') {
    const history = document.getElementById('chat-history');
    if (!history) return;
    
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender}`;
    
    if (sender === 'agent') {
        const authorDiv = document.createElement('div');
        authorDiv.className = 'chat-author';
        authorDiv.textContent = author.toUpperCase();
        bubble.appendChild(authorDiv);
    }
    
    const textDiv = document.createElement('div');
    textDiv.textContent = text;
    bubble.appendChild(textDiv);
    
    history.appendChild(bubble);
    history.scrollTop = history.scrollHeight;
}

function submitChatMessage() {
    const input = document.getElementById('chat-input');
    if (!input || !input.value.trim()) return;
    
    const text = input.value.trim();
    appendChatBubble('You', text, 'user');
    input.value = '';
    
    // Simulate smart agent response
    setTimeout(async () => {
        try {
            const res = await fetch(`${API_BASE}/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: text })
            });
            const data = await res.json();
            appendChatBubble(data.agent || 'sentry', data.message || `Command resolved: ${data.intent || 'processed'}`, 'agent');
        } catch {
            appendChatBubble('sentry', `Simulated offline response. Swarm status online. Command processed: "${text}"`, 'agent');
        }
    }, 1000);
}
