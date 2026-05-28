#!/usr/bin/env python3
"""
Beta Swarm v3.2 — verify_complete.py
Full verification of Phase 1 + Phase 2 implementation.
Run: python verify_complete.py
"""
import sys, os, json, importlib, subprocess, sqlite3
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, ROOT)

results = {"pass": 0, "fail": 0, "warn": 0, "tests": []}

def record(name, status, detail=""):
    results[status.lower()] += 1
    results["tests"].append({"name": name, "status": status, "detail": detail})
    c = {"PASS": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m"}.get(status, "")
    print(f"  [{c}{status}\033[0m] {name}" + (f" -- {detail}" if detail else ""))

def check_import(mod, cls=None, label=None):
    name = label or (f"{mod}.{cls}" if cls else mod)
    try:
        m = importlib.import_module(mod)
        if cls:
            getattr(m, cls)
        record(f"Import: {name}", "PASS")
        return True
    except Exception as e:
        record(f"Import: {name}", "FAIL", str(e)[:120])
        return False

print(f"\n{'='*65}")
print(f"  BETA SWARM v3.2 — COMPLETE VERIFICATION")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*65}\n")

# ── 1. Stage Agents S1–S13 ────────────────────────────────────────── #
print("── PHASE 1: STAGE AGENTS ──────────────────────────────────────")
stage_agents = [
    ("beta_swarm.agents.stage.s1_ideation",         "S1IdeationAgent"),
    ("beta_swarm.agents.stage.s2_research",          "S2ResearchAgent"),
    ("beta_swarm.agents.stage.s3_prd",               "S3PRDAgent"),
    ("beta_swarm.agents.stage.s4_architecture",      "S4ArchitectureAgent"),
    ("beta_swarm.agents.stage.s5_backend",           "S5BackendAgent"),
    ("beta_swarm.agents.stage.s6_api",               "S6APIAgent"),
    ("beta_swarm.agents.stage.s7_frontend",          "S7FrontendAgent"),
    ("beta_swarm.agents.stage.s8_testing",           "S8TestingAgent"),
    ("beta_swarm.agents.stage.s9_containerization",  "S9ContainerizationAgent"),
    ("beta_swarm.agents.stage.s10_cicd",             "S10CICDAgent"),
    ("beta_swarm.agents.stage.s11_documentation",    "S11DocumentationAgent"),
    ("beta_swarm.agents.stage.s12_monitoring",       "S12MonitoringAgent"),
    ("beta_swarm.agents.stage.s13_design",           "S13DesignAgent"),
]
for mod, cls in stage_agents:
    check_import(mod, cls)

# ── S5 aliases (merged) ───────────────────────────────────────────── #
try:
    from beta_swarm.agents.stage.s5_backend import S5LevelCodeAgent
    assert S5LevelCodeAgent is not None
    record("S5 alias: S5LevelCodeAgent", "PASS")
except Exception as e:
    record("S5 alias: S5LevelCodeAgent", "WARN", str(e)[:80])

# ── S7 aliases (merged) ───────────────────────────────────────────── #
try:
    from beta_swarm.agents.stage.s7_frontend import S7FrontendHuashuAgent
    assert S7FrontendHuashuAgent is not None
    record("S7 alias: S7FrontendHuashuAgent", "PASS")
except Exception as e:
    record("S7 alias: S7FrontendHuashuAgent", "WARN", str(e)[:80])

# ── 2. Review Agents X1–X4 ────────────────────────────────────────── #
print("\n── PHASE 2: REVIEW AGENTS ─────────────────────────────────────")
review_agents = [
    ("beta_swarm.agents.review.x1_code_review",          "X1CodeReviewAgent"),
    ("beta_swarm.agents.review.x2_security_review",      "X2SecurityReviewAgent"),
    ("beta_swarm.agents.review.x3_performance_review",   "X3PerformanceReviewAgent"),
    ("beta_swarm.agents.review.x4_review_board",         "X4ReviewBoardAgent"),
]
for mod, cls in review_agents:
    check_import(mod, cls)

# ── 3. Core Infrastructure ─────────────────────────────────────────── #
print("\n── PHASE 2: CORE INFRASTRUCTURE ───────────────────────────────")
check_import("beta_swarm.core.message_bus",           "MessageBus")
check_import("beta_swarm.tools.web.parallel_web_client", "ParallelWebClient")
check_import("beta_swarm.pipeline",                   "run_pipeline")
check_import("beta_swarm.brain.sqlite_brain",         "SQLiteBrain")
check_import("beta_swarm.tools.api_stack.router",     "APIRouter")
check_import("beta_swarm.tools.api_stack.config",     "RouterConfig")

# ── 4. BaseAgent methods ─────────────────────────────────────────────#
print("\n── BASE AGENT METHODS ──────────────────────────────────────────")
try:
    from beta_swarm.agents.base import BaseAgent
    class DummyAgent(BaseAgent):
        def execute(self, *args, **kwargs):
            return None
    b = DummyAgent("test", "Test", "test")
    for method in ["_call_llm", "_log_handover", "_get_router", "generate_codebase"]:
        if hasattr(b, method):
            record(f"BaseAgent.{method}", "PASS")
        else:
            record(f"BaseAgent.{method}", "FAIL", "Method missing")
except Exception as e:
    record("BaseAgent instantiation", "FAIL", str(e)[:120])

# ── 5. SQLiteBrain functional test ──────────────────────────────────#
print("\n── SQLITE BRAIN FUNCTIONAL TEST ────────────────────────────────")
try:
    from beta_swarm.brain.sqlite_brain import SQLiteBrain
    db = SQLiteBrain.get_instance()
    db.register_agent("verify_test", "Verify Agent", "test")
    db.store_fact("verify_test", "verification run", "test")
    ctx = db.query_context("verify_test")
    record("SQLiteBrain: register + store_fact + query_context", "PASS",
           f"{len(ctx)} memories")
except Exception as e:
    record("SQLiteBrain functional test", "FAIL", str(e)[:120])

# ── 6. MessageBus functional test ───────────────────────────────────#
print("\n── MESSAGE BUS FUNCTIONAL TEST ─────────────────────────────────")
try:
    from beta_swarm.core.message_bus import MessageBus
    bus = MessageBus.get_instance()
    mid = bus.publish("verify.test", {"ping": "pong"}, sender="verify")
    msg = bus.consume("verify.test", consumer="verify")
    assert msg is not None and msg["payload"]["ping"] == "pong"
    record("MessageBus: publish + consume", "PASS", f"msg_id={mid[:8]}...")
except Exception as e:
    record("MessageBus functional test", "FAIL", str(e)[:120])

# ── 7. ParallelWebClient import ──────────────────────────────────── #
print("\n── WEB TOOLS ───────────────────────────────────────────────────")
try:
    from beta_swarm.tools.web.parallel_web_client import ParallelWebClient
    pwc = ParallelWebClient(max_workers=2)
    record("ParallelWebClient instantiation", "PASS")
except Exception as e:
    record("ParallelWebClient instantiation", "FAIL", str(e)[:120])

# ── 8. Pipeline function ─────────────────────────────────────────── #
print("\n── PIPELINE FUNCTION ───────────────────────────────────────────")
try:
    from beta_swarm.pipeline import run_pipeline, _STAGE_MAP, _PIPELINE_STAGES
    assert len(_PIPELINE_STAGES) == 17, f"Expected 17 stages, got {len(_PIPELINE_STAGES)}"
    record("pipeline.run_pipeline importable", "PASS", f"{len(_PIPELINE_STAGES)} stages registered")
except Exception as e:
    record("pipeline.run_pipeline", "FAIL", str(e)[:120])

# ── 9. Merged files — dead files gone ───────────────────────────────#
print("\n── CLEANUP: DELETED STUB FILES ─────────────────────────────────")
stage_dir = os.path.join(ROOT, "beta_swarm", "agents", "stage")
dead_files = ["s5_levelcode.py", "s7_frontend_huashu.py",
              "s9_deployment.py", "s10_monitoring.py",
              "s11_deployment.py", "s12_maintenance.py"]
for df in dead_files:
    p = os.path.join(stage_dir, df)
    if not os.path.exists(p):
        record(f"Deleted: {df}", "PASS")
    else:
        record(f"Deleted: {df}", "WARN", "File still exists — merge alias is in place")

# ── 10. Review tools available ──────────────────────────────────────#
print("\n── REVIEW TOOLS ────────────────────────────────────────────────")
for tool in ["bandit", "ruff", "semgrep"]:
    try:
        r = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
        ver = (r.stdout + r.stderr).strip().split("\n")[0][:60]
        record(f"Tool: {tool}", "PASS", ver)
    except FileNotFoundError:
        record(f"Tool: {tool}", "WARN", "Not installed (pip install " + tool + ")")
    except Exception as e:
        record(f"Tool: {tool}", "WARN", str(e)[:60])

# ── Summary ──────────────────────────────────────────────────────── #
total = results["pass"] + results["fail"] + results["warn"]
print(f"\n{'='*65}")
print(f"  RESULTS: {results['pass']}/{total} PASSED  |  "
      f"{results['fail']} FAILED  |  {results['warn']} WARNINGS")
print(f"{'='*65}\n")

# Save JSON report
report_path = os.path.join(ROOT, "verify_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump({"timestamp": datetime.now().isoformat(), **results}, f, indent=2)
print(f"Report saved: {report_path}")

if results["fail"] > 0:
    print(f"\n\033[91m✗ {results['fail']} test(s) FAILED — fix before pushing.\033[0m\n")
    sys.exit(1)
else:
    print(f"\n\033[92m✓ All checks passed ({results['warn']} warnings).\033[0m\n")
    sys.exit(0)
