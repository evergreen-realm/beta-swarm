document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = 'http://localhost:8000';
    let isConnected = false;
    let registeredAgents = [];
    let activeProjects = [];
    let currentProject = null;
    let pollInterval = null;
    let mockMode = false;
    
    // UI Elements
    const navLinks = document.querySelectorAll('.nav-link');
    const pages = document.querySelectorAll('.page');
    const pageTitle = document.getElementById('page-title');
    const systemStatus = document.getElementById('system-status');
    const statusDot = document.querySelector('.status-dot');
    
    const agentCountEl = document.getElementById('agent-count');
    const ramValueEl = document.getElementById('ram-value');
    const ramBar = document.getElementById('ram-bar');
    const projectCountEl = document.getElementById('project-count');
    
    const pipelineContainer = document.getElementById('pipeline');
    const activityList = document.getElementById('activity-list');
    const brainGrid = document.getElementById('brain-grid');
    
    const agentTableBody = document.getElementById('agent-table-body');
    const projectList = document.getElementById('project-list');
    const brainLayersDetail = document.getElementById('brain-layers-detail');
    const monitorGrid = document.getElementById('monitor-grid');
    
    const btnNewProject = document.getElementById('btn-new-project');
    const modalOverlay = document.getElementById('modal-overlay');
    const btnCancelModal = document.getElementById('btn-cancel-modal');
    const projectForm = document.getElementById('project-form');
    
    const searchInput = document.getElementById('search-input');
    
    // Pipeline Stages Configuration
    const STAGES = [
        { id: 's1_ideation', label: 'Ideation', num: 'S1' },
        { id: 's2_research', label: 'Research', num: 'S2' },
        { id: 's3_prd', label: 'PRD', num: 'S3' },
        { id: 's4_architecture', label: 'Arch', num: 'S4' },
        { id: 's5_backend', label: 'Backend', num: 'S5' },
        { id: 's6_api', label: 'API', num: 'S6' },
        { id: 's7_frontend', label: 'Frontend', num: 'S7' },
        { id: 's8_testing', label: 'Testing', num: 'S8' },
        { id: 's9_deployment', label: 'Deploy', num: 'S9' },
        { id: 's10_monitoring', label: 'Monitor', num: 'S10' },
        { id: 's11_documentation', label: 'Docs', num: 'S11' },
        { id: 's12_maintenance', label: 'Maint', num: 'S12' },
        { id: 's13_design', label: 'Design', num: 'S13' }
    ];

    // Navigation toggler
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const pageId = link.getAttribute('data-page');
            
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            pages.forEach(p => p.classList.remove('active'));
            document.getElementById(`page-${pageId}`).classList.add('active');
            
            pageTitle.textContent = link.textContent.trim();
            
            // If switching pages, refresh specific page views
            if (pageId === 'agents') renderAgentsList();
            if (pageId === 'projects') renderProjectsList();
            if (pageId === 'brain') renderBrainDetails();
            if (pageId === 'monitoring') renderMonitoring();
        });
    });

    // Search bar functionality
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const activeLink = document.querySelector('.nav-link.active');
        const currentPage = activeLink.getAttribute('data-page');
        
        if (currentPage === 'agents') {
            const rows = agentTableBody.querySelectorAll('tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        } else if (currentPage === 'projects') {
            const cards = projectList.querySelectorAll('.project-item');
            cards.forEach(card => {
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(query) ? '' : 'none';
            });
        }
    });

    // Modals
    btnNewProject.addEventListener('click', () => {
        modalOverlay.classList.add('active');
    });
    
    btnCancelModal.addEventListener('click', () => {
        modalOverlay.classList.remove('active');
        projectForm.reset();
    });
    
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            modalOverlay.classList.remove('active');
            projectForm.reset();
        }
    });

    projectForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const desc = document.getElementById('proj-desc').value;
        const tier = document.getElementById('proj-tier').value;
        
        if (!desc.trim()) return;
        
        modalOverlay.classList.remove('active');
        projectForm.reset();
        
        if (mockMode) {
            startMockProject(desc, tier);
        } else {
            try {
                const res = await fetch(`${API_BASE}/api/v1/projects`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ description: desc, tier: tier })
                });
                
                if (res.status === 503) {
                    const data = await res.json();
                    alert(`Capacity Breach: ${data.error}. Free memory: ${data.free_mb}MB. 2048MB is required to spawn new projects.`);
                    return;
                }
                
                const data = await res.json();
                currentProject = {
                    project_id: data.project_id,
                    description: desc,
                    tier: tier,
                    status: 'created',
                    current_stage: 's1_ideation',
                    progress_percent: 10,
                    outputs: { concept: data.concept }
                };
                activeProjects.unshift(currentProject);
                projectCountEl.textContent = activeProjects.length;
                
                // Switch to projects tab
                document.getElementById('nav-projects').click();
                startPollingProject(data.project_id);
            } catch (err) {
                console.error(err);
                alert("Failed to spawn project on backend. Switching to interactive simulation!");
                mockMode = true;
                startMockProject(desc, tier);
            }
        }
    });

    // Check status and connection
    async function checkBackend() {
        try {
            const res = await fetch(`${API_BASE}/api/v1/health`);
            if (res.ok) {
                const data = await res.json();
                isConnected = true;
                mockMode = false;
                systemStatus.textContent = 'REST Connected';
                statusDot.style.background = 'var(--accent-green)';
                statusDot.style.boxShadow = '0 0 10px var(--accent-green)';
                
                // Populate base stats
                agentCountEl.textContent = data.agents || 36;
                ramValueEl.textContent = `${data.memory.free_mb} MB`;
                ramBar.style.width = `${100 - data.memory.percent}%`;
                
                // Retrieve agents list
                const agentsRes = await fetch(`${API_BASE}/api/v1/agents`);
                if (agentsRes.ok) {
                    registeredAgents = await agentsRes.json();
                }
                
                // Refresh dashboard components
                renderPipeline();
                renderBrainGrid();
                updateActivityLog();
            }
        } catch (err) {
            console.warn("FastAPI offline. Running in Premium Standalone Simulation Mode.");
            isConnected = false;
            mockMode = true;
            systemStatus.textContent = 'Mesh Simulation';
            statusDot.style.background = 'var(--accent-blue)';
            statusDot.style.boxShadow = '0 0 10px var(--accent-blue)';
            
            // Set mock metrics
            agentCountEl.textContent = '36';
            ramValueEl.textContent = '6144 MB';
            ramBar.style.width = '75%';
            
            // Mock agents list
            registeredAgents = getMockAgents();
            renderPipeline();
            renderBrainGrid();
            updateActivityLog();
        }
    }

    // Render pipeline nodes
    function renderPipeline() {
        pipelineContainer.innerHTML = '';
        
        STAGES.forEach((stage, idx) => {
            const node = document.createElement('div');
            node.className = 'pipeline-node';
            node.id = `node-${stage.id}`;
            node.setAttribute('title', stage.label);
            
            // Determine active/completed status
            if (currentProject) {
                const currentIdx = STAGES.findIndex(s => s.id === currentProject.current_stage);
                if (currentProject.status === 'completed') {
                    node.classList.add('completed');
                } else if (idx < currentIdx) {
                    node.classList.add('completed');
                } else if (idx === currentIdx) {
                    node.classList.add('active');
                }
            }
            
            const circle = document.createElement('div');
            circle.className = 'node-circle';
            circle.textContent = stage.num;
            
            const label = document.createElement('div');
            label.className = 'node-label';
            label.textContent = stage.label;
            
            node.appendChild(circle);
            node.appendChild(label);
            pipelineContainer.appendChild(node);
            
            // Add connector if not the last stage
            if (idx < STAGES.length - 1) {
                const conn = document.createElement('div');
                conn.className = 'pipeline-connector';
                conn.id = `conn-${stage.id}`;
                
                if (currentProject) {
                    const currentIdx = STAGES.findIndex(s => s.id === currentProject.current_stage);
                    if (currentProject.status === 'completed') {
                        conn.classList.add('completed');
                    } else if (idx < currentIdx - 1) {
                        conn.classList.add('completed');
                    } else if (idx === currentIdx - 1) {
                        conn.classList.add('active');
                    }
                }
                
                pipelineContainer.appendChild(conn);
            }
        });
    }

    // Render agent activity logs
    function updateActivityLog() {
        activityList.innerHTML = '';
        const logs = getRecentActivityLogs();
        
        logs.forEach(log => {
            const item = document.createElement('div');
            item.className = 'activity-item';
            
            const dot = document.createElement('span');
            dot.className = `activity-dot ${log.status}`;
            
            const name = document.createElement('span');
            name.className = 'activity-name';
            name.textContent = log.agent;
            
            const desc = document.createElement('span');
            desc.className = 'activity-status';
            desc.textContent = log.message;
            
            item.appendChild(dot);
            item.appendChild(name);
            item.appendChild(desc);
            activityList.appendChild(item);
        });
    }

    // Render Brain Grid status cards
    function renderBrainGrid() {
        brainGrid.innerHTML = '';
        const layers = ['cognee', 'graphiti', 'letta', 'neo4j', 'sqlite', 'obsidian'];
        
        layers.forEach(layer => {
            const card = document.createElement('div');
            card.className = 'brain-card';
            
            const header = document.createElement('div');
            header.className = 'brain-card-header';
            
            const titleSpan = document.createElement('span');
            titleSpan.style.textTransform = 'uppercase';
            titleSpan.style.fontWeight = '700';
            titleSpan.style.letterSpacing = '0.5px';
            titleSpan.textContent = layer;
            
            const statusSpan = document.createElement('span');
            statusSpan.className = 'brain-status-ok';
            statusSpan.textContent = 'ACTIVE';
            
            header.appendChild(titleSpan);
            header.appendChild(statusSpan);
            
            const detailSpan = document.createElement('span');
            detailSpan.className = 'brain-sync-time';
            detailSpan.textContent = `Sync: 1s ago • ${Math.floor(Math.random() * 50) + 12} items`;
            
            card.appendChild(header);
            card.appendChild(detailSpan);
            brainGrid.appendChild(card);
        });
    }

    // Render full agents list inside table
    function renderAgentsList() {
        agentTableBody.innerHTML = '';
        if (registeredAgents.length === 0) {
            registeredAgents = getMockAgents();
        }
        
        registeredAgents.forEach(agent => {
            const tr = document.createElement('tr');
            
            const idTd = document.createElement('td');
            idTd.className = 'agent-id-cell';
            idTd.textContent = agent.id;
            
            const nameTd = document.createElement('td');
            nameTd.style.fontWeight = '600';
            nameTd.style.color = 'var(--text-primary)';
            nameTd.textContent = agent.name;
            
            const roleTd = document.createElement('td');
            roleTd.textContent = agent.role;
            
            const statusTd = document.createElement('td');
            const badge = document.createElement('span');
            badge.className = 'agent-status-badge idle';
            badge.textContent = 'idle';
            
            // Highlight current agent if running
            if (currentProject && currentProject.status === 'running') {
                const curStage = STAGES.find(s => s.id === currentProject.current_stage);
                if (curStage && (agent.id.startsWith(curStage.num.toLowerCase()) || agent.name.toLowerCase().includes(curStage.label.toLowerCase()))) {
                    badge.className = 'agent-status-badge running';
                    badge.textContent = 'running';
                }
            }
            
            statusTd.appendChild(badge);
            
            tr.appendChild(idTd);
            tr.appendChild(nameTd);
            tr.appendChild(roleTd);
            tr.appendChild(statusTd);
            agentTableBody.appendChild(tr);
        });
    }

    // Render projects detail list
    function renderProjectsList() {
        projectList.innerHTML = '';
        
        if (activeProjects.length === 0) {
            const empty = document.createElement('p');
            empty.className = 'empty-state';
            empty.textContent = 'No projects yet. Click "+ New Project" to start.';
            projectList.appendChild(empty);
            return;
        }
        
        activeProjects.forEach(proj => {
            const item = document.createElement('div');
            item.className = 'project-item';
            
            const info = document.createElement('div');
            info.className = 'project-info';
            
            const title = document.createElement('span');
            title.className = 'project-id-title';
            title.textContent = `${proj.project_id} [${proj.tier.toUpperCase()}]`;
            
            const desc = document.createElement('span');
            desc.className = 'project-desc';
            desc.textContent = proj.description;
            
            info.appendChild(title);
            info.appendChild(desc);
            
            const progWrap = document.createElement('div');
            progWrap.className = 'project-progress-wrap';
            
            const textWrap = document.createElement('div');
            textWrap.className = 'project-progress-text';
            
            const stageText = document.createElement('span');
            stageText.style.fontWeight = '600';
            stageText.textContent = proj.status === 'completed' ? 'Completed' : `Stage: ${proj.current_stage.split('_')[0].toUpperCase()}`;
            
            const percentText = document.createElement('span');
            percentText.textContent = `${proj.progress_percent}%`;
            
            textWrap.appendChild(stageText);
            textWrap.appendChild(percentText);
            
            const bar = document.createElement('div');
            bar.className = 'project-progress-bar';
            
            const fill = document.createElement('div');
            fill.className = 'project-progress-fill';
            fill.style.width = `${proj.progress_percent}%`;
            
            bar.appendChild(fill);
            progWrap.appendChild(textWrap);
            progWrap.appendChild(bar);
            
            item.appendChild(info);
            item.appendChild(progWrap);
            projectList.appendChild(item);
        });
    }

    // Render Brain layer details page
    function renderBrainDetails() {
        brainLayersDetail.innerHTML = '';
        const brainInfo = [
            { name: 'KuzuDB (Local Brain)', role: 'Primary local graph query layer with schema compliance, agent registry database.', stats: '36 Agents registered • 58 Vault entries • Read/Write optimized' },
            { name: 'Neo4j (Global Brain Layer)', role: 'Cross-project pattern learning, deep relationship extraction, semantic persistence layer.', stats: 'Bolt protocol active • 12,410 Entities • Graph schema synchronized' },
            { name: 'Letta (Memory Agent Orchestration)', role: 'Dynamic context windows, advanced cognitive memory architectures with flush hooks to Neo4j.', stats: 'Agent runtime active • Context scaling verified • Letta REST synced' },
            { name: 'Cognee (Semantic Knowledge Graph)', role: 'Cognitive fabric compiler, maps semantic relations directly to SQLite/Qdrant.', stats: 'Auto-indexing loaded • Dynamic graphs compiled' },
            { name: 'Graphiti (Dynamic Temporal Memory)', role: 'Temporal event tracing, keeps chronologically ordered swarm interaction logs.', stats: 'Mesh synchronization complete • Chrono database active' },
            { name: 'Obsidian (Human-Readable Vault)', role: 'Direct filesystem vault synchronization of PRDs, architectures, reviewer consensus logs, and remediation reports.', stats: '12 standard directories • 58 total files synced' }
        ];
        
        brainInfo.forEach(info => {
            const wrap = document.createElement('div');
            wrap.className = 'brain-card';
            wrap.style.marginBottom = '20px';
            wrap.style.padding = '24px';
            
            const h = document.createElement('h4');
            h.style.fontSize = '16px';
            h.style.fontWeight = '800';
            h.style.color = 'var(--text-primary)';
            h.style.marginBottom = '8px';
            h.textContent = info.name;
            
            const role = document.createElement('p');
            role.style.fontSize = '14px';
            role.style.color = 'var(--text-secondary)';
            role.style.marginBottom = '12px';
            role.textContent = info.role;
            
            const stats = document.createElement('div');
            stats.className = 'status-badge';
            stats.style.width = 'fit-content';
            stats.style.fontFamily = 'var(--font-mono)';
            stats.style.fontSize = '12px';
            stats.textContent = info.stats;
            
            wrap.appendChild(h);
            wrap.appendChild(role);
            wrap.appendChild(stats);
            brainLayersDetail.appendChild(wrap);
        });
    }

    // Render monitoring details page
    function renderMonitoring() {
        monitorGrid.innerHTML = '';
        const items = [
            { name: 'Local Mesh RAM Status', value: 'Healthy (24% Used)', detail: 'ResourceGuard: OK. Governor is actively stagger-starting Docker compose.' },
            { name: 'Docker Compose Containers', value: '14 Active', detail: 'Neo4j: RUNNING • Letta: RUNNING • Traefik: RUNNING • Prom/Grafana: ACTIVE' },
            { name: 'Consensus Decision', value: 'PASS (3/3 Votes)', detail: 'X1 Code Review: PASS • X2 Security: PASS • X3 Performance: PASS' },
            { name: 'Remediation Loop', value: 'Idle', detail: 'Triple Gate active. No consensus blocks currently detected.' },
            { name: 'Whisper CPP Pipeline', value: 'Standby', detail: 'Audio voice triggers enabled. Latency: <80ms.' },
            { name: 'Continuous Learning Loop', value: 'Running', detail: 'Interest Tracker priority topic: "Multi-agent fault recovery".' }
        ];
        
        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'monitor-card';
            
            const h = document.createElement('div');
            h.className = 'monitor-header';
            
            const name = document.createElement('span');
            name.className = 'monitor-name';
            name.textContent = item.name;
            
            const dot = document.createElement('span');
            dot.className = 'status-dot';
            
            h.appendChild(name);
            h.appendChild(dot);
            
            const val = document.createElement('div');
            val.className = 'monitor-value';
            val.textContent = item.value;
            
            const det = document.createElement('div');
            det.style.fontSize = '12px';
            det.style.color = 'var(--text-secondary)';
            det.textContent = item.detail;
            
            card.appendChild(h);
            card.appendChild(val);
            card.appendChild(det);
            monitorGrid.appendChild(card);
        });
    }

    // Mock project simulation logic
    function startMockProject(desc, tier) {
        clearInterval(pollInterval);
        
        const projId = `proj_mock_${Math.floor(Math.random() * 10000)}`;
        currentProject = {
            project_id: projId,
            description: desc,
            tier: tier,
            status: 'running',
            current_stage: 's1_ideation',
            progress_percent: 5,
            outputs: {}
        };
        
        activeProjects.unshift(currentProject);
        projectCountEl.textContent = activeProjects.length;
        
        // Render and go to projects page
        renderPipeline();
        renderProjectsList();
        document.getElementById('nav-projects').click();
        
        let currentIdx = 0;
        
        pollInterval = setInterval(() => {
            if (currentIdx >= STAGES.length) {
                currentProject.status = 'completed';
                currentProject.progress_percent = 100;
                clearInterval(pollInterval);
                checkBackend(); // Re-establish active status
                renderProjectsList();
                renderPipeline();
                alert(`Project ${projId} Synthesized and Deployed Successfully!`);
                return;
            }
            
            const stage = STAGES[currentIdx];
            currentProject.current_stage = stage.id;
            currentProject.progress_percent = Math.floor(((currentIdx + 1) / STAGES.length) * 100);
            
            // Trigger random activity log related to this stage
            addMockActivity(stage);
            
            renderPipeline();
            renderProjectsList();
            
            currentIdx++;
        }, 3000);
    }

    // Polling actual backend project progress
    function startPollingProject(projectId) {
        clearInterval(pollInterval);
        
        pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}`);
                if (res.ok) {
                    const data = await res.json();
                    
                    // Update currentProject
                    currentProject.status = data.status;
                    currentProject.current_stage = data.current_stage;
                    currentProject.progress_percent = data.progress_percent;
                    currentProject.outputs = data.outputs;
                    
                    // Update project list
                    const pIdx = activeProjects.findIndex(p => p.project_id === projectId);
                    if (pIdx !== -1) {
                        activeProjects[pIdx] = currentProject;
                    }
                    
                    renderPipeline();
                    renderProjectsList();
                    
                    if (data.status === 'completed' || data.status === 'failed') {
                        clearInterval(pollInterval);
                        alert(`Project ${projectId} ended with status: ${data.status.toUpperCase()}`);
                    }
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 4000);
    }

    // Mock data generators
    function addMockActivity(stage) {
        const item = document.createElement('div');
        item.className = 'activity-item';
        
        const dot = document.createElement('span');
        dot.className = 'activity-dot active';
        
        const name = document.createElement('span');
        name.className = 'activity-name';
        name.textContent = stage.num;
        
        const desc = document.createElement('span');
        desc.className = 'activity-status';
        desc.textContent = `Orchestrating ${stage.label} Agent logic... Completed.`;
        
        item.appendChild(dot);
        item.appendChild(name);
        item.appendChild(desc);
        
        activityList.insertBefore(item, activityList.firstChild);
        if (activityList.children.length > 5) {
            activityList.removeChild(activityList.lastChild);
        }
    }

    function getMockAgents() {
        return [
            { id: 's1_ideation', name: 'Ideation Agent', role: 'Stage 1: Input Processing' },
            { id: 's2_research', name: 'Research Agent', role: 'Stage 2: Deep Research' },
            { id: 's3_prd', name: 'PRD Agent', role: 'Stage 3: Product Requirements' },
            { id: 's4_architecture', name: 'Architecture Agent', role: 'Stage 4: System Design' },
            { id: 's5_backend', name: 'Backend Agent', role: 'Stage 5: Backend Development' },
            { id: 's6_api', name: 'API Integration Agent', role: 'Stage 6: API Integration' },
            { id: 's7_frontend', name: 'Frontend Agent', role: 'Stage 7: Frontend Generation' },
            { id: 's8_testing', name: 'Testing Agent', role: 'Stage 8: Quality Assurance' },
            { id: 's9_deployment', name: 'Deployment Agent', role: 'Stage 9: Deployment' },
            { id: 's10_monitoring', name: 'Monitoring Agent', role: 'Stage 10: Observability' },
            { id: 's11_docs', name: 'Documentation Agent', role: 'Stage 11: Documentation' },
            { id: 's12_maintenance', name: 'Maintenance Agent', role: 'Stage 12: Maintenance' },
            { id: 's13_design', name: 'Design Agent', role: 'Stage 13: Visual Design' },
            { id: 'x1_review', name: 'Code Review Agent', role: 'Review: Structural Analysis' },
            { id: 'x2_security', name: 'Security Review Agent', role: 'Review: Security Audit' },
            { id: 'x3_performance', name: 'Performance Review Agent', role: 'Review: Performance' },
            { id: 'x4_board', name: 'Review Board', role: 'Review: Multi-Agent Consensus' },
            { id: 'h5_ram', name: 'RAM Governor Agent', role: 'Health: Active Memory Limiter' },
            { id: 'sentry', name: 'Sentry Layer Agent', role: 'Security: Triple Gate Guard' }
        ];
    }

    function getRecentActivityLogs() {
        return [
            { agent: 'S1', status: 'success', message: 'Input idea validated and synthesized into core app concepts.' },
            { agent: 'S3', status: 'success', message: 'Obsidian vault updated: created PRD markdown structure.' },
            { agent: 'X2', status: 'success', message: 'Triple Gate Security scan complete: 0 vulnerabilities found.' },
            { agent: 'H5', status: 'success', message: 'ResourceGuard capacity check: OK. Free memory 6144 MB.' },
            { agent: 'B3', status: 'success', message: 'Interest Tracker triggered on "fault-tolerant swarm orchestration".' }
        ];
    }

    // Initial check
    checkBackend();
    setInterval(checkBackend, 15000);
});
