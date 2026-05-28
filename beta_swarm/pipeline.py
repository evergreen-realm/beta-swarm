"""
Beta Swarm — run_pipeline() orchestrator wrapper.
Wraps the WorkflowEngine to provide a clean one-call interface.
Logs every stage to the shared PHASE_HANDOVER.md and MessageBus.
"""
import os, json, logging, time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── Stage registry ────────────────────────────────────────────────────── #
_STAGE_MAP = {
    "s1_ideation":        ("beta_swarm.agents.stage.s1_ideation",        "S1IdeationAgent"),
    "s2_research":        ("beta_swarm.agents.stage.s2_research",         "S2ResearchAgent"),
    "s3_prd":             ("beta_swarm.agents.stage.s3_prd",              "S3PRDAgent"),
    "s4_architecture":    ("beta_swarm.agents.stage.s4_architecture",     "S4ArchitectureAgent"),
    "s5_backend":         ("beta_swarm.agents.stage.s5_backend",          "S5BackendAgent"),
    "s6_api":             ("beta_swarm.agents.stage.s6_api",              "S6APIAgent"),
    "s7_frontend":        ("beta_swarm.agents.stage.s7_frontend",         "S7FrontendAgent"),
    "s8_testing":         ("beta_swarm.agents.stage.s8_testing",          "S8TestingAgent"),
    "s9_containerization":("beta_swarm.agents.stage.s9_containerization", "S9ContainerizationAgent"),
    "s10_cicd":           ("beta_swarm.agents.stage.s10_cicd",            "S10CICDAgent"),
    "s11_docs":           ("beta_swarm.agents.stage.s11_documentation",   "S11DocumentationAgent"),
    "s12_monitoring":     ("beta_swarm.agents.stage.s12_monitoring",      "S12MonitoringAgent"),
    "s13_design":         ("beta_swarm.agents.stage.s13_design",          "S13DesignAgent"),
    "x1_code_review":     ("beta_swarm.agents.review.x1_code_review",     "X1CodeReviewAgent"),
    "x2_security_review": ("beta_swarm.agents.review.x2_security_review", "X2SecurityReviewAgent"),
    "x3_performance_review": ("beta_swarm.agents.review.x3_performance_review", "X3PerformanceReviewAgent"),
    "x4_review_board":    ("beta_swarm.agents.review.x4_review_board",    "X4ReviewBoardAgent"),
}

_PIPELINE_STAGES = [
    "s1_ideation", "s2_research", "s3_prd", "s4_architecture",
    "s5_backend", "s6_api", "s7_frontend", "s8_testing",
    "s9_containerization", "s10_cicd", "s11_docs", "s12_monitoring",
    "s13_design", "x1_code_review", "x2_security_review",
    "x3_performance_review", "x4_review_board"
]


def run_pipeline(
    task: Dict[str, Any],
    start_stage: str = "s1_ideation",
    end_stage: Optional[str] = None,
    brain=None
) -> Dict[str, Any]:
    """
    Run the Beta Swarm pipeline from start_stage to end_stage (inclusive).

    Args:
        task: Initial task dict (must contain 'project_id', 'idea'/'concept', etc.)
        start_stage: Stage to begin from (default: s1_ideation)
        end_stage: Optional stop stage (inclusive). None = run all.
        brain: Optional brain instance shared across agents.

    Returns:
        Final accumulated task dict with all stage outputs.
    """
    project_id = task.get("project_id", f"project_{int(time.time())}")
    task["project_id"] = project_id
    task.setdefault("project_path", f"./projects/{project_id}")
    os.makedirs(task["project_path"], exist_ok=True)

    # Determine stages to run
    try:
        start_idx = _PIPELINE_STAGES.index(start_stage)
    except ValueError:
        logger.warning(f"[Pipeline] Unknown start_stage '{start_stage}' — starting from s1")
        start_idx = 0

    if end_stage:
        try:
            end_idx = _PIPELINE_STAGES.index(end_stage)
        except ValueError:
            end_idx = len(_PIPELINE_STAGES) - 1
    else:
        end_idx = len(_PIPELINE_STAGES) - 1

    stages_to_run = _PIPELINE_STAGES[start_idx:end_idx + 1]

    logger.info(f"[Pipeline] Starting project={project_id} stages={stages_to_run}")
    _write_handover(project_id, f"Pipeline started. Stages: {stages_to_run}")

    # Message bus
    bus = None
    try:
        from beta_swarm.core.message_bus import MessageBus
        bus = MessageBus.get_instance()
        bus.publish("pipeline.start", {"project_id": project_id, "stages": stages_to_run}, sender="orchestrator")
    except Exception:
        pass

    context = dict(task)
    results_log = {}

    for stage_id in stages_to_run:
        t0 = time.time()
        logger.info(f"[Pipeline] ▶ {stage_id}")
        _write_handover(project_id, f"Starting stage: {stage_id}")

        try:
            agent = _load_agent(stage_id, brain)
            result = agent.execute(context)
        except Exception as e:
            logger.error(f"[Pipeline] ✗ {stage_id} FAILED: {e}")
            _write_handover(project_id, f"FAILED {stage_id}: {e}")
            result = {"status": "error", "error": str(e)}

        elapsed = round(time.time() - t0, 2)
        result["_elapsed_s"] = elapsed
        context[stage_id] = result
        results_log[stage_id] = {
            "status": result.get("status", "unknown"),
            "elapsed_s": elapsed,
            "next_stage": result.get("next_stage", "")
        }

        _write_handover(project_id,
            f"Completed {stage_id} in {elapsed}s. Status={result.get('status')}. "
            f"Next={result.get('next_stage', 'none')}")

        if bus:
            try:
                bus.publish(f"stage.complete.{stage_id}", {
                    "project_id": project_id, "stage": stage_id,
                    "status": result.get("status"), "elapsed_s": elapsed
                }, sender="orchestrator")
            except Exception:
                pass

        if result.get("status") == "error" and task.get("fail_fast", False):
            logger.error(f"[Pipeline] Fail-fast triggered at {stage_id}")
            break

    # Final summary
    summary = {
        "project_id": project_id,
        "project_path": task["project_path"],
        "stages_run": stages_to_run,
        "results": results_log,
        "context": context
    }

    summary_path = os.path.join(task["project_path"], "pipeline_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in summary.items() if k != "context"}, f, indent=2)

    _write_handover(project_id, f"Pipeline complete. Summary: {summary_path}")
    logger.info(f"[Pipeline] ✓ Done. Summary saved: {summary_path}")

    return summary


def _load_agent(stage_id: str, brain=None):
    """Dynamically import and instantiate the agent for a stage."""
    if stage_id not in _STAGE_MAP:
        raise ValueError(f"Unknown stage: {stage_id}")
    mod_path, cls_name = _STAGE_MAP[stage_id]
    import importlib
    mod = importlib.import_module(mod_path)
    cls = getattr(mod, cls_name)
    try:
        return cls(brain=brain)
    except TypeError:
        return cls()


def _write_handover(project_id: str, message: str):
    """Append a timestamped line to the project's PHASE_HANDOVER.md."""
    try:
        handover_path = f"./projects/{project_id}/PHASE_HANDOVER.md"
        os.makedirs(os.path.dirname(handover_path), exist_ok=True)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(handover_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception as e:
        logger.debug(f"[Pipeline] handover write failed (non-fatal): {e}")
