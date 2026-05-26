import os
import asyncio
from beta_swarm.adapters.aider import AiderAdapter
from beta_swarm.adapters.levelcode import LevelCodeAdapter
from beta_swarm.adapters.evo_map import EvoMapAdapter
from beta_swarm.adapters.hermes import HermesAdapter
from beta_swarm.adapters.opencode import OpenCodeAdapter
from beta_swarm.adapters.goose import GooseAdapter
from beta_swarm.brain.hybrid_brain import HybridBrain
from beta_swarm.brain.graphiti_integration import GraphitiBrain
import importlib
import json
import logging
import traceback
from collections import deque
from typing import Any, Dict, Optional

from beta_swarm.orchestrator_state import Stage
from beta_swarm.orchestrator_db import OrchestratorDB

try:
    from beta_swarm.tools.api_stack.router import APIRouter
except ImportError:
    from beta_swarm.tools.api_stack.api_router import APIRouter
from beta_swarm.orchestration.crewai_backend import CrewAIBackend

class CheckpointManager:
    """Manages pipeline state persistence for long-horizon task handling."""
    
    def __init__(self, checkpoint_file: str = "pipeline_checkpoint.json"):
        self.file = checkpoint_file

    def save(self, stage_id: str, context: Dict[str, Any]):
        """Persist the current pipeline context to disk."""
        try:
            import time
            data = {
                "last_stage": stage_id,
                "timestamp": time.time(),
                "context_keys": list(context.keys())
            }
            with open(self.file, "w") as f:
                json.dump(data, f)
            logging.info(f"Checkpoint saved at {stage_id}")
        except Exception as e:
            logging.error(f"Failed to save checkpoint: {e}")

    def load(self) -> Dict[str, Any]:
        """Load the last saved checkpoint."""
        if os.path.exists(self.file):
            with open(self.file, "r") as f:
                return json.load(f)
        return {}


logger = logging.getLogger(__name__)

# Registry mapping agent_class names to module paths
AGENT_MODULE_MAP: Dict[str, str] = {
    "S1IdeationAgent": "beta_swarm.agents.stage.s1_ideation",
    "S2ResearchAgent": "beta_swarm.agents.stage.s2_research",
    "S3PRDAgent": "beta_swarm.agents.stage.s3_prd",
    "S4ArchitectureAgent": "beta_swarm.agents.stage.s4_architecture",
    "S5BackendAgent": "beta_swarm.agents.stage.s5_backend",
    "S6APIAgent": "beta_swarm.agents.stage.s6_api",
    "S7FrontendAgent": "beta_swarm.agents.stage.s7_frontend",
    "S8TestingAgent": "beta_swarm.agents.stage.s8_testing",
    "S9DeploymentAgent": "beta_swarm.agents.stage.s9_deployment",
    "S10MonitoringAgent": "beta_swarm.agents.stage.s10_monitoring",
    "S11DocumentationAgent": "beta_swarm.agents.stage.s11_documentation",
    "S12MaintenanceAgent": "beta_swarm.agents.stage.s12_maintenance",
    "S13DesignAgent": "beta_swarm.agents.stage.s13_design",
    "X1CodeReviewAgent": "beta_swarm.agents.review.x1_code_review",
    "X2SecurityReviewAgent": "beta_swarm.agents.review.x2_security_review",
    "X3PerformanceReviewAgent": "beta_swarm.agents.review.x3_performance_review",
    "X4ReviewBoardAgent": "beta_swarm.agents.review.x4_review_board",
    "B1LocalBrainAgent": "beta_swarm.agents.brain.b1_local_brain",
    "B2GlobalBrainAgent": "beta_swarm.agents.brain.b2_global_brain",
    "B3EvolverAgent": "beta_swarm.agents.brain.b3_evolver",
    "B4CodeIntelAgent": "beta_swarm.agents.brain.b4_code_intel",
    "G1HealthMonitorAgent": "beta_swarm.agents.growth.g1_health_monitor",
    "G2BusinessDomainAgent": "beta_swarm.agents.growth.g2_business_domain",
    "G3ReflectionAgent": "beta_swarm.agents.growth.g3_reflection",
    "G4CloudResearchAgent": "beta_swarm.agents.growth.g4_research_cloud",
    "SentryLayerAgent": "beta_swarm.agents.sentry.sentry_layer",
    "B5ObsidianAgent": "beta_swarm.agents.brain.b5_obsidian",
    "H1ResourceMonitorAgent": "beta_swarm.agents.health.h1_resource_monitor",
    "H2ModelHealthAgent": "beta_swarm.agents.health.h2_model_health",
    "H3ServiceHealthAgent": "beta_swarm.agents.health.h3_service_health",
    "H4AutoRebootAgent": "beta_swarm.agents.health.h4_auto_reboot",
    "H5RAMGovernorAgent": "beta_swarm.agents.health.h5_ram_governor",
    "U1WebScrapingAgent": "beta_swarm.agents.utility.web_scraping_brain",
    "U2AutoAnnotationAgent": "beta_swarm.agents.utility.auto_annotation",
    "U3GitSyncAgent": "beta_swarm.agents.utility.git_sync",
    "U4DocumentationAgent": "beta_swarm.agents.utility.documentation",
}


class WorkflowEngine:
    def __init__(self, project_id: str, project_path: str, brain=None):
        from beta_swarm.core.resource_guard import ResourceGuard
        self.resource_guard = ResourceGuard()
        self.project_id = project_id
        self.project_path = project_path
        self.brain = brain
        try:
            self.api_router = APIRouter()
        except Exception:
            self.api_router = None
        try:
            self.crew_backend = CrewAIBackend(project_id, self.api_router, self.brain)
        except Exception as e:
            logger.error(f"Failed to initialize CrewAIBackend: {e}")
            self.crew_backend = None
        self.adapters = {
            "aider": AiderAdapter(),
            "levelcode": LevelCodeAdapter(),
            "evomap": EvoMapAdapter(),
            "hermes": HermesAdapter(),
            "opencode": OpenCodeAdapter(),
            "goose": GooseAdapter(),
        }
        self.graphiti = GraphitiBrain(
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "password")
        )
        self.db = OrchestratorDB()
        self.stages: Dict[str, Stage] = {}
        self.results: Dict[str, Any] = {}
        self.run_id: Optional[str] = None
        try:
            from beta_swarm.brain.brain_pipeline import BrainPipeline
            self.brain_pipeline = BrainPipeline(project_path=self.project_path)
        except Exception as e:
            logger.warning(f"Failed to initialize BrainPipeline: {e}")
            self.brain_pipeline = None
        try:
            from beta_swarm.core.learning_loop import ContinuousLearningLoop
            self.learning_loop = ContinuousLearningLoop(project_path=self.project_path)
            self.learning_loop.start()
        except Exception as e:
            logger.warning(f"Failed to start ContinuousLearningLoop: {e}")
            self.learning_loop = None
        try:
            from beta_swarm.core.remediation_engine import RemediationEngine
            self.remediation = RemediationEngine(orchestrator=self)
        except Exception as e:
            logger.warning(f"Failed to initialize RemediationEngine: {e}")
            self.remediation = None
            
    def shutdown(self):
        """Cleanup and shutdown background resources."""
        if hasattr(self, 'learning_loop') and self.learning_loop:
            try:
                self.learning_loop.stop()
                logger.info("ContinuousLearningLoop stopped in Orchestrator.")
            except Exception as e:
                logger.error(f"Error stopping ContinuousLearningLoop: {e}")

    def register_stages(self):
        self.stages = {
            "s1_ideation":      Stage(id="s1_ideation",      agent_class="S1IdeationAgent",      dependencies=[],                    review_gates=[]),
            "s2_research":      Stage(id="s2_research",      agent_class="S2ResearchAgent",      dependencies=["s1_ideation"],      review_gates=[]),
            "s3_prd":           Stage(id="s3_prd",           agent_class="S3PRDAgent",           dependencies=["s2_research"],      review_gates=[]),
            "s4_architecture":  Stage(id="s4_architecture",  agent_class="S4ArchitectureAgent",  dependencies=["s3_prd"],           review_gates=[]),
            "s5_backend":       Stage(id="s5_backend",       agent_class="S5BackendAgent",       dependencies=["s4_architecture"],  review_gates=["x1_code_review", "x2_security_review", "x3_performance_review"]),
            "s6_api":           Stage(id="s6_api",           agent_class="S6APIAgent",           dependencies=["s5_backend"],      review_gates=[]),
            "s7_frontend":      Stage(id="s7_frontend",      agent_class="S7FrontendAgent",      dependencies=["s6_api"],          review_gates=[]),
            "s8_testing":       Stage(id="s8_testing",       agent_class="S8TestingAgent",       dependencies=["s7_frontend"],     review_gates=[]),
            "s9_deployment":    Stage(id="s9_deployment",    agent_class="S9DeploymentAgent",    dependencies=["s8_testing"],      review_gates=["x4_review_board"]),
            "s10_monitoring":   Stage(id="s10_monitoring",   agent_class="S10MonitoringAgent",   dependencies=["s9_deployment"],    review_gates=[]),
            "s11_documentation":Stage(id="s11_documentation",agent_class="S11DocumentationAgent",dependencies=["s10_monitoring"],   review_gates=[]),
            "s12_maintenance":  Stage(id="s12_maintenance",  agent_class="S12MaintenanceAgent",  dependencies=["s11_documentation"], review_gates=[]),
            "s13_design":       Stage(id="s13_design",       agent_class="S13DesignAgent",       dependencies=["s12_maintenance"],  review_gates=[]),
            "x1_code_review":   Stage(id="x1_code_review",   agent_class="X1CodeReviewAgent",    dependencies=["s5_backend"],      review_gates=[]),
            "x2_security_review":Stage(id="x2_security_review",agent_class="X2SecurityReviewAgent",dependencies=["s5_backend"],      review_gates=[]),
            "x3_performance_review":Stage(id="x3_performance_review",agent_class="X3PerformanceReviewAgent",dependencies=["s5_backend"], review_gates=[]),
            "x4_review_board":  Stage(id="x4_review_board",   agent_class="X4ReviewBoardAgent",    dependencies=["x1_code_review", "x2_security_review", "x3_performance_review"], review_gates=[]),
        }

    def _run_brain_hooks(self, stage_id: str, stage_result: Any):
        if not hasattr(self, 'graphiti') or self.graphiti is None:
            return
        if not isinstance(stage_result, dict):
            logger.warning(f"Brain hook received non-dict result for {stage_id}: {type(stage_result)}")
            return
            
        if stage_id == "s3_prd":
            # Extract concept from output or results
            output = stage_result.get("output", {})
            concept = ""
            if isinstance(output, dict):
                concept = output.get("concept", "")
            
            patterns = self.graphiti.search(str(concept), group_ids=[self.project_id])
            stage_result["patterns"] = patterns
        elif stage_id == "s5_backend":
            self.graphiti.add_episode(
                content=f"Backend generated: {stage_result.get('output', {}).get('path', '')}",
                source="s5_backend",
                source_description="Backend code generation",
                episode_type="code"
            )
        elif stage_id == "s13_design":
            self.graphiti.add_episode(
                content=f"Project learnings for {self.project_id}",
                source="b3_evolver",
                source_description="Post-project evolution",
                episode_type="pattern"
            )
    # Public entry point
    # ------------------------------------------------------------------

    async def execute(self, project_input: dict) -> dict:
        """Create or resume a workflow run, execute the full DAG, return results."""
        existing = self.db.get_run(self.project_id)
        if existing:
            self.run_id = existing["run_id"]
            logger.info("Resuming run %s for project %s", self.run_id, self.project_id)
        else:
            self.run_id = self.db.create_run(self.project_id, project_input)
            logger.info("Created run %s for project %s", self.run_id, self.project_id)

        self.results = {"project_id": self.project_id, "run_id": self.run_id, "stages": {}}
        import time
        start_time = time.time()
        try:
            await self._execute_dag(project_input)
        finally:
            if self.brain_pipeline:
                try:
                    total_duration = time.time() - start_time
                    stages_completed = [
                        sid for sid, res in self.results.get("stages", {}).items()
                        if res.get("status") == "completed"
                    ]
                    x4_stage = self.results.get("stages", {}).get("x4_review_board", {})
                    x4_output = x4_stage.get("output", {}) if isinstance(x4_stage, dict) else {}
                    x4_verdict = x4_output.get("verdict", {}) if isinstance(x4_output, dict) else {}
                    review_score = x4_verdict.get("votes", "0/0")

                    summary_content = {
                        "project_id": self.project_id,
                        "tier": project_input.get("tier", "unknown"),
                        "stages_completed": stages_completed,
                        "total_duration": total_duration,
                        "final_status": self.results.get("status", "unknown"),
                        "review_score": review_score
                    }

                    from beta_swarm.brain.brain_pipeline import Artifact
                    summary_artifact = Artifact.from_dict({
                        "artifact_type": "research",
                        "project_id": self.project_id,
                        "content": json.dumps(summary_content, indent=2),
                        "source_agent": "orchestrator",
                        "metadata": {
                            "status": self.results.get("status", "unknown"),
                            "stage": "project_summary",
                            "duration_seconds": total_duration,
                            "project_tier": project_input.get("tier", "unknown")
                        }
                    })
                    self.brain_pipeline.ingest(summary_artifact)
                    logger.info("Ingested project summary artifact into brain.")
                except Exception as summary_exc:
                    logger.error(f"Failed to ingest project summary artifact: {summary_exc}", exc_info=True)
        return self.results

    # ------------------------------------------------------------------
    # DAG execution via topological sort
    # ------------------------------------------------------------------

    async def _execute_dag(self, project_input: dict):
        """Topologically sort stages and execute them in dependency order."""
        order = self._topological_sort()
        context = dict(project_input)

        for stage_id in order:
            # Skip stages already completed in a previous (resumed) run
            if self.db.get_stage_status(self.run_id, stage_id) == "completed":
                logger.info("Stage %s already completed, skipping", stage_id)
                continue

            # Brain hooks: pre-stage
            await self._run_brain_hooks_before(stage_id, context)

            logger.info("Executing stage %s", stage_id)
            result = await self._run_stage(stage_id, context)
            self.results["stages"][stage_id] = result

            if result.get("status") == "completed":
                # Feed successful output into context for downstream stages
                context[stage_id] = result.get("output", {})
                # Brain hooks: post-stage
                await self._run_brain_hooks_after(stage_id, context, result)
                
                # --- Remediation Hook ---
                if stage_id == "x4_review_board" and getattr(self, "remediation", None):
                    verdict = result.get("output", {}).get("verdict", {}) if isinstance(result.get("output"), dict) else {}
                    decision = verdict.get("decision", "FAIL") if isinstance(verdict, dict) else "FAIL"
                    if decision == "FAIL":
                        logger.warning("X4 Review Board voted FAIL. Activating RemediationEngine...")
                        x1_res = context.get("x1_code_review", {})
                        x2_res = context.get("x2_security_review", {})
                        x3_res = context.get("x3_performance_review", {})
                        
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
                        
                        remedy_res = await self.remediation.process_block(review_result, context)
                        
                        if remedy_res.get("status") == "resolved":
                            logger.info("Remediation succeeded! Overriding review board consensus to PASS.")
                            new_verdict = {
                                "consensus": True,
                                "decision": "PASS_AFTER_DEBATE",
                                "votes": "3/3",
                                "reason": "Remediation applied successfully",
                                "summary": {"critical_count": 0, "error_count": 0, "warning_count": 0, "total_issues": 0}
                            }
                            if not isinstance(result.get("output"), dict):
                                result["output"] = {}
                            result["output"]["verdict"] = new_verdict
                            context["x4_review_board"] = result["output"]
                            self.checkpoint(stage_id, "completed", output=result["output"], error=None)
                        else:
                            logger.error("Remediation failed to resolve blocks. Aborting pipeline.")
                            self.results["status"] = "failed"
                            self.results["failed_stage"] = stage_id
                            return
                
                # Check if RAM is still healthy between stages
                try:
                    capacity = self.resource_guard.governor.execute({"action": "check_capacity"})
                    t490_percent = capacity.get("t490", {}).get("percent", 0)
                    t490_free = capacity.get("t490", {}).get("free_mb", 0)
                    logger.info(f"RAM after stage {stage_id}: {t490_free} MB free ({t490_percent}%)")
                    
                    if hasattr(self, "peak_ram_percent"):
                        self.peak_ram_percent = max(self.peak_ram_percent, t490_percent)
                    
                    if t490_percent > 85:
                        logger.warning(f"RAM threshold breached between stages ({t490_percent}% > 85%). Triggering emergency purge of non-essential containers.")
                        self.resource_guard.governor.execute({"action": "emergency_purge"})
                except Exception as e:
                    logger.error(f"Error checking RAM after stage {stage_id}: {e}")
                    
            elif result.get("status") == "blocked":
                logger.warning("Stage %s execution was blocked by ResourceGuard", stage_id)
                self.results["status"] = "blocked"
                self.results["blocked_stage"] = stage_id
                return
            else:
                logger.error("Stage %s failed, aborting pipeline", stage_id)
                self.results["status"] = "failed"
                self.results["failed_stage"] = stage_id
                return

        self.results["status"] = "completed"

    def _topological_sort(self) -> list:
        """Kahn's algorithm – returns stage IDs in dependency-safe order."""
        in_degree = {sid: len(s.dependencies) for sid, s in self.stages.items()}
        queue = deque(sid for sid, deg in in_degree.items() if deg == 0)
        order = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for sid, stage in self.stages.items():
                if current in stage.dependencies:
                    in_degree[sid] -= 1
                    if in_degree[sid] == 0:
                        queue.append(sid)

        if len(order) != len(self.stages):
            raise RuntimeError("Cycle detected in stage dependencies")
        return order

    # ------------------------------------------------------------------
    # Single-stage runner with retries
    # ------------------------------------------------------------------

    async def _run_stage(self, stage_id: str, context: dict) -> dict:
        """Instantiate the agent for *stage_id* and run it with retries."""
        stage = self.stages[stage_id]
        
        # Determine the stage code: "S1", "S2", "S3", etc. from the stage_id
        stage_parts = stage_id.split("_")
        stage_code = stage_parts[0].upper() if stage_parts else "ALL"
        
        # Check with ResourceGuard
        guard_result = self.resource_guard.check_before_execute(stage_id, stage_code)
        if not guard_result.get("ok", True):
            reason = guard_result.get("reason", "Unknown RAM block")
            logger.warning(f"Stage {stage_id} execution blocked by ResourceGuard: {reason}")
            return {"status": "blocked", "reason": reason}
            
        if "warning" in guard_result:
            warning = guard_result["warning"]
            logger.warning(f"ResourceGuard warning for stage {stage_id}: {warning}")
            context["resource_warning"] = warning

        self.checkpoint(stage_id, "running", output=None, error=None)

        last_error = None
        for attempt in range(stage.retries):
            try:
                logger.info("Stage %s attempt %d/%d", stage_id, attempt + 1, stage.retries)
                agent = self._instantiate_agent(stage.agent_class)
                agent.project_id = self.project_id
                if hasattr(agent, "brain"):
                    agent.brain = self.brain

                # Check if agent has a crashed session to resume
                resume_info = agent.check_resume(context.get("project_id", self.project_id))
                if resume_info.get("can_resume"):
                    # Inject prior context into task
                    context["_resumed_from_identity"] = resume_info
                    agent.start_session(context.get("project_id", self.project_id), resume_info.get("last_task", f"Executing stage {stage_id}"))
                else:
                    agent.start_session(context.get("project_id", self.project_id), f"Executing stage {stage_id}")

                # Build the task payload - flatten context for agent convenience
                task = {
                    "project_id": self.project_id,
                    "project_path": self.project_path,
                    "stage_id": stage_id,
                    "attempt": attempt + 1,
                    **context  # This spreads all previous stage results into the task root
                }

                # Execute with timeout
                output = await asyncio.wait_for(
                    self._call_agent(agent, task),
                    timeout=stage.timeout,
                )

                # Run review gates (x1, x2, x3 in parallel)
                gate_result = await self._run_review_gates(stage_id, output)
                if gate_result.get("status") == "failed":
                    last_error = gate_result.get("error")
                    logger.warning("Review gates failed for %s on attempt %d", stage_id, attempt + 1)
                    continue  # retry the whole stage

                self.checkpoint(stage_id, "completed", output=output, error=None)
                result = {"status": "completed", "output": output, "review": gate_result, "attempts": attempt + 1}
                # Store result in brain
                if self.brain:
                    self.brain.store_memory(
                        agent_id=stage_id,
                        fact=f"Stage {stage_id} completed with status {result.get('status')}",
                        fact_type="stage_completion"
                    )
                
                # B5 Obsidian sync hook
                try:
                    from beta_swarm.agents.brain.b5_obsidian import B5ObsidianAgent
                    b5_agent = B5ObsidianAgent()
                    b5_agent.execute({
                        "project_id": self.project_id,
                        "stage_id": stage_id,
                        "content": f"Stage {stage_id} completed successfully. Attempts: {attempt + 1}"
                    })
                    logger.info("[B5 Obsidian] Synced stage %s to vault.", stage_id)
                except Exception as b5_exc:
                    logger.warning("[B5 Obsidian] Hook failed: %s", b5_exc)

                # Run brain hooks for pattern learning
                self._run_brain_hooks(stage_id, result)
                
                # Use adapters for tool-specific stages
                if stage_id == "s5_backend" and "aider" in self.adapters:
                    try:
                        aider_adapter = self.adapters["aider"]
                        if aider_adapter.check_installed():
                            logger.info("Aider is installed. Calling Aider to check/refactor backend code...")
                            polish_prompt = "Verify all files for syntax and imports. Clean up any unused code."
                            aider_files = [os.path.join(self.project_path, f) for f in output.get("backend_info", {}).get("generated_files", []) if f.endswith(".py")]
                            if aider_files:
                                aider_adapter.code(polish_prompt, aider_files)
                    except Exception as aider_exc:
                        logger.warning("Aider post-processing failed: %s", aider_exc)
                
                result = self._ingest_stage_safe(stage_id, result, context)
                if result.get("status") in ["complete", "completed"]:
                    agent.complete_session()
                return result

            except asyncio.TimeoutError:
                last_error = {"type": "TimeoutError", "message": f"Stage {stage_id} timed out after {stage.timeout}s"}
                logger.warning("Stage %s timed out on attempt %d", stage_id, attempt + 1)
            except Exception as exc:
                last_error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
                logger.warning("Stage %s failed on attempt %d: %s", stage_id, attempt + 1, exc)
                try:
                    from beta_swarm.core.identity_manager import IdentityManager
                    im = IdentityManager()
                    im.mark_crashed(stage_id, self.project_id, str(exc))
                except Exception as crash_exc:
                    logger.warning("Failed to mark identity as crashed: %s", crash_exc)

        # All retries exhausted
        self.checkpoint(stage_id, "failed", output=None, error=last_error)
        result = {"status": "failed", "error": last_error, "attempts": stage.retries}
        result = self._ingest_stage_safe(stage_id, result, context)
        return result

    def _ingest_artifact(self, stage_id: str, result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert agent output to Artifact and ingest into brain."""
        if not self.brain_pipeline:
            return {}

        # a. Map stage_id to artifact_type
        mapping = {
            "s1_ideation": "prd",
            "s2_research": "research",
            "s3_prd": "prd",
            "s4_architecture": "architecture",
            "s5_backend": "code",
            "s6_api": "code",
            "s7_frontend": "code",
            "s8_testing": "review",
            "s9_deployment": "deployment",
            "s10_monitoring": "research",
            "s11_docs": "research",
            "s12_maintenance": "research",
            "s13_design": "design",
            "x1_code_review": "review",
            "x2_security_review": "review",
            "x3_performance_review": "review",
            "x4_review_board": "review",
            "b1_local_brain": "research",
            "b2_global_brain": "research",
            "b3_evolver": "research",
            "b4_code_intel": "research",
            "b5_obsidian": "research",
            "g1_health_monitor": "research",
            "g2_business_domain": "research",
            "g3_reflection": "research",
            "g4_research_cloud": "research"
        }
        artifact_type = mapping.get(stage_id, "research")

        # b. Build artifact content from result
        if stage_id == "x4_review_board":
            # Ingest the final review artifact with all review scores
            # Content should include: passes, total, scores from X1/X2/X3
            verdict = result.get("output", {}).get("verdict", {}) if isinstance(result, dict) else {}
            decision = verdict.get("decision", "unknown")
            votes = verdict.get("votes", "0/0")
            
            x1_res = context.get("x1_code_review", {})
            x2_res = context.get("x2_security_review", {})
            x3_res = context.get("x3_performance_review", {})
            
            summary_info = {
                "decision": decision,
                "votes": votes,
                "x1_code_review": {
                    "passed": x1_res.get("passed", False) if isinstance(x1_res, dict) else False,
                    "issues_count": len(x1_res.get("issues", [])) if isinstance(x1_res, dict) else 0
                },
                "x2_security_review": {
                    "passed": x2_res.get("passed", False) if isinstance(x2_res, dict) else False,
                    "issues_count": len(x2_res.get("findings", [])) if isinstance(x2_res, dict) else 0
                },
                "x3_performance_review": {
                    "passed": x3_res.get("passed", False) if isinstance(x3_res, dict) else False,
                    "issues_count": len(x3_res.get("findings", [])) if isinstance(x3_res, dict) else 0
                }
            }
            content = json.dumps(summary_info, indent=2)
        elif isinstance(result, dict) and "result" in result:
            content = str(result["result"])
        else:
            content = str(result)

        # Truncate content
        if len(content) > 5000:
            content = content[:5000]

        # c. Build metadata
        metadata = {
            "status": result.get("status", "unknown") if isinstance(result, dict) else "unknown",
            "stage": stage_id,
            "duration_seconds": result.get("duration", 0) if isinstance(result, dict) else 0,
            "errors": result.get("errors", []) if isinstance(result, dict) else [],
            "project_tier": context.get("tier", "unknown"),
            "user_id": context.get("user_id", "default")
        }

        # d. Create Artifact
        from beta_swarm.brain.brain_pipeline import Artifact
        artifact = Artifact.from_dict({
            "artifact_type": artifact_type,
            "project_id": context.get("project_id", "unknown") if context.get("project_id") else self.project_id,
            "content": content,
            "source_agent": stage_id,
            "metadata": metadata
        })

        # e. Call self.brain_pipeline.ingest(artifact)
        pipeline_result = self.brain_pipeline.ingest(artifact)

        # f. Return the pipeline result
        return pipeline_result

    def _ingest_stage_safe(self, stage_id: str, result: dict, context: dict) -> dict:
        if self.brain_pipeline is None:
            logger.info("Brain pipeline unavailable — artifact not ingested")
            return result

        try:
            pipeline_result = self._ingest_artifact(stage_id, result, context)
            
            # Extract layer statuses
            layers = pipeline_result.get("layers", {})
            cognee_status = layers.get("cognee", {}).get("status", "unknown")
            graphiti_status = layers.get("graphiti", {}).get("status", "unknown")
            letta_status = layers.get("letta", {}).get("status", "unknown")
            neo4j_status = layers.get("neo4j", {}).get("status", "unknown")
            obsidian_status = layers.get("obsidian", {}).get("status", "unknown")
            
            logger.info(
                f"Brain ingestion: {stage_id} → "
                f"Cognee:{cognee_status} Graphiti:{graphiti_status} Letta:{letta_status} "
                f"Neo4j:{neo4j_status} Obsidian:{obsidian_status}"
            )
            result["_brain_ingestion"] = pipeline_result
        except Exception as e:
            logger.error(f"Brain ingestion failed for stage {stage_id}: {e}", exc_info=True)
            
        return result

    # ------------------------------------------------------------------
    # Agent helpers
    # ------------------------------------------------------------------

    def _instantiate_agent(self, agent_class_name: str):
        """Dynamically import and instantiate the agent class."""
        module_path = AGENT_MODULE_MAP.get(agent_class_name)
        if not module_path:
            raise ValueError(f"Unknown agent class: {agent_class_name}")
        module = importlib.import_module(module_path)
        cls = getattr(module, agent_class_name)
        return cls()

    @staticmethod
    async def _call_agent(agent, task: dict) -> dict:
        """Call agent.run(); supports both sync and async agents."""
        if asyncio.iscoroutinefunction(getattr(agent, "run", None)):
            return await agent.run(task)
        return agent.run(task)

    # ------------------------------------------------------------------
    # Checkpoint persistence
    # ------------------------------------------------------------------

    def checkpoint(self, stage_id: str, status: str, output=None, error=None):
        """Persist the current stage state to the database."""
        self.db.update_stage(
            run_id=self.run_id,
            stage_id=stage_id,
            status=status,
            output=output,
            error=error,
        )

    # ------------------------------------------------------------------
    # Review gates  (x1, x2, x3 in parallel; g3 auto-fix on failure)
    # ------------------------------------------------------------------

    async def _run_review_gates(self, stage_id: str, stage_output: dict) -> dict:
        """Run x1, x2, x3 review agents in parallel.  On any failure, invoke
        g3_reflection for auto-fix and return the combined result."""
        from beta_swarm.agents.review.x1_code_review import X1CodeReviewAgent
        from beta_swarm.agents.review.x2_security_review import X2SecurityReviewAgent
        from beta_swarm.agents.review.x3_performance_review import X3PerformanceReviewAgent

        stage = self.stages[stage_id]
        if not stage.review_gates:
            return {"status": "skipped"}

        payload = {
            "project_id": self.project_id,
            "project_path": self.project_path,
            "stage_output": stage_output
        }

        x1 = X1CodeReviewAgent()
        x2 = X2SecurityReviewAgent()
        x3 = X3PerformanceReviewAgent()

        async def _safe_review(agent, name: str) -> dict:
            try:
                result = await self._call_agent(agent, payload)
                return {"name": name, "status": "passed", "result": result}
            except Exception as exc:
                logger.warning("Review gate %s failed: %s", name, exc)
                return {"name": name, "status": "failed", "error": str(exc)}

        # Run all three in parallel
        results = await asyncio.gather(
            _safe_review(x1, "x1_code_review"),
            _safe_review(x2, "x2_security_review"),
            _safe_review(x3, "x3_performance_review"),
        )

        failed = [r for r in results if r["status"] == "failed"]

        if failed:
            logger.info("Review gates failed for %s — invoking g3_reflection", stage_id)
            fix_result = await self._invoke_g3_reflection(stage_id, stage_output, failed)
            return {
                "status": "failed" if fix_result.get("status") == "failed" else "auto_fixed",
                "reviews": results,
                "reflection": fix_result,
                "error": {"failed_gates": [f["name"] for f in failed]},
            }

        return {"status": "passed", "reviews": results}

    async def _invoke_g3_reflection(self, stage_id: str, stage_output: dict, failures: list) -> dict:
        """Call g3_reflection agent to attempt auto-fix of review failures."""
        from beta_swarm.agents.growth.g3_reflection import G3ReflectionAgent

        g3 = G3ReflectionAgent()
        task_log = {
            "project_id": self.project_id,
            "project_path": self.project_path,
            "stage_id": stage_id,
            "output_summary": str(stage_output)[:2000],
            "failures": failures,
        }

        try:
            result = await self._call_agent(g3, task_log)
            logger.info("g3_reflection auto-fix result for %s: %s", stage_id, result)
            return {"status": "auto_fixed", "result": result}
        except Exception as exc:
            logger.error("g3_reflection failed for %s: %s", stage_id, exc)
            return {"status": "failed", "error": str(exc)}

    # ------------------------------------------------------------------
    # Brain hooks  (b2 query, b4 index, b3 evolve)
    # ------------------------------------------------------------------

    async def _run_brain_hooks_before(self, stage_id: str, context: dict):
        """Brain hooks that fire *before* a stage executes."""
        if self.brain is None:
            return

        if stage_id == "s3_prd":
            # b2: query knowledge graph for domain context before design
            await self._b2_query(context)

    async def _run_brain_hooks_after(self, stage_id: str, context: dict, result: dict):
        """Brain hooks that fire *after* a stage completes successfully."""
        if self.brain is None:
            return

        if stage_id == "s5_backend":
            # b4: index generated code into knowledge graph
            await self._b4_index(result.get("output", {}))

        if stage_id == "s13_design":
            # b3: evolve the brain with completed project learnings
            await self._b3_evolve(context, result.get("output", {}))

    async def _b2_query(self, context: dict):
        """B2 hook — query Cognee/KuzuDB for relevant domain knowledge."""
        try:
            from beta_swarm.agents.brain.b2_global_brain import B2GlobalBrainAgent
            b2_agent = B2GlobalBrainAgent()
            b2_res = b2_agent.execute(topic=str(context.get("s2", {})))
            logger.info("[b2_query] B2 Global Brain Agent query completed: %s", b2_res)

            from beta_swarm.brain.cognee_client import CogneeClient
            from beta_swarm.brain.kuzu_manager import KuzuBrain

            query_text = json.dumps(context.get("s2", {}), default=str)[:1000]
            logger.info("[b2_query] Querying brain for design-stage context")

            cognee = CogneeClient()
            cognee.add_document(query_text, doc_id=f"{self.project_id}_s2_context")
            cognee.cognify()

            logger.info("[b2_query] Brain context indexed for project %s", self.project_id)
        except Exception as exc:
            logger.warning("[b2_query] Brain hook failed (non-fatal): %s", exc)

    async def _b4_index(self, output: dict):
        """B4 hook — index generated code artifacts into the knowledge graph."""
        try:
            from beta_swarm.agents.brain.b4_code_intel import B4CodeIntelAgent
            b4_agent = B4CodeIntelAgent()
            b4_res = b4_agent.execute(query=str(output))
            logger.info("[b4_intel] B4 Code Intel Agent index completed: %s", b4_res)

            from beta_swarm.brain.cognee_client import CogneeClient
            from beta_swarm.brain.kuzu_manager import KuzuBrain

            code_summary = json.dumps(output, default=str)[:3000]
            logger.info("[b4_index] Indexing code artifacts into brain")

            cognee = CogneeClient()
            cognee.add_document(code_summary, doc_id=f"{self.project_id}_s5_code")
            cognee.cognify()

            kuzu = KuzuBrain()
            kuzu.store_artifact(
                project_id=self.project_id,
                stage="s5_backend",
                data=output,
            )

            logger.info("[b4_index] Code artifacts indexed for project %s", self.project_id)
        except Exception as exc:
            logger.warning("[b4_index] Brain hook failed (non-fatal): %s", exc)

    async def _b3_evolve(self, context: dict, output: dict):
        """B3 hook — evolve the brain with learnings from the completed project."""
        try:
            from beta_swarm.agents.brain.b3_evolver import B3EvolverAgent
            b3_agent = B3EvolverAgent()
            b3_res = b3_agent.execute({"context": context, "output": output})
            logger.info("[b3_evolve] B3 Evolver Agent execution completed: %s", b3_res)

            from beta_swarm.brain.cognee_client import CogneeClient
            from beta_swarm.brain.neo4j_manager import Neo4jBrain

            evolution_payload = json.dumps({
                "project_id": self.project_id,
                "final_output": str(output)[:2000],
                "stage_count": len(self.stages),
            }, default=str)

            logger.info("[b3_evolve] Evolving brain with project learnings")

            cognee = CogneeClient()
            cognee.add_document(evolution_payload, doc_id=f"{self.project_id}_evolution")
            cognee.cognify()

            neo4j = Neo4jBrain()
            neo4j.store_evolution(
                project_id=self.project_id,
                learnings=output,
            )

            logger.info("[b3_evolve] Brain evolved for project %s", self.project_id)
        except Exception as exc:
            logger.warning("[b3_evolve] Brain hook failed (non-fatal): %s", exc)

    def use_crewai(self, agent_ids: list, tasks: list, process: str = "sequential") -> dict:
        """Delegate to CrewAI backend."""
        if not hasattr(self, "crew_backend") or self.crew_backend is None:
            return {"status": "error", "message": "CrewAI backend not initialized."}
        try:
            return self.crew_backend.run_custom_crew(agent_ids, tasks, process)
        except Exception as e:
            logger.error(f"Error in use_crewai: {e}")
            return {"status": "error", "message": str(e)}

    async def run_with_governor(self, project_id: str, tier: str, description: str) -> dict:
        """Wraps the existing execute() but with pre-flight capacity check and RAM logging."""
        capacity = self.resource_guard.governor.execute({"action": "check_capacity"})
        free_mb = capacity.get("t490", {}).get("free_mb", 0)
        logger.info(f"[Pre-flight] RAM check: {free_mb} MB free.")
        if free_mb < 2000:
            err_msg = f"Insufficient RAM for pre-flight check: {free_mb} MB available, 2000 MB required."
            logger.error(err_msg)
            return {"status": "error", "reason": "Insufficient RAM", "free_mb": free_mb}

        self.peak_ram_percent = capacity.get("t490", {}).get("percent", 0)
        self.project_id = project_id
        
        project_input = {
            "idea": description,
            "tier": tier
        }
        
        try:
            results = await self.execute(project_input)
            logger.info(f"Project completed. Peak RAM usage during run: {self.peak_ram_percent}%")
            results["peak_ram_percent"] = self.peak_ram_percent
            return results
        except Exception as e:
            logger.error(f"Execution failed under governor: {e}")
            return {"status": "failed", "error": str(e), "peak_ram_percent": self.peak_ram_percent}

    def get_brain_status(self) -> Dict[str, Any]:
        if self.brain_pipeline:
            return self.brain_pipeline.get_brain_health()
        return {}

def run_project(project_name: str, task_name: str, project_input: dict) -> dict:
    import asyncio
    import os
    engine = WorkflowEngine(project_name, os.path.abspath(project_name))
    engine.register_stages()
    return asyncio.run(engine.execute(project_input))

def resume_project(project_name: str, task_name: str) -> dict:
    import asyncio
    import os
    engine = WorkflowEngine(project_name, os.path.abspath(project_name))
    engine.register_stages()
    return asyncio.run(engine.execute({"idea": "resume"}))

def run_tier3_project(project_name: str, query: str, depth: str = "standard") -> dict:
    """Run a Tier 3 project, optionally using CrewAI collaboration for research and specs."""
    import os
    import asyncio
    engine = WorkflowEngine(project_name, os.path.abspath(project_name))
    engine.register_stages()
    if hasattr(engine, "crew_backend") and engine.crew_backend and getattr(engine.crew_backend, "HAS_CREWAI", False):
        try:
            logger.info("CrewAI detected. Running research crew for Tier 3 project.")
            return engine.crew_backend.run_research_crew(query, depth)
        except Exception as e:
            logger.warning(f"CrewAI research crew execution failed, falling back: {e}")
    return asyncio.run(engine.execute({"idea": query, "depth": depth}))

def run_tier4_project(project_name: str, project_path: str, stack: dict) -> dict:
    """Run a Tier 4 project, optionally using CrewAI collaboration for architecture and coding."""
    import os
    import asyncio
    engine = WorkflowEngine(project_name, project_path)
    engine.register_stages()
    if hasattr(engine, "crew_backend") and engine.crew_backend and getattr(engine.crew_backend, "HAS_CREWAI", False):
        try:
            logger.info("CrewAI detected. Running code crew for Tier 4 project.")
            return engine.crew_backend.run_code_crew(project_path, stack)
        except Exception as e:
            logger.warning(f"CrewAI code crew execution failed, falling back: {e}")
    return asyncio.run(engine.execute({"idea": f"Build code at {project_path} using stack {stack}"}))

