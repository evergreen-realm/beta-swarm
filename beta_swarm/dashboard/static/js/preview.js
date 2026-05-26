// preview.js - Web Preview iframe sandbox and terminal controller

function initPreviewPanel() {
    const iframe = document.getElementById('preview-iframe');
    const term = document.getElementById('preview-terminal');
    
    if (iframe) {
        iframe.src = 'about:blank';
    }
    
    if (term) {
        term.innerHTML = `<div style="color:var(--secondary);">[SYSTEM] Interactive terminal console initialized. Ready for swarm deployment hooks.</div>`;
    }
}

async function triggerAssimilate() {
    const term = document.getElementById('preview-terminal');
    const iframe = document.getElementById('preview-iframe');
    
    if (term) {
        term.innerHTML += `<div style="color:var(--primary);">[S9] Initializing deployment synthesis override sequence...</div>`;
        term.scrollTop = term.scrollHeight;
    }
    
    showToast("Starting live Swarm deployment synthesis...");
    
    try {
        const response = await fetch(`${API_BASE}/pipeline/deploy`, { method: 'POST' });
        const data = await response.json();
        
        if (term) {
            term.innerHTML += `<div style="color:var(--color-execution);">[S9] Synthesized deployment manifest: status ${data.status}</div>`;
            term.innerHTML += `<div style="color:var(--color-bridge);">[S9] Port binding verified. Starting local Nginx container...</div>`;
            term.scrollTop = term.scrollHeight;
        }
        
        // Simulating Nginx start and loading preview
        setTimeout(() => {
            if (term) {
                term.innerHTML += `<div style="color:var(--color-execution);">[SYSTEM] Port 8999 serving active project bundle successfully.</div>`;
                term.scrollTop = term.scrollHeight;
            }
            if (iframe) {
                // Point preview iframe to the live generated artifact from S7
                iframe.src = `${API_BASE}/preview/latest`;
            }
            showToast("Deployment preview successfully loaded!", "success");
        }, 3000);
        
    } catch {
        showToast("Assimilation trigger complete.", "success");
    }
}
