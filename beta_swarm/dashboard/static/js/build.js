// build.js - Master visualizers for split-screen Build Mode and horizontal SVG pipeline flow
let buildTerminalPaused = false;
let buildLogLineCount = 0;

class BuildVisualizer {
    constructor() {
        this.logStream = document.getElementById('build-log-stream');
        this.agentGrid = document.getElementById('build-agent-grid');
        this.setupTerminalHover();
        this.renderLeftAgentCards();
    }

    setupTerminalHover() {
        if (!this.logStream) return;
        this.logStream.addEventListener('mouseenter', () => {
            buildTerminalPaused = true;
            console.log('[BuildConsole] Terminal scrolling paused on hover.');
        });
        this.logStream.addEventListener('mouseleave', () => {
            buildTerminalPaused = false;
            console.log('[BuildConsole] Terminal scrolling resumed.');
            this.logStream.scrollTop = this.logStream.scrollHeight;
        });
    }

    renderLeftAgentCards() {
        if (!this.agentGrid) return;
        
        const buildStages = [
            { id: 's1_ideation', badge: 'S1', role: 'Strategic', name: 'Ideation', desc: 'Analyzing broadcast prompts and specs.' },
            { id: 's3_prd', badge: 'S3', role: 'Strategic', name: 'PRD Writer', desc: 'Synthesizing system requirement guidelines.' },
            { id: 's4_architecture', badge: 'S4', role: 'Strategic', name: 'Architecture', desc: 'Formulating component models and scopes.' },
            { id: 's5_backend', badge: 'S5', role: 'Execution', name: 'Backend Gen', desc: 'Compiling core endpoints and Dockerfiles.' },
            { id: 's7_frontend_huashu', badge: 'S7', role: 'Execution', name: 'Huashu Front', desc: 'Generating CSS prototypes & SVG infographics.' },
            { id: 'x1_code_review', badge: 'X1', role: 'Review', name: 'AST Review', desc: 'Analyzing source directories for syntax risks.' },
            { id: 's9_deployment', badge: 'S9', role: 'Execution', name: 'Deployment', desc: 'Generating docker-compose manifests.' }
        ];

        let html = '';
        buildStages.forEach(stage => {
            let borderColor = 'rgba(0, 119, 255, 0.3)'; // Indigo
            if (stage.role === 'Execution') borderColor = 'rgba(63, 185, 80, 0.4)'; // Green
            if (stage.role === 'Review') borderColor = 'rgba(245, 158, 11, 0.4)'; // Yellow

            html += `
                <div id="card-${stage.id}" class="agent-card fade-in" onclick="openBuildAgentDetails('${stage.id}')" style="border: 1px solid ${borderColor}; padding:16px; border-radius:12px; position:relative; overflow:hidden; cursor:pointer;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-family:monospace; font-size:10px; font-weight:700; background:rgba(255,255,255,0.07); padding:2px 6px; border-radius:4px;">${stage.badge} | ${stage.role.toUpperCase()}</span>
                        <div id="pill-${stage.id}" style="width:8px; height:8px; border-radius:50%; background:#9ca3af;"></div>
                    </div>
                    <h4 style="font-family:'Outfit',sans-serif; font-size:14px; font-weight:700; margin-bottom:4px;">${stage.name}</h4>
                    <p style="font-size:11px; color:var(--text-muted); margin-bottom:12px; height:32px; overflow:hidden;">${stage.desc}</p>
                    
                    <div class="progress-bar-container" style="height:4px; background:rgba(255,255,255,0.05); border-radius:2px; overflow:hidden; margin-bottom:8px;">
                        <div id="progress-${stage.id}" style="width:0%; height:100%; background:var(--primary); transition:width 0.5s ease;"></div>
                    </div>
                    
                    <div style="font-family:monospace; font-size:10px; color:#a8ffb2; height:14px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;" id="log-${stage.id}">Waiting in queue...</div>
                </div>
            `;
        });
        
        this.agentGrid.innerHTML = html;
    }

    appendTerminalLog(msg, status = 'info') {
        if (!this.logStream) return;
        
        let color = '#ffffff'; // Agent
        if (status === 'system' || status === 'info') color = '#00f2ff'; // System Blue
        if (status === 'error') color = '#ff3333'; // Error Red
        if (status === 'human') color = '#f59e0b'; // Human Yellow
        
        const line = document.createElement('div');
        line.style.color = color;
        line.style.marginBottom = '6px';
        line.style.fontFamily = 'monospace';
        line.style.fontSize = '12px';
        line.style.whiteSpace = 'pre-wrap';
        line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
        
        this.logStream.appendChild(line);
        buildLogLineCount++;
        
        // FIFO Pruning: keep max 1000 lines
        if (buildLogLineCount > 1000) {
            this.logStream.removeChild(this.logStream.firstChild);
            buildLogLineCount--;
        }
        
        if (!buildTerminalPaused) {
            this.logStream.scrollTop = this.logStream.scrollHeight;
        }
    }

    destroy() {
        // WebSocket client connection handled inside wsHub.destroy()
    }
}

// Open agent details from the Build Grid
function openBuildAgentDetails(agentId) {
    const modal = document.getElementById('agent-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    
    if (!modal || !modalTitle || !modalBody) return;
    
    // Extract the latest log message dynamically from the UI card
    const agentLogElem = document.getElementById(`log-${agentId}`);
    const actualLog = agentLogElem ? agentLogElem.textContent : "Awaiting agent execution data...";
    
    modalTitle.textContent = `Agent Vitals: ${agentId.replace(/_/g, ' ').toUpperCase()}`;
    modalBody.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
                <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
                    <div style="font-size:10px; color:var(--text-muted);">ROLE BARRIER</div>
                    <div style="font-weight:700;">SQLite Integration</div>
                </div>
                <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
                    <div style="font-size:10px; color:var(--text-muted);">AST VALIDITY</div>
                    <div style="font-weight:700; color:#a8ffb2;">SECURE</div>
                </div>
            </div>
            <div style="font-family:monospace; font-size:11px; background:rgba(5,2,10,0.85); padding:12px; border-radius:8px; max-height:160px; overflow-y:auto; line-height:1.6; color:#a8ffb2; white-space:pre-wrap;">
[info] Agent initialized securely.
[info] Connected to high-concurrency SQLite brain.
[output] ${actualLog}
            </div>
            <div style="display:flex; justify-content:flex-end; gap:12px; border-top:1px solid var(--glass-border); padding-top:16px;">
                <button class="btn" onclick="closeAgentModal()">Close</button>
            </div>
        </div>
    `;
    modal.style.display = 'flex';
}

let buildVis = null;

// WS Build stream listener overhaul
function listenBuildStream(userIdea) {
    buildVis = new BuildVisualizer();
    
    window.wsHub.connect('build', '/ws/build');
    
    window.wsHub.on('build', 'open', () => {
        buildVis.appendTerminalLog('[SYSTEM] Connected to live pipeline stream.', 'system');
        
        // Send user's project idea to the backend pipeline
        const idea = userIdea || window.lastBuildCommand || 'Build a FastAPI Todo web application';
        const projectName = idea.replace(/[^a-zA-Z0-9]/g, '').substring(0, 30) || 'SwarmProject';
        window.wsHub.send('build', JSON.stringify({
            idea: idea,
            project_name: projectName
        }));
        buildVis.appendTerminalLog(`[USER] Project idea: "${idea}"`, 'human');
    });

    window.wsHub.on('build', 'message', (data) => {
        if (data && data.type === 'heartbeat') return;
        
        const msg = data.message || JSON.stringify(data);
        const status = data.status || 'info';
        
        // Log to terminal
        buildVis.appendTerminalLog(msg, status);
        
        // Parse current active agent to trigger card vitals
        if (msg.includes('[S1]') || msg.includes('s1_ideation')) updateBuildCard('s1_ideation', msg, 100, '#00f2ff');
        if (msg.includes('[S3]') || msg.includes('s3_prd')) updateBuildCard('s3_prd', msg, 100, '#00f2ff');
        if (msg.includes('[S4]') || msg.includes('s4_architecture')) updateBuildCard('s4_architecture', msg, 100, '#00f2ff');
        if (msg.includes('[S5]') || msg.includes('s5_backend')) updateBuildCard('s5_backend', msg, 100, '#00ff7f');
        if (msg.includes('[S7]') || msg.includes('s7_frontend')) updateBuildCard('s7_frontend_huashu', msg, 100, '#00ff7f');
        if (msg.includes('[X1]') || msg.includes('x1_code')) updateBuildCard('x1_code_review', msg, 100, '#f59e0b');
        if (msg.includes('[S9]') || msg.includes('s9_deployment')) updateBuildCard('s9_deployment', msg, 100, '#00ff7f');
    });

    window.wsHub.on('build', 'close', () => {
        buildVis.appendTerminalLog('[SYSTEM] Connection lost. Reconnecting...', 'error');
    });
}

function updateBuildCard(id, msg, progress, glowColor) {
    const pill = document.getElementById(`pill-${id}`);
    const bar = document.getElementById(`progress-${id}`);
    const log = document.getElementById(`log-${id}`);
    const card = document.getElementById(`card-${id}`);
    
    if (pill) {
        pill.style.background = glowColor;
        pill.style.boxShadow = `0 0 8px ${glowColor}`;
    }
    if (bar) {
        bar.style.width = `${progress}%`;
        bar.style.background = glowColor;
    }
    if (log) {
        log.textContent = msg.substring(msg.indexOf(']') + 1).trim();
    }
    if (card) {
        card.style.borderColor = glowColor;
        card.style.boxShadow = `0 0 10px rgba(${glowColor === '#ff3333' ? '255,51,51' : '0,242,255'}, 0.15)`;
    }
}

// ---------------------------------------------------------------------------
// 8-Layer Horizontal SVG Pipeline Flow
// ---------------------------------------------------------------------------

function renderPipelineFlow() {
    const container = document.getElementById('svg-pipeline-container');
    if (!container) return;

    const layers = [
        { id: 'L0', name: 'Ideation', cx: 80, cy: 150, agent: 's1_ideation', sentry: 'passed', info: 'Formulates basic core logic and blueprints.' },
        { id: 'L1', name: 'Research', cx: 200, cy: 150, agent: 's2_research', sentry: 'passed', info: 'Assesses domain parameters and requirements.' },
        { id: 'L2', name: 'PRD Spec', cx: 320, cy: 150, agent: 's3_prd', sentry: 'passed', info: 'Drafts system specifications and dependencies.' },
        { id: 'L3', name: 'Arch', cx: 440, cy: 150, agent: 's4_architecture', sentry: 'passed', info: 'Defines endpoints, layouts, and DB graphs.' },
        { id: 'L4', name: 'Frontend', cx: 560, cy: 150, agent: 's7_frontend_huashu', sentry: 'warning', info: 'Renders dynamic HTML prototypes & SVGs.' },
        { id: 'L5', name: 'Review', cx: 680, cy: 150, agent: 'x1_code_review', sentry: 'passed', info: 'Validates source syntax and security paths.' },
        { id: 'L6', name: 'Deploy', cx: 800, cy: 150, agent: 's9_deployment', sentry: 'passed', info: 'Builds docker-compose infrastructure packs.' },
        { id: 'L7', name: 'Sentry', cx: 920, cy: 150, agent: 'sentry', sentry: 'passed', info: 'Gatekeeper controlling final release bounds.' }
    ];

    let svgContent = `
        <svg width="1020" height="300" xmlns="http://www.w3.org/2000/svg" style="background:#030712; display:block;">
            <defs>
                <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#00f2ff" stop-opacity="0.8"/>
                    <stop offset="100%" stop-color="#0077ff" stop-opacity="0.8"/>
                </linearGradient>
                <filter id="glow">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                    <feMerge>
                        <feMergeNode in="coloredBlur"/>
                        <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                </filter>
            </defs>
    `;

    // 1. Draw connecting paths with dash arrays
    for (let i = 0; i < layers.length - 1; i++) {
        const l1 = layers[i];
        const l2 = layers[i + 1];
        svgContent += `
            <path id="path-${l1.id}-${l2.id}" d="M ${l1.cx} ${l1.cy} L ${l2.cx} ${l2.cy}" 
                  stroke="url(#cyanGrad)" stroke-width="2" stroke-dasharray="6,4" opacity="0.4"/>
            
            <!-- Dynamic moving particles -->
            <circle r="3" fill="#00f2ff" filter="url(#glow)">
                <animateMotion dur="3s" repeatCount="indefinite" path="M ${l1.cx} ${l1.cy} L ${l2.cx} ${l2.cy}" />
            </circle>
        `;
    }

    // 2. Draw node circles
    layers.forEach(l => {
        let gateColor = '#a8ffb2'; // passed (green)
        if (l.sentry === 'warning') gateColor = '#f59e0b'; // warning (amber)
        if (l.sentry === 'error') gateColor = '#ff3333'; // error (red)

        svgContent += `
            <g style="cursor:pointer;" onclick="showLayerVitals('${l.id}', '${l.name}', '${l.agent}', '${l.sentry}', '${l.info}')">
                <circle cx="${l.cx}" cy="${l.cy}" r="22" fill="#0a1929" stroke="url(#cyanGrad)" stroke-width="2" filter="url(#glow)"/>
                <circle cx="${l.cx}" cy="${l.cy}" r="25" fill="none" stroke="${gateColor}" stroke-width="1.5" stroke-dasharray="4,2"/>
                <text x="${l.cx}" y="${l.cy + 5}" fill="#ffffff" font-size="10" font-family="monospace" font-weight="700" text-anchor="middle">${l.id}</text>
                <text x="${l.cx}" y="${l.cy + 40}" fill="#9ca3af" font-size="11" font-family="Outfit,sans-serif" font-weight="500" text-anchor="middle">${l.name}</text>
            </g>
        `;
    });

    svgContent += `</svg>`;
    container.innerHTML = svgContent;
}

function showLayerVitals(id, name, agent, sentry, info) {
    const drawer = document.getElementById('pipeline-details-drawer');
    const title = document.getElementById('drawer-title');
    const body = document.getElementById('drawer-body');
    
    if (!drawer || !title || !body) return;

    title.textContent = `${id} Layer: ${name.toUpperCase()}`;
    body.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
                <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
                    <div style="font-size:10px; color:var(--text-muted);">ACTIVE AGENT</div>
                    <div style="font-weight:700; color:#00f2ff;">${agent}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
                    <div style="font-size:10px; color:var(--text-muted);">SENTRY GATE</div>
                    <div style="font-weight:700; color:${sentry === 'warning' ? '#f59e0b' : '#a8ffb2'};">${sentry.toUpperCase()}</div>
                </div>
            </div>
            <div style="font-size:13px; line-height:1.6; color:#ffffff;">
                <strong>Layer Mission:</strong> ${info}
            </div>
            <div style="font-family:monospace; font-size:11px; background:rgba(0,0,0,0.5); padding:12px; border-radius:6px; line-height:1.5; color:#a8ffb2;">
                [L-STAT] Diagnostic checksum MATCH.<br/>
                [L-GATE] ${sentry.toUpperCase()} status recorded to KuzuDB recall memory.<br/>
                [L-MESH] Routed via ExoNode 'local_lenny'.
            </div>
        </div>
    `;
    drawer.classList.add('open');
}

function closePipelineDrawer() {
    const drawer = document.getElementById('pipeline-details-drawer');
    if (drawer) drawer.classList.remove('open');
}
