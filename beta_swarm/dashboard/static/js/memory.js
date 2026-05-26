// memory.js - Premium Multi-Tab Dynamic Memory Vault Viewer
let memoryEntries = [];
let currentVaultTab = 'letta-core';

function switchVaultTab(tabId) {
    currentVaultTab = tabId;
    
    // Update button states
    document.querySelectorAll('.vault-tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('onclick').includes(tabId)) {
            btn.classList.add('active');
        }
    });

    // Update panel states
    document.querySelectorAll('.vault-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    const activePane = document.getElementById(`vault-${tabId}`);
    if (activePane) {
        activePane.classList.add('active');
    }

    // Load data for the selected tab
    loadVaultData(tabId);
}

async function loadVaultData(tabId) {
    const pane = document.getElementById(`vault-${tabId}`);
    if (!pane) return;

    pane.innerHTML = '<div style="color:var(--text-muted); padding:20px;">Fetching memory blocks...</div>';

    try {
        if (tabId === 'letta-core') {
            const res = await fetch(`${API_BASE}/brain/core`);
            const data = await res.json();
            
            let html = `<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:16px; padding:16px 0;">`;
            data.letta_blocks.forEach(block => {
                html += `
                    <div class="agent-card fade-in" style="border: 1px solid rgba(0, 242, 255, 0.25); background: rgba(10, 25, 41, 0.5); backdrop-filter: blur(10px); padding:20px; border-radius:12px; position:relative; overflow:hidden;">
                        <div style="font-size:11px; font-weight:700; color:var(--primary); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">${block.type} BLOCK</div>
                        <h4 style="font-family:'Outfit',sans-serif; font-size:16px; font-weight:700; margin-bottom:8px;">${block.name.replace(/_/g, ' ')}</h4>
                        <div style="font-family:monospace; font-size:12px; color:var(--text-muted);">Size: ${block.size_bytes} Bytes</div>
                        <div style="margin-top:12px; border-top:1px solid rgba(255,255,255,0.1); padding-top:12px; font-size:11px; color:#a8ffb2; font-family:monospace;">STATE: LOADED & SYNCHRONIZED</div>
                    </div>
                `;
            });
            html += `</div>`;
            pane.innerHTML = html;

        } else if (tabId === 'letta-recall') {
            pane.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--glass-border); padding-bottom:12px;">
                        <span style="font-size:12px; color:var(--text-muted);">Chronological timeline of agent knowledge nodes sync'd with Obsidian Daily-Note.md</span>
                        <input type="text" id="memory-search-input" class="command-input" style="max-width:300px; font-size:11px; height:32px;" placeholder="Search daily note WikiLinks..." oninput="renderTimeline(this.value)">
                    </div>
                    <div id="timeline-container" class="timeline-container"></div>
                </div>
            `;
            await loadMemoryTimeline();

        } else if (tabId === 'neo4j-archival') {
            const res = await fetch(`${API_BASE}/brain/archival`);
            const data = await res.json();
            
            let html = `
                <div style="display:grid; grid-template-columns: 1fr 2fr; gap:20px; padding:16px 0;">
                    <div class="agent-card" style="border:1px solid rgba(0, 119, 255, 0.3); background: rgba(5,10,15,0.8); padding:20px; border-radius:12px; display:flex; flex-direction:column; justify-content:center;">
                        <h4 style="font-size:18px; font-weight:700; margin-bottom:12px; color:#00f2ff;">Neo4j Cluster Vitals</h4>
                        <div style="font-size:32px; font-weight:900; margin-bottom:4px; color:#ffffff;">${data.graph_summary.nodes} <span style="font-size:14px; font-weight:400; color:var(--text-muted);">Nodes</span></div>
                        <div style="font-size:32px; font-weight:900; margin-bottom:16px; color:#ffffff;">${data.graph_summary.edges} <span style="font-size:14px; font-weight:400; color:var(--text-muted);">Edges</span></div>
                        <div style="font-family:monospace; font-size:11px; background:rgba(0,0,0,0.4); padding:8px; border-radius:4px; color:#a8ffb2;">LAYOUT: ${data.graph_summary.type}</div>
                    </div>
                    <div style="background:rgba(5,2,10,0.85); border:1px solid var(--glass-border); border-radius:12px; overflow:hidden; display:flex; flex-direction:column;">
                        <div style="padding:10px 16px; background:rgba(0,0,0,0.3); border-bottom:1px solid var(--glass-border); font-size:11px; font-weight:700; color:var(--text-muted);">Archival Graph Relationship Entities</div>
                        <div style="flex-grow:1; overflow-y:auto; padding:16px; font-family:monospace; font-size:12px; line-height:1.8; color:#f3f4f6;">
            `;
            data.elements.forEach(el => {
                if (el.data.source) {
                    html += `<div>MATCH <span style="color:#00f2ff;">(${el.data.source})</span>-[:<span style="color:#f59e0b;">${el.data.label}</span>]-><span style="color:#00f2ff;">(${el.data.target})</span></div>`;
                } else {
                    html += `<div>CREATE <span style="color:#a8ffb2;">(${el.data.id}:${el.data.label})</span></div>`;
                }
            });
            html += `
                        </div>
                    </div>
                </div>
            `;
            pane.innerHTML = html;

        } else if (tabId === 'cognee-kg') {
            const res = await fetch(`${API_BASE}/brain/kg`);
            const data = await res.json();
            
            let html = `
                <div style="padding:16px 0;">
                    <div style="background:rgba(5,2,10,0.85); border:1px solid var(--glass-border); border-radius:12px; overflow:hidden;">
                        <table style="width:100%; border-collapse:collapse; text-align:left; font-family:monospace; font-size:12px;">
                            <thead>
                                <tr style="background:rgba(0,242,255,0.05); border-bottom:1px solid var(--glass-border); color:var(--primary);">
                                    <th style="padding:12px 16px;">Source Entity</th>
                                    <th style="padding:12px 16px;">Source Type</th>
                                    <th style="padding:12px 16px;">Relationship</th>
                                    <th style="padding:12px 16px;">Target Entity</th>
                                </tr>
                            </thead>
                            <tbody>
            `;
            data.semantic_entities.forEach(ent => {
                html += `
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                        <td style="padding:12px 16px; color:#ffffff; font-weight:700;">${ent.entity}</td>
                        <td style="padding:12px 16px; color:var(--text-muted);">${ent.type}</td>
                        <td style="padding:12px 16px; color:#f59e0b;">${ent.relation.toUpperCase()}</td>
                        <td style="padding:12px 16px; color:#a8ffb2;">${ent.target}</td>
                    </tr>
                `;
            });
            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            pane.innerHTML = html;

        } else if (tabId === 'graphiti-temporal') {
            const res = await fetch(`${API_BASE}/brain/temporal`);
            const data = await res.json();
            
            let html = `<div style="display:flex; flex-direction:column; gap:16px; padding:16px 0;">`;
            data.temporal_facts.forEach(fact => {
                html += `
                    <div class="agent-card fade-in" style="border-left: 3px solid #ff3333; background: rgba(5,2,10,0.85); padding:16px; border-radius:0 12px 12px 0;">
                        <div style="font-family:monospace; font-size:11px; color:#ff3333; margin-bottom:4px;">[${new Date(fact.timestamp * 1000).toLocaleTimeString()}] TEMPORAL RECORD</div>
                        <div style="font-family:'Outfit',sans-serif; font-size:14px; color:#ffffff; line-height:1.5;">${fact.fact}</div>
                    </div>
                `;
            });
            html += `</div>`;
            pane.innerHTML = html;
        }

    } catch (e) {
        pane.innerHTML = `<div style="color:var(--color-guardian); padding:20px;">Failed to retrieve active memory structures: ${e}</div>`;
    }
}

async function loadMemoryTimeline() {
    const container = document.getElementById('timeline-container');
    if (!container) return;
    
    container.innerHTML = '<div style="color:var(--text-muted);">Syncing with Obsidian Vault...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/memory/timeline`);
        const data = await response.json();
        
        if (data.entries && data.entries.length > 0) {
            memoryEntries = data.entries;
            renderTimeline();
        } else {
            // Fallback seed timeline for demo
            memoryEntries = [
                { date: '2026-05-17', preview: '[[b1_local_brain]] initialized. Schema seeded for KuzuDB. All 26 agent states matching strategic, execution, bridge layers mapped successfully.', path: '' },
                { date: '2026-05-16', preview: '[[whisper_pipeline]] integration successful. Transcribing audio captures directly to FastAPI backends.', path: '' }
            ];
            renderTimeline();
        }
    } catch (e) {
        container.innerHTML = '<div style="color:var(--color-guardian);">Vault sync connection failed. Check local path bindings.</div>';
    }
}

function renderTimeline(filterText = '') {
    const container = document.getElementById('timeline-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    let filtered = memoryEntries;
    if (filterText.trim()) {
        try {
            const regex = new RegExp(filterText, 'i');
            filtered = memoryEntries.filter(entry => regex.test(entry.preview) || regex.test(entry.date));
        } catch {
            filtered = memoryEntries.filter(entry => entry.preview.toLowerCase().includes(filterText.toLowerCase()));
        }
    }
    
    if (filtered.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted); padding:20px;">No notes match search filters.</div>';
        return;
    }
    
    filtered.forEach(entry => {
        const card = document.createElement('div');
        card.className = 'timeline-item fade-in';
        card.style.background = 'rgba(10, 25, 41, 0.4)';
        card.style.border = '1px solid var(--glass-border)';
        card.style.padding = '16px';
        card.style.borderRadius = '8px';
        card.style.cursor = 'pointer';
        card.onclick = () => showTimelineItemDetails(entry);
        
        const header = document.createElement('div');
        header.className = 'timeline-item-header';
        header.style.display = 'flex';
        header.style.justify = 'space-between';
        header.style.marginBottom = '8px';
        
        const title = document.createElement('div');
        title.className = 'timeline-item-title';
        title.style.fontWeight = '700';
        title.style.color = '#ffffff';
        title.textContent = `Daily Log - ${entry.date}`;
        
        const date = document.createElement('div');
        date.className = 'timeline-item-date';
        date.style.fontSize = '10px';
        date.style.color = '#a8ffb2';
        date.textContent = 'SYNCED';
        
        header.appendChild(title);
        header.appendChild(date);
        
        const body = document.createElement('div');
        body.className = 'timeline-item-body';
        body.style.fontSize = '12px';
        body.style.lineHeight = '1.6';
        body.style.color = 'var(--text-muted)';
        
        let parsedPreview = entry.preview.replace(/\[\[(.*?)\]\]/g, '<span style="color:var(--primary); font-weight:700; cursor:pointer;">$1</span>');
        body.innerHTML = parsedPreview;
        
        card.appendChild(header);
        card.appendChild(body);
        container.appendChild(card);
    });
}

function showTimelineItemDetails(entry) {
    const modal = document.getElementById('agent-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    
    if (!modal || !modalTitle || !modalBody) return;
    
    modalTitle.textContent = `Obsidian Daily Note: ${entry.date}`;
    modalBody.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="font-family:monospace; font-size:12px; background:rgba(0,0,0,0.5); padding:16px; border-radius:8px; max-height:300px; overflow-y:auto; line-height:1.6; white-space:pre-wrap;">${entry.preview}</div>
            <div style="font-size:11px; color:var(--text-muted);">Local Path: ${entry.path || 'Obsidian Memory Vault'}</div>
            <div style="display:flex; justify-content:flex-end; gap:12px; border-top:1px solid var(--glass-border); padding-top:16px;">
                <button class="btn" onclick="closeAgentModal()">Close</button>
            </div>
        </div>
    `;
    modal.style.display = 'flex';
}
