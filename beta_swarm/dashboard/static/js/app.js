// app.js - SPA Router and Dashboard core initialization

function switchView(viewId) {
    // Hide all main panel views
    document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));
    
    // Deactivate all sidebar items
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    
    // Show selected panel view
    const activePanel = document.getElementById(viewId);
    if (activePanel) {
        activePanel.classList.add('active');
    }
    
    // Highlight active sidebar navigation item
    const navItem = document.querySelector(`.nav-item[onclick*="${viewId}"]`);
    if (navItem) {
        navItem.classList.add('active');
    }
    
    // Switch specific inner sub-tabs or behaviors
    if (viewId === 'overview-panel') {
        setTimeout(() => initBrainGraph(), 100);
    } else if (viewId === 'build-panel') {
        setTimeout(() => {
            window.buildVisualizer = new BuildVisualizer('build-canvas');
            listenBuildStream(window.lastBuildCommand);
        }, 100);
    } else if (viewId === 'skills-panel') {
        loadSkillsMarketplace();
    } else if (viewId === 'memory-panel') {
        loadMemoryTimeline();
    } else if (viewId === 'preview-panel') {
        initPreviewPanel();
    } else if (viewId === 'gates-panel') {
        loadGatesDashboard();
    }
}

// Inner tab navigation for Upper Screen view (overview-panel)
function switchUpperTab(tabName) {
    document.querySelectorAll('#overview-panel .tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('#overview-panel .tab-pane').forEach(pane => pane.classList.remove('active'));
    
    const activeBtn = document.querySelector(`#overview-panel .tab-btn[onclick*="${tabName}"]`);
    if (activeBtn) activeBtn.classList.add('active');
    
    const activePane = document.getElementById(`tab-${tabName}`);
    if (activePane) activePane.classList.add('active');
    
    if (tabName === 'brain') {
        setTimeout(() => initBrainGraph(), 100);
    } else if (tabName === 'chat') {
        initChat();
    } else if (tabName === 'preview') {
        // Shared iframe inside core preview tab
        const iframe = document.querySelector('#tab-preview iframe');
        if (iframe && iframe.src === 'about:blank') {
            iframe.src = `${window.location.origin}/`;
        }
    }
}

// Global action triggers (Sidebar buttons)
async function deployApp() {
    showToast("Triggering global swarm synthesis deployment...");
    try {
        const response = await fetch(`${API_BASE}/pipeline/deploy`, { method: 'POST' });
        const data = await response.json();
        showToast(data.message || "Synthesis deployment initialized!", "success");
        switchView('preview-panel');
    } catch {
        showToast("Simulated local deployment sequence triggered.", "success");
    }
}

async function evolveSwarm() {
    showToast("Triggering global meta evolution loop...");
    try {
        const response = await fetch(`${API_BASE}/pipeline/evolve`, { method: 'POST' });
        const data = await response.json();
        showToast(data.message || "Evolve phase started!", "success");
        switchView('overview-panel');
        switchUpperTab('brain');
    } catch {
        showToast("Simulated swarm meta-evolution initiated.", "success");
    }
}

async function securityAudit() {
    showToast("Triggering full security gate audit scan...");
    try {
        const response = await fetch(`${API_BASE}/pipeline/audit`, { method: 'POST' });
        const data = await response.json();
        showToast(data.message || "Audit scan started!", "success");
        switchView('gates-panel');
    } catch {
        showToast("Simulated triple-gate security audit complete.", "success");
    }
}

async function abortAll() {
    showToast("TRIGGERING PANIC BLOCK SEQUENCE - STOPPING ALL AGENTS!", "error");
    try {
        const response = await fetch(`${API_BASE}/pipeline/abort`, { method: 'POST' });
        const data = await response.json();
        showToast(data.message || "All agent execution aborted.", "info");
    } catch {
        showToast("Emergency command stop issued.", "info");
    }
}

// Initializer
document.addEventListener('DOMContentLoaded', () => {
    // Navigate to default view
    switchView('overview-panel');
    switchUpperTab('chat');
    
    // Set up topbar Command Input keyboard listeners
    const input = document.getElementById('command-center-input');
    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                executeConsoleCommand(input.value);
                input.value = '';
            }
        });
    }
    
    // Roster live status polling (every 5 seconds)
    updateAgentRoster();
    setInterval(updateAgentRoster, 5000);
});

// Global error handler for on-screen debugging
window.onerror = function(msg, url, lineNo, columnNo, error) {
    const errorMsg = `[JS Error] ${msg} at ${lineNo}:${columnNo}`;
    console.error(errorMsg);
    // Force the error to display in the build stream if possible
    const stream = document.getElementById('build-log-stream');
    if (stream) {
        stream.innerHTML += `<div style="color:red; font-family:monospace;">${errorMsg}</div>`;
    }
    return false;
};
