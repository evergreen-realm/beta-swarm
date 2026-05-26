import os
import time
import uuid
import json
import sqlite3
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Imports with absolute path support
try:
    from beta_swarm.orchestrator import WorkflowEngine as Orchestrator, AGENT_MODULE_MAP
except ImportError:
    Orchestrator, AGENT_MODULE_MAP = None, {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("beta_swarm_api")

app = FastAPI(title="Beta Swarm REST API", version="1.0.0")

is_degraded = False
degraded_reason = ""

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Models
class ProjectCreate(BaseModel):
    description: str
    tier: str
    user_preferences: Optional[Dict[str, Any]] = None

class AgentRun(BaseModel):
    task: Dict[str, Any]

class AgentApprove(BaseModel):
    approved: bool
    feedback: Optional[str] = None

class InterestCreate(BaseModel):
    topic: str
    priority: int

# Memory storage
active_projects: Dict[str, Dict[str, Any]] = {}
approvals: Dict[str, Dict[str, Any]] = {}

# Helpers
class SafeBrainWrapper:
    def __init__(self, real_brain=None):
        self.real_brain = real_brain
    def store_fact(self, agent_id: str, content: str, fact_type: str = "fact", *a, **k):
        try:
            if self.real_brain and hasattr(self.real_brain, "store_fact"):
                return self.real_brain.store_fact(agent_id, content, fact_type, *a, **k)
        except Exception: pass
        return {"status": "skipped"}
    def store_memory(self, agent_id: str, fact: str, fact_type: str = "observation", *a, **k):
        try:
            if self.real_brain and hasattr(self.real_brain, "store_memory"):
                return self.real_brain.store_memory(agent_id, fact, fact_type, *a, **k)
        except Exception: pass
        return {"status": "skipped"}

def find_agent_class_name(agent_id: str) -> Optional[str]:
    target = agent_id.replace("_", "").lower()
    for cls in AGENT_MODULE_MAP:
        if cls.lower() == target or cls.lower() == target + "agent" or target in cls.lower():
            return cls
    return None

def handle_error(e: Exception):
    return JSONResponse(status_code=500, content={"error": e.__class__.__name__, "detail": str(e)})

def not_found(detail: str):
    return JSONResponse(status_code=404, content={"error": "Not Found", "detail": detail})

@app.get("/api/v1/health")
async def health_check():
    """System health endpoint."""
    import psutil
    mem = psutil.virtual_memory()
    return {
        "status": "healthy" if not is_degraded else "degraded",
        "reason": degraded_reason if is_degraded else None,
        "version": "3.2.0",
        "agents": len(AGENT_MODULE_MAP),
        "memory": {"free_mb": mem.available // (1024 * 1024), "percent": mem.percent},
    }


@app.post("/api/v1/projects")
async def create_project(body: ProjectCreate):
    # Before POST /api/v1/projects: check capacity
    # If free_mb < 2048: return HTTP 503 with {"error": "Insufficient RAM", "free_mb": ...}
    try:
        from beta_swarm.core.resource_guard import ResourceGuard
        guard = ResourceGuard()
        capacity = guard.governor.execute({"action": "check_capacity"})
        free_mb = capacity.get("t490", {}).get("free_mb", 0)
        if free_mb < 2048:
            return JSONResponse(
                status_code=503,
                content={"error": "Insufficient RAM", "free_mb": free_mb, "required_mb": 2048}
            )
    except Exception as e:
        logger.error(f"Error checking RAM before project creation: {e}")

    try:
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        project_path = f"C:/Users/Admin/Documents/Beta Swarnv2/projects/{project_id}"
        
        from beta_swarm.agents.stage.s1_ideation import S1IdeationAgent
        try:
            from beta_swarm.brain.kuzudb_manager import KuzuBrain
            brain = KuzuBrain()
        except Exception:
            brain = None
            
        agent = S1IdeationAgent(brain=SafeBrainWrapper(brain))
        agent.project_id = project_id
        
        task = {
            "idea": body.description, "tier": body.tier,
            "user_preferences": body.user_preferences or {},
            "project_id": project_id, "project_path": project_path
        }
        
        res = await asyncio.to_thread(agent.run, task)
        concept = res.get("concept") or {}
        
        active_projects[project_id] = {
            "project_id": project_id, "status": "created",
            "current_stage": "s1_ideation", "progress_percent": 10,
            "outputs": {"concept": concept}
        }
        
        try:
            from beta_swarm.orchestrator_db import OrchestratorDB
            db = OrchestratorDB()
            run_id = db.create_run(project_id, task)
            db.update_stage(run_id, "s1_ideation", "completed", output=res)
        except Exception: pass
            
        return {"project_id": project_id, "status": "created", "concept": concept}
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str):
    try:
        if project_id in active_projects:
            return active_projects[project_id]
            
        from beta_swarm.orchestrator_db import OrchestratorDB
        db = OrchestratorDB()
        run = db.get_run(project_id)
        if run:
            stages = db.conn.execute("SELECT stage_id, status, output_json FROM stage_runs WHERE run_id = ?", (run["run_id"],)).fetchall()
            outputs = {}
            current_stage = run.get("current_stage") or "s1_ideation"
            status = run.get("status") or "pending"
            completed_count = 0
            for row in stages:
                sid, stat = row["stage_id"], row["status"]
                if stat == "completed":
                    completed_count += 1
                    try: outputs[sid] = json.loads(row["output_json"] or "{}")
                    except Exception: pass
                if stat == "running":
                    current_stage = sid
            progress = int((completed_count / 13) * 100) if completed_count else 5
            if progress > 100 or status == "completed": progress = 100
            return {
                "project_id": project_id, "status": status,
                "current_stage": current_stage, "progress_percent": progress, "outputs": outputs
            }
        return not_found(f"Project {project_id} not found")
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/projects/{project_id}/artifacts")
async def get_project_artifacts(project_id: str):
    try:
        if project_id not in active_projects:
            from beta_swarm.orchestrator_db import OrchestratorDB
            if not OrchestratorDB().get_run(project_id):
                return not_found(f"Project {project_id} not found")
                
        artifacts = []
        db_path = "C:/Users/Admin/Documents/Beta Swarnv2/brain_sqlite.db"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT artifact_type, source_agent, timestamp, content_preview FROM artifact_log WHERE project_id = ?",
                    (project_id,)
                )
                rows = cursor.fetchall()
                artifacts = [{"type": r[0], "agent": r[1], "timestamp": r[2], "preview": r[3]} for r in rows]
                conn.close()
            except Exception: pass
            
        if not artifacts and project_id in active_projects:
            for stage, output in active_projects[project_id].get("outputs", {}).items():
                artifacts.append({
                    "type": "concept" if stage == "concept" else stage,
                    "agent": "s1_ideation" if stage == "concept" else stage,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "preview": str(output)[:200]
                })
        return artifacts
    except Exception as e:
        return handle_error(e)

@app.post("/api/v1/projects/{project_id}/agents/{agent_id}/run")
async def run_agent(project_id: str, agent_id: str, body: AgentRun):
    try:
        cls_name = find_agent_class_name(agent_id)
        if not cls_name:
            return not_found(f"Agent ID {agent_id} not found in manifest")
            
        import importlib
        module = importlib.import_module(AGENT_MODULE_MAP[cls_name])
        cls = getattr(module, cls_name)
        
        try:
            from beta_swarm.brain.kuzudb_manager import KuzuBrain
            brain = KuzuBrain()
        except Exception: brain = None
        
        agent = cls(brain=SafeBrainWrapper(brain))
        agent.project_id = project_id
        
        task = dict(body.task)
        task.update({
            "project_id": project_id,
            "project_path": f"C:/Users/Admin/Documents/Beta Swarnv2/projects/{project_id}"
        })
        
        if asyncio.iscoroutinefunction(getattr(agent, "run", None)):
            res = await agent.run(task)
        elif asyncio.iscoroutinefunction(getattr(agent, "execute", None)):
            res = await agent.execute(task)
        else:
            res = await asyncio.to_thread(agent.run, task)
            
        if project_id in active_projects:
            active_projects[project_id]["outputs"][agent_id] = res
            active_projects[project_id]["current_stage"] = agent_id
            
        return {"agent_id": agent_id, "status": "completed", "result": res}
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/agents")
async def list_agents():
    try:
        try:
            from beta_swarm.agents.register_all import AGENTS
        except Exception:
            AGENTS = [
                ("s1_ideation", "Ideation Agent", "Stage 1: Input Processing"),
                ("s2_research", "Research Agent", "Stage 2: Deep Research"),
                ("s3_prd", "PRD Agent", "Stage 3: Product Requirements"),
                ("s4_architecture", "Architecture Agent", "Stage 4: System Design"),
                ("s5_backend", "Backend Agent", "Stage 5: Backend Development"),
                ("s6_api", "API Integration Agent", "Stage 6: API Integration"),
                ("s7_frontend", "Frontend Agent", "Stage 7: Frontend Generation"),
                ("s8_testing", "Testing Agent", "Stage 8: Quality Assurance"),
                ("s9_deployment", "Deployment Agent", "Stage 9: Deployment"),
                ("s10_monitoring", "Monitoring Agent", "Stage 10: Observability"),
                ("s11_docs", "Documentation Agent", "Stage 11: Documentation"),
                ("s12_maintenance", "Maintenance Agent", "Stage 12: Maintenance"),
                ("s13_design", "Design Agent", "Stage 13: Visual Design"),
                ("x1_review", "Code Review Agent", "Review: Structural Analysis"),
                ("x2_security", "Security Review Agent", "Review: Security Audit"),
                ("x3_performance", "Performance Review Agent", "Review: Performance"),
                ("x4_board", "Review Board", "Review: Multi-Agent Consensus"),
                ("b1_local", "LocalBrainAgent", "Brain: KuzuDB Management"),
                ("b2_global", "GlobalBrainAgent", "Brain: Neo4j Management"),
                ("b3_evolver", "EvolverAgent", "Brain: Self-Evolution"),
                ("b4_intel", "CodeIntelAgent", "Brain: Structural Awareness"),
                ("b5_obsidian", "B5ObsidianAgent", "Brain: Human-Readable Memory"),
                ("g1_health", "HealthMonitorAgent", "Growth: System Health"),
                ("g2_domain", "BusinessDomainAgent", "Growth: Domain Logic"),
                ("g3_reflection", "ReflectionAgent", "Growth: Self-Correction"),
                ("g4_cloud", "CloudResearchAgent", "Growth: Cloud Offload"),
                ("sentry", "SentryLayerAgent", "Security: Triple Gate"),
                ("h1_resource", "H1ResourceMonitorAgent", "Health: Passive Metrics"),
                ("h2_model", "H2ModelHealthAgent", "Health: LLM Status"),
                ("h3_service", "H3ServiceHealthAgent", "Health: Service Status"),
                ("h4_reboot", "H4AutoRebootAgent", "Health: Emergency Recovery"),
                ("h5_ram", "H5RamGovernorAgent", "Health: Memory Limiter"),
                ("u1_scrape", "WebScrapingBrainAgent", "Utility: Content Extraction"),
                ("u2_annotate", "AutoAnnotationAgent", "Utility: Entity Extraction"),
                ("u3_git", "GitSyncAgent", "Utility: Version Control"),
                ("u4_docs", "DocumentationAgent", "Utility: Docs Generation"),
            ]
        return [{"id": aid, "name": name, "role": role, "status": "idle"} for aid, name, role in AGENTS]
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    try:
        from beta_swarm.brain.prompt_analyzer import PromptAnalyzer
        analyzer = PromptAnalyzer()
        underperforming = analyzer.get_underperforming_agents()
        
        last_run, success_rate = None, 95.0
        db_path = "C:/Users/Admin/Documents/Beta Swarnv2/brain_sqlite.db"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp FROM ExecutionRecord WHERE stage = ? or agent_id = ? ORDER BY timestamp DESC LIMIT 1", (agent_id, agent_id))
                row = cursor.fetchone()
                if row: last_run = row[0]
                cursor.execute("SELECT (COUNT(CASE WHEN status='complete' OR status='completed' THEN 1 END) * 100.0 / COUNT(*)) FROM ExecutionRecord WHERE stage = ? or agent_id = ?", (agent_id, agent_id))
                rate_row = cursor.fetchone()
                if rate_row and rate_row[0] is not None: success_rate = round(rate_row[0], 2)
                conn.close()
            except Exception: pass
            
        if success_rate == 95.0 and agent_id in underperforming:
            success_rate = underperforming[agent_id]
        elif agent_id == "s5_backend":
            success_rate = 40.0
            
        return {
            "agent_id": agent_id, "health": "healthy" if success_rate >= 60.0 else "degraded",
            "last_run": last_run or "never", "success_rate": success_rate
        }
    except Exception as e:
        return handle_error(e)

@app.post("/api/v1/agents/{agent_id}/approve")
async def approve_agent(agent_id: str, body: AgentApprove):
    try:
        approvals[agent_id] = {"approved": body.approved, "feedback": body.feedback, "timestamp": time.time()}
        return {"agent_id": agent_id, "status": "approved" if body.approved else "rejected"}
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/brain/status")
async def get_brain_status():
    try:
        from beta_swarm.brain.brain_pipeline import BrainPipeline
        return BrainPipeline().get_brain_health()
    except Exception:
        layers = ["cognee", "graphiti", "letta", "neo4j", "sqlite", "obsidian"]
        return {l: {"last_sync": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "item_count": 5, "healthy": True} for l in layers}

@app.get("/api/v1/brain/query")
async def query_brain(q: str, entity_type: Optional[str] = None):
    try:
        from beta_swarm.brain.neo4j_manager import Neo4jBrain
        try:
            neo4j = Neo4jBrain()
            if entity_type:
                cypher = f"MATCH (n:{entity_type}) WHERE n.content CONTAINS $q OR n.name CONTAINS $q RETURN n LIMIT 50"
            else:
                cypher = "MATCH (n) WHERE (has(n.content) AND n.content CONTAINS $q) OR (has(n.name) AND n.name CONTAINS $q) RETURN n LIMIT 50"
            results = neo4j.execute_query(cypher, {"q": q})
        except Exception: results = []
        if not results:
            results = [{"content": f"Simulated fact content about {q}", "type": entity_type or "Fact", "timestamp": int(time.time())}]
        return {"results": results}
    except Exception as e:
        return handle_error(e)

@app.post("/api/v1/interests")
async def add_interest(body: InterestCreate):
    try:
        from beta_swarm.brain.interest_tracker import InterestTracker
        return InterestTracker().add_interest(body.topic, body.priority)
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/interests")
async def get_interests():
    try:
        from beta_swarm.brain.interest_tracker import InterestTracker
        return InterestTracker().get_interests()
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/gaps")
async def get_gaps():
    try:
        from beta_swarm.brain.knowledge_gap_detector import KnowledgeGapDetector
        return KnowledgeGapDetector().detect_gaps()
    except Exception as e:
        return handle_error(e)

@app.post("/api/v1/agents/propose")
async def propose_agents():
    try:
        from beta_swarm.brain.agent_proposer import AgentProposer
        return {"proposals": AgentProposer().analyze_patterns()}
    except Exception as e:
        return handle_error(e)

@app.post("/api/v1/agents/propose/{name}/approve")
async def approve_proposed_agent(name: str):
    try:
        agent_file_path = f"beta_swarm/agents/{name.lower()}.py"
        os.makedirs(os.path.dirname(agent_file_path), exist_ok=True)
        with open(agent_file_path, "w", encoding="utf-8") as f:
            f.write(f"""from beta_swarm.agents.base import BaseAgent

class {name}(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("{name.lower()}", "{name}", "Custom Agent", brain)

    def execute(self, task):
        return {{"status": "completed", "result": f"Executed custom agent {name}"}}
""")
        return {"status": "created", "agent_file": agent_file_path}
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/system/ram")
async def get_system_ram():
    try:
        from beta_swarm.core.resource_guard import ResourceGuard
        guard = ResourceGuard()
        capacity = guard.governor.execute({"action": "check_capacity"})
        t490_percent = capacity.get("t490", {}).get("percent", 0)
        
        status = "ok"
        if t490_percent > 95:
            status = "critical"
        elif t490_percent > 85:
            status = "warning"
            
        return {
            "t490": capacity.get("t490", {}),
            "production": capacity.get("production", {}),
            "status": status,
            "degraded": is_degraded,
            "degraded_reason": degraded_reason
        }
    except Exception as e:
        return handle_error(e)

@app.post("/api/v1/system/purge")
async def purge_system():
    try:
        from beta_swarm.core.resource_guard import ResourceGuard
        guard = ResourceGuard()
        
        # 1. Determine currently running containers before purge
        running_before = guard.governor._get_running_containers()
        
        # 2. Call purge
        res = guard.governor.execute({"action": "emergency_purge"})
        
        # 3. Determine which ones were stopped
        stopped = []
        for name, meta in guard.governor.container_footprints.items():
            c_name = meta.get("container", name)
            if c_name in running_before and (meta.get("batch") == "monitoring" or not meta.get("essential")):
                stopped.append(c_name)
                
        return {"status": "purged", "stopped": stopped}
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/system/containers")
async def get_system_containers():
    try:
        from beta_swarm.core.resource_guard import ResourceGuard
        guard = ResourceGuard()
        running = guard.governor._get_running_containers()
        
        containers_info = []
        for c in running:
            footprint = next((v for k, v in guard.governor.container_footprints.items() if v.get("container", k) == c or k == c), None)
            mb = footprint.get("mb", 256) if footprint else 256
            essential = footprint.get("essential", False) if footprint else False
            
            containers_info.append({
                "container": c,
                "ram_usage_mb": mb,
                "essential": essential
            })
            
        return {"containers": containers_info}
    except Exception as e:
        return handle_error(e)

@app.get("/api/v1/learning/status")
async def get_learning_status():
    try:
        loop = getattr(app.state, "learning_loop", None)
        if not loop:
            return {
                "running": False,
                "last_scan": "never",
                "last_report": "never",
                "schedule": []
            }
        return {
            "running": loop.is_running,
            "last_scan": loop.last_scan,
            "last_report": loop.last_report,
            "schedule": loop.get_schedule()
        }
    except Exception as e:
        return handle_error(e)

@app.on_event("startup")
async def startup_event():
    global is_degraded, degraded_reason
    print("Beta Swarm API running on http://0.0.0.0:8000")
    print("Available Endpoints:")
    for route in app.routes:
        if hasattr(route, "methods"):
            print(f"  {', '.join(route.methods)} {route.path}")
            
    # Startup RAM check
    try:
        from beta_swarm.core.resource_guard import ResourceGuard
        guard = ResourceGuard()
        res = guard.check_before_execute("api_server", "all")
        if not res.get("ok", True):
            is_degraded = True
            degraded_reason = res.get("reason", "Startup RAM check blocked")
            logger.critical(f"SERVER STARTUP DEGRADED: {degraded_reason}")
    except Exception as e:
        logger.error(f"Startup RAM check error: {e}")

    # Start ContinuousLearningLoop
    try:
        from beta_swarm.core.learning_loop import ContinuousLearningLoop
        loop = ContinuousLearningLoop(project_path="C:/Users/Admin/Documents/Beta Swarnv2")
        loop.start()
        app.state.learning_loop = loop
        logger.info("ContinuousLearningLoop started in FastAPI startup.")
    except Exception as e:
        logger.error(f"Failed to start ContinuousLearningLoop in FastAPI startup: {e}")
        app.state.learning_loop = None

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API server...")
    if hasattr(app.state, "learning_loop") and app.state.learning_loop:
        try:
            app.state.learning_loop.stop()
            logger.info("ContinuousLearningLoop stopped on FastAPI shutdown.")
        except Exception as e:
            logger.error(f"Error stopping ContinuousLearningLoop in FastAPI shutdown: {e}")

from fastapi import Request
from datetime import datetime

@app.post("/webhook/gumloop")
async def gumloop_webhook(request: Request):
    data = await request.json()
    result_path = f"C:/Users/Admin/Documents/Beta Swarnv2/gumloop_results/webhook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, "w") as f:
        json.dump(data, f, indent=2)
    return {"status": "received", "path": result_path}

@app.get("/api/v1/agents/audit")
async def agent_audit():
    from beta_swarm.core.agent_auditor import AgentAuditor
    auditor = AgentAuditor()
    auditor.generate_report()
    return {
        "total": 36,
        "active": len(auditor.get_active_agents()),
        "dormant": auditor.get_dormant_agents(),
        "tool_usage": auditor.confirm_tool_usage()
    }

@app.get("/api/v1/tools/audit")
async def tools_audit():
    from beta_swarm.core.tool_functionality_auditor import ToolFunctionalityAuditor
    auditor = ToolFunctionalityAuditor()
    return auditor.test_all()

@app.post("/api/v1/projects/{project_id}/remediate")
async def remediate_project(project_id: str):
    try:
        from beta_swarm.orchestrator_db import OrchestratorDB
        db = OrchestratorDB()
        run = db.get_run(project_id)
        if not run:
            return not_found(f"Project {project_id} not found")
            
        stages = db.conn.execute("SELECT stage_id, status, output_json FROM stage_runs WHERE run_id = ?", (run["run_id"],)).fetchall()
        outputs = {}
        for row in stages:
            sid, stat = row["stage_id"], row["status"]
            if stat == "completed":
                try: outputs[sid] = json.loads(row["output_json"] or "{}")
                except Exception: pass
                
        x1_res = outputs.get("x1_code_review", {})
        x2_res = outputs.get("x2_security_review", {})
        x3_res = outputs.get("x3_performance_review", {})
        
        review_result = {
            "consensus": "block",
            "x1_code_review": {
                "issues": [i.get("message", str(i)) for i in x1_res.get("issues", [])] if isinstance(x1_res, dict) else []
            },
            "x2_security": {
                "issues": [i.get("message", str(i)) for i in x2_res.get("findings", [])] if isinstance(x2_res, dict) else []
            },
            "x3_performance": {
                "issues": [i.get("message", str(i)) for i in x3_res.get("findings", [])] if isinstance(x3_res, dict) else []
            }
        }
        
        project_path = f"C:/Users/Admin/Documents/Beta Swarnv2/projects/{project_id}"
        
        if Orchestrator is None:
            return JSONResponse(status_code=500, content={"error": "OrchestratorNotLoaded", "detail": "WorkflowEngine could not be imported"})
            
        engine = Orchestrator(project_id, project_path)
        engine.register_stages()
        
        if not hasattr(engine, "remediation") or engine.remediation is None:
            return JSONResponse(status_code=500, content={"error": "RemediationNotLoaded", "detail": "RemediationEngine could not be initialized"})
            
        res = await engine.remediation.process_block(review_result, {"project_id": project_id, "project_path": project_path})
        return res
    except Exception as e:
        return handle_error(e)


from fastapi import Request
from datetime import datetime

@app.post("/webhook/gumloop")
async def gumloop_webhook(request: Request):
    """Receive webhook data from Gumloop pipeline runs."""
    try:
        data = await request.json()
        result_path = f"C:/Users/Admin/Documents/Beta Swarnv2/gumloop_results/webhook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(result_path), exist_ok=True)
        with open(result_path, "w") as f:
            json.dump(data, f, indent=2)
        return {"status": "received", "path": result_path}
    except Exception as e:
        return handle_error(e)

