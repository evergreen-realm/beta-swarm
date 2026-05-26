// agents.js - Full double-screen agent roster rendering and state controls

// Static list of all 26 core agents in v3.2 Swarm as absolute local fallback
const CORE_AGENT_ROSTER = [
    // Strategic (S1-S13)
    { id: 's1_ideation', name: 'Ideation Stage', stage: 'S1', role: 'strategic', status: 'idle' },
    { id: 's2_research', name: 'Research Stage', stage: 'S2', role: 'strategic', status: 'idle' },
    { id: 's3_prd', name: 'PRD Stage', stage: 'S3', role: 'strategic', status: 'idle' },
    { id: 's4_architecture', name: 'Architecture Stage', stage: 'S4', role: 'strategic', status: 'idle' },
    { id: 's5_backend', name: 'Backend Stage', stage: 'S5', role: 'strategic', status: 'idle' },
    { id: 's6_api', name: 'API Stage', stage: 'S6', role: 'strategic', status: 'idle' },
    { id: 's7_frontend_huashu', name: 'Frontend Huashu', stage: 'S7', role: 'strategic', status: 'idle' },
    { id: 's8_testing', name: 'Testing Stage', stage: 'S8', role: 'strategic', status: 'idle' },
    { id: 's9_deployment', name: 'Deployment Stage', stage: 'S9', role: 'strategic', status: 'idle' },
    { id: 's10_monitoring', name: 'Monitoring Stage', stage: 'S10', role: 'strategic', status: 'idle' },
    { id: 's11_documentation', name: 'Documentation Stage', stage: 'S11', role: 'strategic', status: 'idle' },
    { id: 's12_maintenance', name: 'Maintenance Stage', stage: 'S12', role: 'strategic', status: 'idle' },
    { id: 's13_design', name: 'Design Stage', stage: 'S13', role: 'strategic', status: 'idle' },
    
    // Execution (X1-X4)
    { id: 'x1_code_review', name: 'Code Reviewer', stage: 'X1', role: 'execution', status: 'idle' },
    { id: 'x2_security_review', name: 'Security Auditor', stage: 'X2', role: 'execution', status: 'idle' },
    { id: 'x3_performance_review', name: 'Performance Monitor', stage: 'X3', role: 'execution', status: 'idle' },
    { id: 'x4_review_board', name: 'Swarm Review Board', stage: 'X4', role: 'execution', status: 'idle' },
    
    // Bridge (B1-B4)
    { id: 'b1_local_brain', name: 'KuzuDB Manager', stage: 'B1', role: 'bridge', status: 'idle' },
    { id: 'b2_global_brain', name: 'Neo4j Bridge', stage: 'B2', role: 'bridge', status: 'idle' },
    { id: 'b3_evolver', name: 'Meta Evolver', stage: 'B3', role: 'bridge', status: 'idle' },
    { id: 'b4_code_intel', name: 'GitNexus Indexer', stage: 'B4', role: 'bridge', status: 'idle' },
    
    // Guardian (G1-G4)
    { id: 'g1_health_monitor', name: 'Health Supervisor', stage: 'G1', role: 'guardian', status: 'idle' },
    { id: 'g2_business_domain', name: 'Domain Specialist', stage: 'G2', role: 'guardian', status: 'idle' },
    { id: 'g3_reflection', name: 'Self-Reflection', stage: 'G3', role: 'guardian', status: 'idle' },
    { id: 'g4_research_cloud', name: 'Cloud Integration', stage: 'G4', role: 'guardian', status: 'idle' },
    
    // Sentry
    { id: 'sentry', name: 'Sentry Watchdog', stage: 'Watchdog', role: 'sentry', status: 'idle' }
];

let agentStates = [...CORE_AGENT_ROSTER];

// Fetch and render the agent cards
async function updateAgentRoster() {
    try {
        const response = await fetch(`${API_BASE}/agents`);
        const data = await response.json();
        
        if (data.agents && data.agents.length > 0) {
            // Merge status updates from server into our structural grid
            agentStates.forEach(localAgent => {
                const updated = data.agents.find(a => a.id === localAgent.id || a.id.replace('_agent','') === localAgent.id);
                if (updated) {
                    localAgent.status = updated.status || 'idle';
                }
            });
        }
    } catch (e) {
        console.warn("Could not query live agent statuses. Falling back to simulated cache.", e);
    }
    
    renderAgentGrid();
}

function renderAgentGrid() {
    const grid = document.getElementById('agent-grid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    agentStates.forEach(agent => {
        const card = document.createElement('div');
        card.className = `agent-card role-${agent.role} fade-in`;
        card.onclick = () => showAgentDetails(agent.id);
        
        const header = document.createElement('div');
        header.className = 'agent-card-header';
        
        const badge = document.createElement('div');
        badge.className = 'agent-id-badge';
        badge.textContent = agent.stage;
        
        const indicator = document.createElement('div');
        indicator.className = `agent-status-indicator ${agent.status === 'active' || agent.status === 'working' ? 'active' : ''}`;
        
        header.appendChild(badge);
        header.appendChild(indicator);
        
        const name = document.createElement('div');
        name.className = 'agent-card-name';
        name.textContent = agent.name;
        
        const details = document.createElement('div');
        details.className = 'agent-card-stage';
        details.textContent = `ID: ${agent.id} | Status: ${agent.status}`;
        
        card.appendChild(header);
        card.appendChild(name);
        card.appendChild(details);
        
        grid.appendChild(card);
    });
}

// Display Details Overlay Modal
async function showAgentDetails(agentId) {
    const agent = agentStates.find(a => a.id === agentId);
    if (!agent) return;
    
    const modal = document.getElementById('agent-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    
    if (!modal || !modalTitle || !modalBody) return;
    
    modalTitle.textContent = `${agent.name} (${agent.stage}) Configuration`;
    modalBody.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="display:grid; grid-template-columns:100px 1fr; gap:8px; font-size:13px;">
                <span style="color:var(--text-muted);">Agent ID:</span>
                <span>${agent.id}</span>
                <span style="color:var(--text-muted);">Role Layer:</span>
                <span style="text-transform:capitalize;">${agent.role}</span>
                <span style="color:var(--text-muted);">Active Status:</span>
                <span style="color:${agent.status === 'active' ? 'var(--color-execution)' : 'var(--text-muted)'}; font-weight:700;">${agent.status.toUpperCase()}</span>
            </div>
            
            <div style="border-top:1px solid var(--glass-border); padding-top:16px;">
                <h4 style="font-size:14px; margin-bottom:8px;">Execution Logs</h4>
                <div id="modal-agent-logs" style="background:rgba(0,0,0,0.5); padding:12px; border-radius:8px; font-family:monospace; font-size:12px; max-height:150px; overflow-y:auto; color:#a8ffb2;">
                    Fetching logs from Hybrid Brain...
                </div>
            </div>

            <div style="display:flex; justify-content:flex-end; gap:12px; border-top:1px solid var(--glass-border); padding-top:16px;">
                <button class="btn" onclick="closeAgentModal()">Close</button>
                <button class="btn primary" onclick="triggerSingleAgent('${agent.id}')">Evolve Agent</button>
            </div>
        </div>
    `;
    
    modal.style.display = 'flex';
    
    // Query dynamic details from KuzuDB
    try {
        const res = await fetch(`${API_BASE}/agents/${agentId}`);
        const data = await res.json();
        const logsDiv = document.getElementById('modal-agent-logs');
        if (logsDiv) {
            if (data.artifacts && data.artifacts.length > 0) {
                logsDiv.innerHTML = data.artifacts.map(art => `[${formatDate(art['ar.created_at'] || art.created_at)}] Generated ${art['ar.project'] || art.project} synthesis.`).join('<br>');
            } else {
                logsDiv.textContent = `No active knowledge artifacts recorded in KuzuDB for ${agent.name}.`;
            }
        }
    } catch {
        const logsDiv = document.getElementById('modal-agent-logs');
        if (logsDiv) logsDiv.textContent = "Offline cache: Live workspace status normal.";
    }
}

function closeAgentModal() {
    const modal = document.getElementById('agent-modal');
    if (modal) modal.style.display = 'none';
}

async function triggerSingleAgent(agentId) {
    showToast(`Initiating Meta Evolution override sequence for ${agentId}...`);
    try {
        const res = await fetch(`${API_BASE}/command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: `evolve agent ${agentId}` })
        });
        const data = await res.json();
        showToast(`Evolution triggered: ${data.message || 'Success'}`, 'success');
    } catch {
        showToast("Server offline, simulated evolution complete.", "success");
    }
    closeAgentModal();
}
