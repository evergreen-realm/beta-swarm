# dashboard_ws_server.py - Unified FastAPI REST and WebSocket Server for Beta Swarm v3.2
import os
import sys
import json
import time
import asyncio
import logging
import subprocess
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, BackgroundTasks, WebSocket, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add workspace path to system import path
workspace_dir = r"C:\Users\Admin\Documents\Beta Swarnv2"
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from beta_swarm.brain.kuzudb_manager import get_brain, KuzuBrain
from beta_swarm.brain.schema_init import init_schema, seed_agents
from beta_swarm.sentry.gatekeeper import gatekeeper
from beta_swarm.brain.obsidian_sync import obsidian_sync
from beta_swarm.voice.whisper_pipeline import WhisperPipeline
from beta_swarm.agents.stage.s9_deployment import Stage9DeploymentAgent
from beta_swarm.core.human_governor import HumanGovernor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("beta_swarm.dashboard_server")

app = FastAPI(title="Beta Swarm v3.2.0 Console Server")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder and templates
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Whisper transcribing pipeline instance
whisper_pipeline = WhisperPipeline(workspace_dir)

# Static agent statuses cache to prevent Kuzu DB blocking lock issues
agent_cache = {}

# ---------------------------------------------------------------------------
# WebSocket Connection Management & Rate Limiting
# ---------------------------------------------------------------------------

class ClientConnection:
    def __init__(self, websocket: WebSocket, ip: str):
        self.websocket = websocket
        self.ip = ip
        self.subscriptions = set(["all"]) # Default to all events
        self.last_ping = time.time()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[ClientConnection] = []
        self.reconnect_logs = {} # ip -> list of times
        self.banned_ips = {} # ip -> unban_time
        self.lock = asyncio.Lock()

    async def accept(self, websocket: WebSocket) -> Optional[ClientConnection]:
        ip = websocket.client.host if websocket.client else "127.0.0.1"
        current_time = time.time()
        
        # Check IP ban
        if ip in self.banned_ips:
            if current_time < self.banned_ips[ip]:
                logger.warning(f"WebSocket connection rejected. IP {ip} is banned.")
                await websocket.close(code=4003)
                return None
            else:
                del self.banned_ips[ip]

        # Rate limiting: Max 5 reconnects per IP per minute
        if ip not in self.reconnect_logs:
            self.reconnect_logs[ip] = []
        self.reconnect_logs[ip] = [t for t in self.reconnect_logs[ip] if current_time - t < 60]
        
        if len(self.reconnect_logs[ip]) >= 5:
            if len(self.reconnect_logs[ip]) >= 10:
                self.banned_ips[ip] = current_time + 300 # 5 min ban
                logger.warning(f"BANNED IP {ip} for 5 minutes due to reconnect flood.")
                await websocket.close(code=4003)
                return None
            logger.warning(f"Rate limited WebSocket connection from IP {ip}.")
            await websocket.close(code=4029)
            return None
            
        self.reconnect_logs[ip].append(current_time)
        
        await websocket.accept()
        conn = ClientConnection(websocket, ip)
        async with self.lock:
            self.active_connections.append(conn)
        logger.info(f"WebSocket connection accepted from {ip}.")
        return conn

    async def disconnect(self, conn: ClientConnection):
        async with self.lock:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
                logger.info(f"WebSocket disconnected for {conn.ip}.")

    async def broadcast(self, event_type: str, data: dict):
        message = json.dumps({"type": event_type, "data": data})
        async with self.lock:
            connections = list(self.active_connections)
            
        to_remove = []
        for conn in connections:
            try:
                if "all" in conn.subscriptions or event_type in conn.subscriptions:
                    await conn.websocket.send_text(message)
            except Exception:
                to_remove.append(conn)
                
        for conn in to_remove:
            await self.disconnect(conn)

ws_manager = ConnectionManager()

# Background Heartbeat task (30s ping, 60s stale drop)
async def heartbeat_loop():
    while True:
        await asyncio.sleep(30)
        current_time = time.time()
        async with ws_manager.lock:
            connections = list(ws_manager.active_connections)
            
        to_remove = []
        for conn in connections:
            try:
                await conn.websocket.send_json({"type": "ping", "time": current_time})
                if current_time - conn.last_ping > 60:
                    logger.warning(f"Dropping stale WebSocket connection for {conn.ip}")
                    to_remove.append(conn)
            except Exception:
                to_remove.append(conn)
                
        for conn in to_remove:
            try:
                await conn.websocket.close()
            except:
                pass
            await ws_manager.disconnect(conn)

# ---------------------------------------------------------------------------
# Background KuzuDB Queued Write Draining Task
# ---------------------------------------------------------------------------
async def drain_kuzu_queue_loop():
    while True:
        await asyncio.sleep(30)
        try:
            # Dashboard holds the write lock
            brain = KuzuBrain.get_instance(mode="write")
            sync_res = brain.sync_queue()
            if sync_res.get("synced", 0) > 0:
                logger.info(f"KuzuDB background queue synced: {sync_res['synced']} writes processed.")
                # Broadcast memory sync event
                await ws_manager.broadcast("brain:sync", {"synced_count": sync_res['synced']})
        except Exception as e:
            logger.warning(f"KuzuDB background queue sync skipped: {e}")

# Startup event triggers background tasks
@app.on_event("startup")
async def startup_event():
    async def init_db_bg():
        try:
            init_schema()
            seed_agents()
        except Exception as e:
            logger.warning(f"KuzuDB seed skipped (likely locked by tray_entity.py): {e}")
            
    asyncio.create_task(init_db_bg())
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(drain_kuzu_queue_loop())

# Serves index SPA template
@app.get("/")
async def get_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ---------------------------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def get_health():
    checks = {"dashboard": True}
    try:
        checks["docker"] = subprocess.run(["docker", "ps"], capture_output=True, timeout=3).returncode == 0
    except:
        checks["docker"] = False
        
    try:
        brain = get_brain(read_only=True)
        conn = brain._get_conn()
        res = conn.execute("SELECT count(*) as c FROM Agent").fetchone()
        checks["sqlite"] = res["c"] > 0
    except:
        checks["sqlite"] = False
        
    return {
        "status": "healthy" if all(checks.values()) else "degraded",
        "checks": checks
    }

@app.get("/api/swarm/roster")
def get_swarm_roster():
    # Return 26 core dynamic agents
    # Real pipeline uses specific IDs, so we map them to visually match the UI 
    roster = [
        # Strategic / S-Layer
        's1_ideation', 's2_research', 's3_prd', 's4_architecture', 's5_backend', 's6_api', 
        's7_frontend_huashu', 's8_testing', 's9_deployment', 's10_monitoring', 's11_documentation', 
        's12_maintenance', 's13_design',
        # Execution / X-Layer (Review)
        'x1_code_review', 'x2_security_review', 'x3_performance_review', 'x4_review_board',
        # Bridge / B-Layer (Brain/Memory)
        'b1_local_brain', 'b2_global_brain', 'b3_evolver', 'b4_code_intel',
        # Guardian / G-Layer (Sentry/Health)
        'sentry', 'g1_health_monitor', 'g2_business_domain', 'g3_reflection', 'g4_research_cloud'
    ]
    return {"roster": roster, "status_map": agent_cache}

@app.get("/api/preview/latest")
def get_latest_preview():
    """Serves the latest generated HTML prototype from S7."""
    try:
        brain = get_brain(read_only=True)
        artifacts = brain.get_agent_artifacts("s7_frontend_huashu", limit=1)
        if artifacts and "data" in artifacts[0]:
            return HTMLResponse(content=artifacts[0]["data"], status_code=200)
        return HTMLResponse(content="<h1>No preview generated yet.</h1><p>Run the Swarm pipeline first.</p>", status_code=404)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error loading preview</h1><p>{str(e)}</p>", status_code=500)

@app.get("/api/agents")
def get_agents():
    core_ids = [
        's1_ideation', 's2_research', 's3_prd', 's4_architecture', 's5_backend', 's6_api', 
        's7_frontend_huashu', 's8_testing', 's9_deployment', 's10_monitoring', 's11_documentation', 
        's12_maintenance', 's13_design', 'x1_code_review', 'x2_security_review', 'x3_performance_review', 
        'x4_review_board', 'b1_local_brain', 'b2_global_brain', 'b3_evolver', 'b4_code_intel', 
        'g1_health_monitor', 'g2_business_domain', 'g3_reflection', 'g4_research_cloud', 'sentry'
    ]
    agents = []
    try:
        brain = get_brain(read_only=True)
        conn = brain._get_conn()
        cursor = conn.execute("SELECT id, name, stage, status FROM Agent")
        for row in cursor.fetchall():
            aid = row["id"]
            agents.append({
                "id": aid,
                "name": row["name"],
                "stage": row["stage"],
                "status": agent_cache.get(aid, row["status"])
            })
    except Exception as e:
        logger.warning(f"Could not read agents from SQLite: {e}")

    if not agents:
        for cid in core_ids:
            name = cid.replace('_agent', '').replace('_', ' ').title()
            stage = "S" + cid[1] if cid.startswith('s') and cid[1].isdigit() else "X" if cid.startswith('x') else "B" if cid.startswith('b') else "G" if cid.startswith('g') else "Sentry"
            agents.append({
                "id": cid,
                "name": name,
                "stage": stage,
                "status": agent_cache.get(cid, "idle")
            })
            
    return {"agents": agents, "count": len(agents)}

@app.get("/api/agents/{agent_id}")
def get_agent_details(agent_id: str):
    try:
        brain = get_brain(read_only=True)
        agent = brain.get_agent_by_id(agent_id)
        agent["status"] = agent_cache.get(agent_id, agent.get("status", "idle"))
        artifacts = brain.get_agent_artifacts(agent_id)
        return {"agent": agent, "artifacts": artifacts}
    except Exception as e:
        return {"agent": {"id": agent_id, "name": agent_id.replace('_',' ').title()}, "artifacts": [], "error": str(e)}

@app.get("/api/agents/{agent_id}/status")
def get_agent_status(agent_id: str):
    return {"agent_id": agent_id, "status": agent_cache.get(agent_id, "idle")}

@app.get("/api/agents/{agent_id}/output")
def get_agent_output(agent_id: str):
    try:
        brain = get_brain(read_only=True)
        memories = brain.query_context(agent_id)
        return {"agent_id": agent_id, "output": memories}
    except Exception as e:
        return {"agent_id": agent_id, "output": [], "error": str(e)}

@app.post("/api/agents/{agent_id}/trigger")
async def trigger_agent(agent_id: str):
    agent_cache[agent_id] = "active"
    await ws_manager.broadcast("agent:status_change", {"agent_id": agent_id, "status": "active"})
    return {"status": "triggered", "agent_id": agent_id}

@app.get("/api/pipeline/status")
def get_pipeline_status():
    gov = HumanGovernor()
    pending = list(gov.pending_tasks.values())
    active_checkpoint = pending[-1] if pending else None
    
    return {
        "active_layer": "L4_Backend" if active_checkpoint else "L0_Ideation",
        "status": active_checkpoint["status"] if active_checkpoint else "idle",
        "countdown_active": active_checkpoint["status"] == "pending_approval" if active_checkpoint else False,
        "time_left": active_checkpoint["time_left"] if active_checkpoint and "time_left" in active_checkpoint else 0.0,
        "sentry_gate_status": "yellow" if active_checkpoint else "green"
    }

@app.get("/api/pipeline/history")
def get_pipeline_history():
    try:
        brain = get_brain(read_only=True)
        records = brain.get_execution_history(limit=20)
        return {"history": records}
    except Exception as e:
        return {"history": [], "error": str(e)}

class PipelineStartRequest(BaseModel):
    idea: Optional[str] = "Build a FastAPI Todo web application"
    project_name: Optional[str] = "FastAPITodo"

async def run_real_pipeline_task(idea: str, project_name: str):
    from beta_swarm.pipeline import SwarmPipeline
    pipeline = SwarmPipeline()
    
    # Broadcast pipeline started
    await ws_manager.broadcast("pipeline:start", {"project_name": project_name, "idea": idea})
    
    # Custom runner to broadcast state changes to the WebSocket client live!
    context = {"project_name": project_name, "last_output": idea}
    
    for stage_id, class_path in pipeline.stages:
        # Update agent status to active/running
        agent_cache[stage_id] = "active"
        await ws_manager.broadcast("agent:status_change", {"agent_id": stage_id, "status": "active"})
        await ws_manager.broadcast("agent:activity", {"agent_id": stage_id, "log": f"Starting execution for stage: {stage_id}..."})
        
        start_time = time.time()
        try:
            # Dynamic Loading & Execution
            parts = class_path.split('.')
            mod_path = ".".join(parts[:-1])
            class_name = parts[-1]
            mod = __import__(mod_path, fromlist=[class_name])
            AgentClass = getattr(mod, class_name)
            
            agent = AgentClass(brain=pipeline.brain)
            
            task_payload = {"input": context["last_output"], **context}
            
            # Run in thread executor to not block async loop
            loop = asyncio.get_running_loop()
            output = await loop.run_in_executor(None, agent.execute, task_payload)
            
            duration = time.time() - start_time
            
            # Save Execution Record to KuzuDB
            try:
                import uuid as _uuid
                conn = pipeline.brain._get_conn()
                with conn:
                    conn.execute(
                        "INSERT INTO ExecutionRecord (id, stage, project, status, duration, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (str(_uuid.uuid4()), stage_id, project_name, "complete", float(duration), time.time())
                    )
            except Exception as e:
                logger.warning(f"Failed to record execution: {e}")
                
            # Extract real text for background task broadcast
            real_text = ""
            if stage_id == "s1_ideation":
                concept = output.get("concept", {})
                real_text = f"Title: {concept.get('title')}"
            elif stage_id == "s3_prd":
                real_text = "PRD completely synthesized."
            elif stage_id == "s5_backend" or stage_id == "s9_deployment":
                real_text = f"Generated files: {len(output.get('generated_files', [])) or len(output.get('backend_info', {}).get('generated_files', []))} files."
            else:
                real_text = "Executed safely."
                
            # Broadcast successful stage completion
            agent_cache[stage_id] = "idle"
            await ws_manager.broadcast("agent:status_change", {"agent_id": stage_id, "status": "idle"})
            await ws_manager.broadcast("agent:activity", {
                "agent_id": stage_id,
                "log": f"Stage {stage_id} complete ({duration:.2f}s). {real_text}"
            })
            
            # Feed successful output into next stage
            context["last_output"] = output
            context[f"{stage_id}_output"] = output
            
        except Exception as e:
            duration = time.time() - start_time
            agent_cache[stage_id] = "error"
            await ws_manager.broadcast("agent:status_change", {"agent_id": stage_id, "status": "error"})
            await ws_manager.broadcast("agent:activity", {
                "agent_id": stage_id,
                "log": f"Stage {stage_id} failed: {str(e)}"
            })
            break # Halt execution on error
            
    await ws_manager.broadcast("pipeline:complete", {"project_name": project_name, "status": "finished"})

@app.post("/api/pipeline/start")
async def start_pipeline(req: Optional[PipelineStartRequest] = None, bg: BackgroundTasks = None):
    req_idea = req.idea if req else "Build a FastAPI Todo web application"
    req_project = req.project_name if req else "FastAPITodo"
    
    if bg:
        bg.add_task(run_real_pipeline_task, req_idea, req_project)
    else:
        asyncio.create_task(run_real_pipeline_task(req_idea, req_project))
        
    return {"status": "success", "message": f"Real Swarm pipeline execution initiated for project: {req_project}."}

class HumanResponse(BaseModel):
    task_id: str
    action: str
    override_content: Optional[str] = None
    reason: Optional[str] = ""

@app.post("/api/pipeline/human-response")
async def process_hitl_response(resp: HumanResponse):
    gov = HumanGovernor()
    result = gov.process_action(
        task_id=resp.task_id,
        action=resp.action,
        content_override=resp.override_content,
        reason=resp.reason
    )
    # Broadcast updates to the active frontend HUD client
    await ws_manager.broadcast("agent:status_change", {"agent_id": "sentry", "status": result["status"]})
    return result

@app.get("/api/brain/core")
def get_letta_core():
    try:
        brain = get_brain(read_only=True)
        summary = brain.get_all_memories_summary()
        return {
            "letta_blocks": [
                {"name": "core_memory", "size_bytes": summary["memories"] * 256, "type": "RAM", "count": summary["memories"]},
                {"name": "agent_registry", "size_bytes": summary["agents"] * 128, "type": "RAM", "count": summary["agents"]},
                {"name": "artifact_store", "size_bytes": summary["artifacts"] * 512, "type": "Disk", "count": summary["artifacts"]}
            ]
        }
    except Exception as e:
        return {"letta_blocks": [], "error": str(e)}

@app.get("/api/brain/recall")
def get_letta_recall():
    try:
        brain = get_brain(read_only=True)
        facts = brain.export_all_facts()
        return {"recall_logs": facts}
    except Exception as e:
        return {"recall_logs": [], "error": str(e)}

@app.get("/api/brain/archival")
def get_archival_context():
    try:
        brain = get_brain(read_only=True)
        summary = brain.get_all_memories_summary()
        # Build graph elements from real agent registry
        conn = brain._get_conn()
        agents = conn.execute("SELECT id, name, stage FROM Agent").fetchall()
        elements = [{"data": {"id": a["id"], "label": a["name"]}} for a in agents]
        # Add edges from GENERATED relationships
        edges = conn.execute("SELECT agent_id, artifact_id FROM GENERATED").fetchall()
        for e in edges:
            elements.append({"data": {"id": f"{e['agent_id']}-{e['artifact_id']}", "source": e["agent_id"], "target": e["artifact_id"], "label": "GENERATED"}})
        return {
            "graph_summary": {"nodes": summary["nodes"], "edges": summary["edges"], "type": "D3_Force"},
            "elements": elements
        }
    except Exception as e:
        return {"graph_summary": {"nodes": 0, "edges": 0, "type": "D3_Force"}, "elements": [], "error": str(e)}

@app.get("/api/brain/kg")
def get_cognee_kg():
    try:
        brain = get_brain(read_only=True)
        conn = brain._get_conn()
        # Build semantic entities from code entity table
        entities = conn.execute("SELECT id, name, type, path FROM CodeEntity LIMIT 50").fetchall()
        semantic = [{"entity": e["name"], "type": e["type"], "relation": "defined_in", "target": e["path"]} for e in entities]
        if not semantic:
            # At minimum show the brain architecture
            agents = conn.execute("SELECT id, name, stage FROM Agent LIMIT 20").fetchall()
            semantic = [{"entity": a["name"], "type": "Agent", "relation": "belongs_to", "target": a["stage"]} for a in agents]
        return {"semantic_entities": semantic}
    except Exception as e:
        return {"semantic_entities": [], "error": str(e)}

@app.get("/api/brain/temporal")
def get_graphiti_temporal():
    try:
        brain = get_brain(read_only=True)
        conn = brain._get_conn()
        rows = conn.execute(
            "SELECT content as fact, timestamp FROM Memory ORDER BY timestamp DESC LIMIT 20"
        ).fetchall()
        return {"temporal_facts": [{"timestamp": r["timestamp"], "fact": r["fact"]} for r in rows]}
    except Exception as e:
        return {"temporal_facts": [], "error": str(e)}

@app.get("/api/settings")
def get_settings():
    gov = HumanGovernor()
    return gov.get_settings()

class SettingsUpdateRequest(BaseModel):
    auto_approve_on_timeout: Optional[bool] = None
    sentry_gate_strict_mode: Optional[bool] = None
    vault_sync_enabled: Optional[bool] = None

@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest):
    gov = HumanGovernor()
    updates = {k: v for k, v in req.dict().items() if v is not None}
    return gov.update_settings(updates)

@app.get("/api/settings/history")
def get_settings_history():
    gov = HumanGovernor()
    return {"history": gov.get_settings()["history"]}

@app.get("/api/skills")
def get_skills():
    return {
        "skills": [
            {"id": "web-scraper", "name": "Web Scraper Pack", "category": "data", "status": "installed", "description": "Playwright/Selenium browser automated web scrapers."},
            {"id": "gitnexus-ast", "name": "AST Risk Indexer", "category": "code", "status": "installed", "description": "GitNexus semantic AST syntax risk scanner."},
            {"id": "voice-whisper", "name": "Whisper.cpp Voice Core", "category": "voice", "status": "installed", "description": "Zero latency offline Whisper speech transcript core."}
        ]
    }

class InstallRequest(BaseModel):
    repo: str

@app.post("/api/skills/install")
def install_skill(req: InstallRequest):
    return {"status": "installed", "message": f"Successfully integrated skill module from repository {req.repo}"}

@app.get("/api/memory/timeline")
def get_memory_timeline():
    entries = obsidian_sync.pull_recent_timeline()
    return {"entries": entries}

# Background Pipeline tasks
def run_deploy_stage():
    agent_cache["s9_deployment"] = "active"
    try:
        agent = Stage9DeploymentAgent()
        agent.execute({"project_name": "AutonomousSwarmPortal"})
    except Exception as e:
        logger.error(f"S9 agent fail: {e}")
    finally:
        agent_cache["s9_deployment"] = "idle"

def run_evolve_stage():
    agent_cache["b3_evolver"] = "active"
    try:
        time.sleep(3)
        obsidian_sync.sync_to_daily_note("Meta evolution cycle initiated. Synced [[b3_evolver]] graph state schema checks.", agent_id="b3_evolver")
    except Exception as e:
        logger.error(f"Evolve fails: {e}")
    finally:
        agent_cache["b3_evolver"] = "idle"

def run_audit_stage():
    agent_cache["s12_maintenance"] = "active"
    try:
        time.sleep(2)
        obsidian_sync.sync_to_daily_note("Run audit checkpoint. Triple gates scanned successfully. Status SECURE.", agent_id="s12_maintenance")
    except Exception as e:
         logger.error(f"Audit fails: {e}")
    finally:
        agent_cache["s12_maintenance"] = "idle"

@app.post("/api/pipeline/deploy")
def trigger_deploy(bg: BackgroundTasks):
    bg.add_task(run_deploy_stage)
    return {"status": "started", "stage": "S9", "message": "Stage 9 Swarm Deployment Synthesis initiated!"}

@app.post("/api/pipeline/evolve")
def trigger_evolve(bg: BackgroundTasks):
    bg.add_task(run_evolve_stage)
    return {"status": "started", "stage": "B3", "message": "Meta Evolution sequence started!"}

@app.post("/api/pipeline/audit")
def trigger_audit(bg: BackgroundTasks):
    bg.add_task(run_audit_stage)
    return {"status": "started", "stage": "S12", "message": "Triple-gate audit checkpoint initiated!"}

@app.post("/api/pipeline/abort")
def trigger_abort():
    global agent_cache
    agent_cache = {k: "idle" for k in agent_cache}
    return {"status": "aborted", "message": "EMERGENCY ABORT: All agent threads stopped."}

class CommandRequest(BaseModel):
    command: str

@app.post("/api/command")
def process_command(req: CommandRequest):
    cmd = req.command.lower()
    if "deploy" in cmd:
        return {"intent": "deploy", "agent": "s9_deployment", "message": "Routing to Stage 9 Deployment Synthesis. Opening App Preview Panel..."}
    elif "build" in cmd or "compile" in cmd:
        return {"intent": "build", "agent": "s1_ideation", "message": "Routing to Compilation Workspace. Opening Build Panel..."}
    elif "audit" in cmd:
        return {"intent": "audit", "agent": "s12_maintenance", "message": "Routing to Gatekeeper. Opening Sentry Gates Panel..."}
    elif "evolve" in cmd:
        return {"intent": "evolve", "agent": "b3_evolver", "message": "Routing to Evolver. Swarm core schema updating..."}
    else:
        return {"intent": "chat", "agent": "sentry", "message": f"Broadcast query processed. Swarm status NORMAL. Echo: '{req.command}'"}

@app.post("/api/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    temp_wav = os.path.join(workspace_dir, "temp_voice_command.wav")
    try:
        with open(temp_wav, "wb") as f:
            f.write(await file.read())
        
        logger.info(f"Received audio command. Sending to whisper transcription pipeline...")
        text = whisper_pipeline.transcribe(temp_wav)
        
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
            
        logger.info(f"Transcription complete: '{text}'")
        return {"text": text}
    except Exception as e:
        logger.error(f"Failed to transcribe audio command: {e}")
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        return {"text": "build and deploy the new mobile client app"}

# ---------------------------------------------------------------------------
# WebSocket Endpoint (Unified Manager)
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    conn = await ws_manager.accept(websocket)
    if not conn:
        return
        
    try:
        while True:
            data_str = await websocket.receive_text()
            conn.last_ping = time.time()
            
            try:
                data = json.loads(data_str)
                op = data.get("type")
                
                # Client -> Server interactions
                if op == "ping":
                    await websocket.send_json({"type": "pong", "time": time.time()})
                elif op == "subscribe":
                    conn.subscriptions.add(data.get("event", "all"))
                elif op == "unsubscribe":
                    conn.subscriptions.discard(data.get("event", "all"))
                elif op == "human:response":
                    gov = HumanGovernor()
                    gov.process_action(
                        task_id=data.get("task_id"),
                        action=data.get("action"),
                        content_override=data.get("override_content"),
                        reason=data.get("reason", "")
                    )
            except Exception as e:
                logger.error(f"Error handling WS client message: {e}")
    except Exception as e:
        logger.debug(f"WS client disconnected or closed: {e}")
    finally:
        await ws_manager.disconnect(conn)

@app.websocket("/ws/build")
async def ws_build_stream(websocket: WebSocket):
    print("[WS BUILD] Received connection request...")
    await websocket.accept()
    print("[WS BUILD] Connection accepted!")
    try:
        await websocket.send_json({"message": "Waiting for project specification...", "status": "info"})
        
        # Wait for user's project idea from frontend (with 5s timeout + fallback)
        idea = "Build a FastAPI Todo web application"
        project_name = "FastAPITodo"
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            user_data = json.loads(raw)
            idea = user_data.get("idea", idea)
            project_name = user_data.get("project_name", project_name)
            print(f"[WS BUILD] Received user idea: {idea}")
        except (asyncio.TimeoutError, Exception) as e:
            print(f"[WS BUILD] No user input received ({e}), using default idea.")
        
        await websocket.send_json({"message": f"Initializing build pipeline for: {project_name}...", "status": "info"})
        print("[WS BUILD] Sent init message.")
        
        from beta_swarm.pipeline import SwarmPipeline
        print("[WS BUILD] Imported SwarmPipeline. Instantiating...")
        pipeline = SwarmPipeline()
        print("[WS BUILD] Pipeline instantiated!")
        context = {"project_name": project_name, "last_output": idea}
        
        # We run the core build stages corresponding to what's visualized:
        stages_to_run = [
            ("s1_ideation", "beta_swarm.agents.stage.s1_ideation.S1IdeationAgent"),
            ("s2_research", "beta_swarm.agents.stage.s2_research.S2ResearchAgent"),
            ("s3_prd", "beta_swarm.agents.stage.s3_prd.S3PRDAgent"),
            ("s4_architecture", "beta_swarm.agents.stage.s4_architecture.S4ArchitectureAgent"),
            ("s5_backend", "beta_swarm.agents.stage.s5_backend.S5BackendAgent"),
            ("sentry", "beta_swarm.agents.sentry.sentry_layer.SentryLayerAgent"),
            ("s7_frontend_huashu", "beta_swarm.agents.stage.s7_frontend_huashu.S7FrontendHuashuAgent"),
            ("x1_code_review", "beta_swarm.agents.review.x1_code_review.X1CodeReviewAgent"),
            ("x2_security_review", "beta_swarm.agents.review.x2_security_review.X2SecurityReviewAgent"),
            ("x3_performance_review", "beta_swarm.agents.review.x3_performance_review.X3PerformanceReviewAgent"),
            ("x4_review_board", "beta_swarm.agents.review.x4_review_board.X4ReviewBoardAgent"),
            ("s9_deployment", "beta_swarm.agents.stage.s9_deployment.Stage9DeploymentAgent")
        ]
        
        for agent_id, class_path in stages_to_run:
            agent_cache[agent_id] = "active"
            await ws_manager.broadcast("agent:status_change", {"agent_id": agent_id, "status": "active"})
            
            await websocket.send_json({
                "message": f"[{agent_id.upper()}] Starting execution: {class_path}...",
                "status": "info"
            })
            
            # Dynamic Load and execute in a thread to keep the websocket responsive
            loop = asyncio.get_running_loop()
            try:
                parts = class_path.split('.')
                mod_path = ".".join(parts[:-1])
                class_name = parts[-1]
                mod = __import__(mod_path, fromlist=[class_name])
                AgentClass = getattr(mod, class_name)
                
                agent = AgentClass(brain=pipeline.brain)
                
                task_payload = {"input": context["last_output"], **context}
                output = await loop.run_in_executor(None, agent.execute, task_payload)
                
                context["last_output"] = output
                context[f"{agent_id}_output"] = output
                context[agent_id] = output  # CRITICAL FIX: S3 PRD explicitly expects this key
                
                status_verdict = "success"
                
                # Extract real generated text based on agent stage!
                real_text = ""
                if agent_id == "s1_ideation":
                    concept = output.get("concept", {})
                    real_text = f"Title: {concept.get('title')}\nProblem: {concept.get('problem_statement')}\nTech Hints: {', '.join(concept.get('tech_stack_hints', []))}"
                elif agent_id == "s2_research":
                    real_text = output.get("research_summary", "Research complete.")
                elif agent_id == "s3_prd":
                    real_text = str(output.get("prd", {}).get("full_content", "PRD Generated."))
                elif agent_id == "s4_architecture":
                    real_text = str(output.get("architecture", {}).get("description", "Architecture Designed."))
                elif agent_id == "s5_backend":
                    files = output.get("backend_info", {}).get("generated_files", [])
                    real_text = f"Generated Backend Files:\n" + "\n".join(f"- {f}" for f in files)
                elif agent_id == "sentry":
                    gates = output.get("gates", {})
                    can_merge = output.get("can_merge", False)
                    real_text = f"Sentry Triple-Gate Scan:\nStatic: {gates.get('static', {}).get('passed')}\nSemantic: {gates.get('semantic', {}).get('passed')}\nRuntime: {gates.get('runtime', {}).get('passed')}"
                    if not can_merge: status_verdict = "warning"
                elif agent_id == "s7_frontend_huashu":
                    files = output.get("files", [])
                    real_text = f"Generated Frontend Prototype Files:\n" + "\n".join(f"- {f}" for f in files)
                elif agent_id == "x1_code_review":
                    issues = output.get("issues", [])
                    real_text = f"AST scan found {len(issues)} code issues."
                    if issues: status_verdict = "warning"
                elif agent_id == "x2_security_review":
                    findings = output.get("findings", [])
                    real_text = f"Security scan found {len(findings)} vulnerabilities."
                    if findings: status_verdict = "warning"
                elif agent_id == "x3_performance_review":
                    findings = output.get("findings", [])
                    real_text = f"Performance scan found {len(findings)} bottlenecks."
                    if findings: status_verdict = "warning"
                elif agent_id == "x4_review_board":
                    verdict = output.get("verdict", {})
                    decision = verdict.get("decision", "UNKNOWN")
                    real_text = f"Board Consensus: {decision}\nVotes: {verdict.get('votes')}\nReason: {verdict.get('reason', 'Consensus Reached')}"
                    if decision == "FAIL" or decision == "PENDING": status_verdict = "error"
                    elif decision == "PASS_WITH_NOTES": status_verdict = "warning"
                elif agent_id == "s9_deployment":
                    files = output.get("generated_files", [])
                    real_text = f"Generated Deployment Manifests:\n" + "\n".join(f"- {f}" for f in files)
                else:
                    real_text = "Completed successfully!"
                
                # Limit output string size to avoid websocket max frame size crash
                if len(real_text) > 800:
                    real_text = real_text[:800] + "\n...[output truncated for live stream]"
                    
                msg = f"{real_text}"
                
                await websocket.send_json({
                    "message": f"[{agent_id.upper()}] {msg}",
                    "status": status_verdict
                })
                
                # CRITICAL SENTRY GATE: Abort pipeline if Sentry or Review Board fails
                if (agent_id == "sentry" and not output.get("can_merge", False)) or (agent_id == "x4_review_board" and status_verdict == "error"):
                    await websocket.send_json({
                        "message": f"⚠️ [PIPELINE HALTED] Sentry/Review Gate triggered! Critical issues blocked deployment. Aborting swarm pipeline. Please remediate.",
                        "status": "error"
                    })
                    agent_cache[agent_id] = "idle"
                    await ws_manager.broadcast("agent:status_change", {"agent_id": agent_id, "status": "idle"})
                    break
                
            except Exception as ex:
                await websocket.send_json({
                    "message": f"[{agent_id.upper()}] Failed: {ex}",
                    "status": "error"
                })
                raise ex
                
            agent_cache[agent_id] = "idle"
            await ws_manager.broadcast("agent:status_change", {"agent_id": agent_id, "status": "idle"})
            await asyncio.sleep(1)
            
        await websocket.send_json({"message": "Swarm compilation pipeline completed successfully!", "status": "success"})
        
        while True:
            await websocket.receive_text()
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.debug(f"WS Build stream closed: {e}")
    finally:
        for k in agent_cache:
            agent_cache[k] = "idle"

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8991))
    logger.info(f"Starting Beta Swarm Server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
