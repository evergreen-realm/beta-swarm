"""Beta Swarm Pipeline Orchestrator — Sequential Execution (S1-S13)."""

import time
import logging
import importlib
from typing import Dict, Any, List
from beta_swarm.brain.kuzudb_manager import KuzuBrain
from beta_swarm.sentry.bugsink_client import bugsink

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SwarmPipeline:
    def __init__(self):
        self.brain = KuzuBrain()
            
        self.stages = [
            ("s1_ideation", "beta_swarm.agents.stage.s1_ideation.S1IdeationAgent"),
            ("s2_research", "beta_swarm.agents.stage.s2_research.S2ResearchAgent"),
            ("s3_prd", "beta_swarm.agents.stage.s3_prd.S3PRDAgent"),
            ("s4_architecture", "beta_swarm.agents.stage.s4_architecture.S4ArchitectureAgent"),
            ("s5_backend", "beta_swarm.agents.stage.s5_backend.S5BackendAgent"),
            ("s6_api", "beta_swarm.agents.stage.s6_api.S6APIAgent"),
            ("s7_frontend", "beta_swarm.agents.stage.s7_frontend.S7FrontendAgent"),
            ("s8_testing", "beta_swarm.agents.stage.s8_testing.S8TestingAgent"),
            ("s9_deployment", "beta_swarm.agents.stage.s9_deployment.S9DeploymentAgent"),
            ("s10_monitoring", "beta_swarm.agents.stage.s10_monitoring.S10MonitoringAgent"),
            ("s11_docs", "beta_swarm.agents.stage.s11_documentation.S11DocumentationAgent"),
            ("s12_maintenance", "beta_swarm.agents.stage.s12_maintenance.S12MaintenanceAgent"),
            ("s13_design", "beta_swarm.agents.stage.s13_design.S13DesignAgent"),
        ]

    def _load_agent(self, class_path: str):
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def run(self, initial_input: str, project_name: str) -> Dict[str, Any]:
        context = {"project_name": project_name, "last_output": initial_input}
        results = []
        
        logger.info(f"Starting pipeline for project: {project_name}")
        
        for stage_id, class_path in self.stages:
            start_time = time.time()
            try:
                logger.info(f"--- Executing Stage: {stage_id} ---")
                
                # Dynamic Loading
                AgentClass = self._load_agent(class_path)
                agent = AgentClass(brain=self.brain)
                
                # Execution
                task_payload = {"input": context["last_output"], **context}
                output = agent.execute(task=task_payload)
                
                # Track Results
                duration = time.time() - start_time
                results.append({
                    "stage": stage_id,
                    "status": "complete",
                    "duration": round(duration, 2)
                })
                
                # Update Context for next stage
                context["last_output"] = output
                context[f"{stage_id}_output"] = output
                
                # Persist to SQLite securely
                import uuid
                try:
                    conn = self.brain._get_conn()
                    with conn:
                        conn.execute(
                            "INSERT INTO ExecutionRecord (id, stage, project, status, duration, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (str(uuid.uuid4()), stage_id, project_name, "complete", float(duration), time.time())
                        )
                except Exception as db_err:
                    logger.warning(f"Failed to write ExecutionRecord: {db_err}")
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Stage {stage_id} failed: {e}")
                bugsink.capture_exception(e, context={"stage": stage_id, "project": project_name})
                results.append({
                    "stage": stage_id,
                    "status": "failed",
                    "error": str(e),
                    "duration": round(duration, 2)
                })
                break # Halt on failure
                
        return {"project": project_name, "stages": results}

if __name__ == "__main__":
    pipeline = SwarmPipeline()
    summary = pipeline.run("Build a Flask todo API", "FlaskTodoProject")
    print("\n--- Pipeline Summary ---")
    for r in summary["stages"]:
        print(f"{r['stage']}: {r['status']} ({r['duration']}s)")
