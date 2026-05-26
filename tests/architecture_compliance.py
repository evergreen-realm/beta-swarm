#!/usr/bin/env python3
"""Beta Swarm v3.2 -- Architecture Compliance Audit (Phases 1-2)"""
import sys, os, json, shutil, subprocess, importlib, inspect
sys.path.insert(0, r"C:\Users\Admin\Documents\Beta Swarnv2")

BASE = r"C:\Users\Admin\Documents\Beta Swarnv2"
results = {"agents": [], "tools": [], "docker": [], "summary": {}}

def check(name, status, detail=""):
    s = {"PASS": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m"}.get(status, "")
    print(f"  {name}: [{s}{status}\033[0m] {detail}")
    return {"name": name, "status": status, "detail": detail}

# ═══════════════════════════════════════════════════════════════
# PHASE 1: AGENT WIRING AUDIT
# ═══════════════════════════════════════════════════════════════
print("=" * 65)
print("  PHASE 1: AGENT WIRING AUDIT")
print("=" * 65)

# Load register_all.py registry
try:
    from beta_swarm.agents.register_all import AGENTS
    registered_ids = set(AGENTS.keys()) if isinstance(AGENTS, dict) else set()
except Exception:
    AGENTS = {}
    registered_ids = set()

# Load orchestrator agent map
try:
    from beta_swarm.orchestrator import AGENT_MODULE_MAP
    orch_agents = set(AGENT_MODULE_MAP.keys())
except Exception:
    AGENT_MODULE_MAP = {}
    orch_agents = set()

AGENT_SPEC = {
    # Stage agents
    "s1_ideation":      ("beta_swarm.agents.stage.s1_ideation", "S1IdeationAgent"),
    "s2_research":      ("beta_swarm.agents.stage.s2_research", "S2ResearchAgent"),
    "s3_prd":           ("beta_swarm.agents.stage.s3_prd", "S3PRDAgent"),
    "s4_architecture":  ("beta_swarm.agents.stage.s4_architecture", "S4ArchitectureAgent"),
    "s5_backend":       ("beta_swarm.agents.stage.s5_backend", "S5BackendAgent"),
    "s6_api":           ("beta_swarm.agents.stage.s6_api", "S6APIAgent"),
    "s7_frontend":      ("beta_swarm.agents.stage.s7_frontend", "S7FrontendAgent"),
    "s8_testing":       ("beta_swarm.agents.stage.s8_testing", "S8TestingAgent"),
    "s9_deployment":    ("beta_swarm.agents.stage.s9_deployment", "S9DeploymentAgent"),
    "s10_monitoring":   ("beta_swarm.agents.stage.s10_monitoring", "S10MonitoringAgent"),
    "s11_documentation":("beta_swarm.agents.stage.s11_documentation", "S11DocumentationAgent"),
    "s12_maintenance":  ("beta_swarm.agents.stage.s12_maintenance", "S12MaintenanceAgent"),
    "s13_design":       ("beta_swarm.agents.stage.s13_design", "S13DesignAgent"),
    # Review agents
    "x1_code_review":   ("beta_swarm.agents.review.x1_code_review", "X1CodeReviewAgent"),
    "x2_security_review":("beta_swarm.agents.review.x2_security_review", "X2SecurityReviewAgent"),
    "x3_performance_review":("beta_swarm.agents.review.x3_performance_review", "X3PerformanceReviewAgent"),
    "x4_review_board":  ("beta_swarm.agents.review.x4_review_board", "X4ReviewBoardAgent"),
    # Brain agents
    "b1_local_brain":   ("beta_swarm.agents.brain.b1_local_brain", "B1LocalBrainAgent"),
    "b2_global_brain":  ("beta_swarm.agents.brain.b2_global_brain", "B2GlobalBrainAgent"),
    "b3_evolver":       ("beta_swarm.agents.brain.b3_evolver", "B3EvolverAgent"),
    "b4_code_intel":    ("beta_swarm.agents.brain.b4_code_intel", "B4CodeIntelAgent"),
    "b5_obsidian":      ("beta_swarm.agents.brain.b5_obsidian", "B5ObsidianAgent"),
    # Growth agents
    "g1_health_monitor":("beta_swarm.agents.growth.g1_health_monitor", "G1HealthMonitorAgent"),
    "g2_business_domain":("beta_swarm.agents.growth.g2_business_domain", "G2BusinessDomainAgent"),
    "g3_reflection":    ("beta_swarm.agents.growth.g3_reflection", "G3ReflectionAgent"),
    "g4_research_cloud":("beta_swarm.agents.growth.g4_research_cloud", "G4CloudResearchAgent"),
    # Health agents
    "h1_resource_monitor":("beta_swarm.agents.health.h1_resource_monitor", "H1ResourceMonitorAgent"),
    "h2_model_health":  ("beta_swarm.agents.health.h2_model_health", "H2ModelHealthAgent"),
    "h3_service_health":("beta_swarm.agents.health.h3_service_health", "H3ServiceHealthAgent"),
    "h4_auto_reboot":   ("beta_swarm.agents.health.h4_auto_reboot", "H4AutoRebootAgent"),
    "h5_ram_governor":  ("beta_swarm.agents.health.h5_ram_governor", "H5RAMGovernorAgent"),
    # Utility agents
    "auto_annotation":  ("beta_swarm.agents.utility.auto_annotation", "U2AutoAnnotationAgent"),
    "documentation":    ("beta_swarm.agents.utility.documentation", "U4DocumentationAgent"),
    "git_sync":         ("beta_swarm.agents.utility.git_sync", "U3GitSyncAgent"),
    "web_scraping":     ("beta_swarm.agents.utility.web_scraping_brain", "U1WebScrapingAgent"),
    # Sentry
    "sentry_layer":     ("beta_swarm.agents.sentry.sentry_layer", "SentryLayerAgent"),
}

print(f"\n{'Agent ID':<25} {'FILE':>5} {'REG':>5} {'ORCH':>5} {'EXEC':>5} {'STATUS':>10}")
print("-" * 65)

agent_pass = 0
agent_total = len(AGENT_SPEC)

for agent_id, (mod_path, cls_name) in AGENT_SPEC.items():
    # FILE check
    file_path = os.path.join(BASE, mod_path.replace(".", "/") + ".py")
    file_ok = os.path.exists(file_path)
    
    # REGISTERED check
    reg_ok = agent_id in registered_ids or any(agent_id in str(v) for v in registered_ids)
    
    # ORCHESTRATOR check
    orch_ok = cls_name in orch_agents
    
    # EXECUTE check - does it have a real execute() method?
    exec_ok = False
    try:
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name)
        if hasattr(cls, 'execute'):
            src = inspect.getsource(cls.execute)
            # Check it's not just pass or return {}
            exec_ok = len(src.strip().split('\n')) > 3
    except Exception:
        pass
    
    marks = lambda ok: "Y" if ok else "X"
    status = "ACTIVE" if all([file_ok, exec_ok]) else "DORMANT" if file_ok else "MISSING"
    if status == "ACTIVE":
        agent_pass += 1
    
    print(f"  {agent_id:<23} {marks(file_ok):>5} {marks(reg_ok):>5} {marks(orch_ok):>5} {marks(exec_ok):>5} {status:>10}")
    results["agents"].append({
        "id": agent_id, "class": cls_name, "file": file_ok,
        "registered": reg_ok, "orchestrator": orch_ok, "execute": exec_ok, "status": status
    })

print(f"\n  Agent Summary: {agent_pass}/{agent_total} ACTIVE")

# ═══════════════════════════════════════════════════════════════
# PHASE 2: TOOL FUNCTIONALITY VERIFICATION
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("  PHASE 2: TOOL FUNCTIONALITY VERIFICATION")
print("=" * 65)

# CODING TOOLS
print("\n--- Coding Tools ---")
coding_tools = [
    ("Aider",     "aider",     ["aider", "--version"]),
    ("Goose",     "goose",     ["goose", "--version"]),
    ("OpenCode",  "opencode",  ["opencode", "--version"]),
    ("LevelCode", "levelcode", ["levelcode", "--version"]),
    ("Git",       "git",       ["git", "--version"]),
    ("Docker",    "docker",    ["docker", "--version"]),
]

print(f"\n  {'Tool':<15} {'BINARY':>8} {'ADAPTER':>9} {'USED':>6}")
print("  " + "-" * 45)

for name, binary, cmd in coding_tools:
    bin_ok = shutil.which(binary) is not None
    # Check adapter
    adapter_ok = False
    try:
        if name == "Git":
            adapter_ok = True  # used directly
        elif name == "Docker":
            adapter_ok = True  # used directly
        else:
            mod = importlib.import_module(f"beta_swarm.adapters.{binary if binary != 'levelcode' else 'levelcode'}")
            adapter_ok = True
    except Exception:
        try:
            mod = importlib.import_module(f"beta_swarm.adapters.{name.lower()}")
            adapter_ok = True
        except Exception:
            pass
    
    used_ok = adapter_ok  # if adapter exists, it's wired
    marks_fn = lambda ok: "Y" if ok else "X"
    status = "PASS" if bin_ok else "WARN"
    results["tools"].append({"name": name, "binary": bin_ok, "adapter": adapter_ok, "used": used_ok})
    print(f"  {name:<15} {marks_fn(bin_ok):>8} {marks_fn(adapter_ok):>9} {marks_fn(used_ok):>6}")

# BRAIN TOOLS
print("\n--- Brain Tools ---")
brain_tools = [
    ("Neo4j",    "beta_swarm.brain.neo4j_manager"),
    ("Cognee",   "beta_swarm.brain.cognee_client"),
    ("Letta",    "beta_swarm.brain.letta_client"),
    ("Graphiti", "beta_swarm.brain.graphiti_manager"),
    ("SQLite",   None),
    ("Obsidian", "beta_swarm.brain.obsidian_manager"),
]

for name, mod_path in brain_tools:
    if mod_path:
        try:
            importlib.import_module(mod_path)
            r = check(name, "PASS", "Module loads")
        except Exception as e:
            r = check(name, "FAIL", str(e)[:50])
    else:
        import sqlite3
        try:
            c = sqlite3.connect(os.path.join(BASE, "brain_sqlite.db"))
            t = c.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            r = check(name, "PASS", f"{t} tables")
            c.close()
        except Exception as e:
            r = check(name, "FAIL", str(e)[:50])
    results["tools"].append({"name": name, "status": r["status"]})

# INFRASTRUCTURE FILES
print("\n--- Infrastructure Files ---")
infra_files = [
    ("EXO Mesh",       "beta_swarm/core/exo_mesh.py"),
    ("BitNet Runtime",  "beta_swarm/core/bitnet_runtime.py"),
    ("MergeKit",        "beta_swarm/core/mergekit_manager.py"),
    ("Whisper Pipeline","beta_swarm/voice/whisper_pipeline.py"),
    ("Bugsink Client",  "beta_swarm/sentry/bugsink_client.py"),
    ("Uptime Kuma",     "beta_swarm/monitoring/uptime_kuma_advanced.py"),
    ("OpenClaw",        "beta_swarm/orchestration/openclaw.py"),
    ("ClawGraph",       "beta_swarm/tools/clawgraph.py"),
    ("Huashu Skill",    "beta_swarm/tools/huashu/huashu_skill.py"),
    ("Agency Personas", "beta_swarm/core/agency_personas.py"),
    ("Persistence",     "beta_swarm/core/persistence.py"),
    ("Messaging",       "beta_swarm/core/messaging.py"),
    ("Model Optimizer", "beta_swarm/core/model_optimizer.py"),
    ("Learning Loop",   "beta_swarm/core/learning_loop.py"),
    ("Resource Guard",  "beta_swarm/core/resource_guard.py"),
    ("Remediation",     "beta_swarm/core/remediation_engine.py"),
    ("Identity Manager","beta_swarm/core/identity_manager.py"),
    ("Crash Recovery",  "beta_swarm/core/crash_recovery.py"),
    ("X4 Consensus",    "beta_swarm/core/x4_advanced_consensus.py"),
    ("BrainPipeline",   "beta_swarm/brain/brain_pipeline.py"),
    ("KuzuDB Manager",  "beta_swarm/brain/kuzudb_manager.py"),
    ("Knowledge Gap",   "beta_swarm/brain/knowledge_gap_detector.py"),
    ("Interest Tracker","beta_swarm/brain/interest_tracker.py"),
    ("Prompt Analyzer", "beta_swarm/brain/prompt_analyzer.py"),
]

for name, path in infra_files:
    full = os.path.join(BASE, path)
    exists = os.path.exists(full)
    sz = os.path.getsize(full) if exists else 0
    status = "PASS" if exists and sz > 100 else "WARN" if exists else "FAIL"
    r = check(name, status, f"{sz}B" if exists else "MISSING")
    results["tools"].append({"name": name, "status": r["status"], "size": sz})

# DEPLOY FILES
print("\n--- Deploy Files ---")
deploy_files = [
    "deploy/master-docker-compose.yml",
    "deploy/letta-docker-compose.yml",
    "deploy/cognee-docker-compose.yml",
    "deploy/monitoring-docker-compose.yml",
    "deploy/bugsink-docker-compose.yml",
    "deploy/prometheus.yml",
    "deploy/alertmanager.yml",
    "deploy/traefik/traefik.yml",
    "deploy/master_setup.sh",
]

for path in deploy_files:
    full = os.path.join(BASE, path)
    exists = os.path.exists(full)
    name = os.path.basename(path)
    r = check(name, "PASS" if exists else "FAIL", path)
    results["tools"].append({"name": name, "status": r["status"]})

# ORCHESTRATION FILES
print("\n--- Orchestration Managers ---")
orch_files = [
    ("AiderManager",    "beta_swarm/orchestration/aider_manager.py"),
    ("GooseManager",    "beta_swarm/orchestration/goose_manager.py"),
    ("GooseServer",     "beta_swarm/orchestration/goose_server.py"),
    ("OpenClawManager", "beta_swarm/orchestration/openclaw.py"),
    ("OpenCodeManager", "beta_swarm/orchestration/opencode_manager.py"),
    ("LevelCodeManager","beta_swarm/orchestration/levelcode_manager.py"),
    ("CrewAIBackend",   "beta_swarm/orchestration/crewai_backend.py"),
]

for name, path in orch_files:
    full = os.path.join(BASE, path)
    exists = os.path.exists(full)
    r = check(name, "PASS" if exists else "FAIL", f"{os.path.getsize(full)}B" if exists else "MISSING")
    results["tools"].append({"name": name, "status": r["status"]})

# API SERVER ENDPOINTS
print("\n--- API Server Endpoints ---")
try:
    from beta_swarm.api.server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    endpoints = [
        ("GET",  "/api/v1/agents",       200),
        ("GET",  "/api/v1/health",        200),
        ("POST", "/webhook/gumloop",      200),
    ]
    for method, path, expected in endpoints:
        try:
            if method == "GET":
                resp = client.get(path)
            else:
                resp = client.post(path, json={"test": True})
            status = "PASS" if resp.status_code == expected else "WARN"
            r = check(f"{method} {path}", status, f"HTTP {resp.status_code}")
        except Exception as e:
            r = check(f"{method} {path}", "FAIL", str(e)[:40])
        results["tools"].append({"name": f"{method} {path}", "status": r["status"]})
except Exception as e:
    check("API Server", "FAIL", str(e)[:50])

# FRONTEND FILES
print("\n--- Frontend ---")
frontend_dirs = [
    "frontend",
    "beta_swarm/frontend",
    "static",
    "dashboard",
]
found_frontend = None
for d in frontend_dirs:
    full = os.path.join(BASE, d)
    if os.path.isdir(full):
        found_frontend = full
        files = os.listdir(full)
        check("Frontend Dir", "PASS", f"{d}/ ({len(files)} files)")
        break
if not found_frontend:
    check("Frontend Dir", "WARN", "No frontend directory found")

# OBSIDIAN VAULT
print("\n--- Obsidian Vault ---")
vault = os.path.join(BASE, "obsidian-vault")
if os.path.isdir(vault):
    items = []
    for root, dirs, files in os.walk(vault):
        items.extend(files)
    check("Obsidian Vault", "PASS", f"{len(items)} files")
else:
    check("Obsidian Vault", "WARN", "No vault directory")

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("  PHASE 1-2 SUMMARY")
print("=" * 65)

active_agents = sum(1 for a in results["agents"] if a["status"] == "ACTIVE")
dormant_agents = sum(1 for a in results["agents"] if a["status"] == "DORMANT")
missing_agents = sum(1 for a in results["agents"] if a["status"] == "MISSING")
tool_pass = sum(1 for t in results["tools"] if t.get("status") == "PASS")
tool_fail = sum(1 for t in results["tools"] if t.get("status") == "FAIL")
tool_warn = sum(1 for t in results["tools"] if t.get("status") == "WARN")
tool_total = len(results["tools"])

results["summary"] = {
    "agents_active": active_agents,
    "agents_dormant": dormant_agents,
    "agents_missing": missing_agents,
    "agents_total": agent_total,
    "tools_pass": tool_pass,
    "tools_fail": tool_fail,
    "tools_warn": tool_warn,
    "tools_total": tool_total,
}

print(f"""
  Agents:  {active_agents}/{agent_total} ACTIVE, {dormant_agents} DORMANT, {missing_agents} MISSING
  Tools:   {tool_pass} PASS, {tool_warn} WARN, {tool_fail} FAIL (of {tool_total})
""")

if dormant_agents > 0:
    print("  DORMANT AGENTS (file exists but execute() is stub):")
    for a in results["agents"]:
        if a["status"] == "DORMANT":
            print(f"    - {a['id']} ({a['class']})")

if missing_agents > 0:
    print("\n  MISSING AGENTS (file not found):")
    for a in results["agents"]:
        if a["status"] == "MISSING":
            print(f"    - {a['id']} ({a['class']})")

if tool_fail > 0:
    print("\n  FAILED TOOLS:")
    for t in results["tools"]:
        if t.get("status") == "FAIL":
            print(f"    - {t['name']}")

# Save
report_path = os.path.join(BASE, "Architecture-Compliance-Phase1-2.json")
with open(report_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\n  Report saved: {report_path}")
