import os
import json
import time
import importlib
import sys
import logging
import argparse
import inspect
from typing import Dict, Any, List
from beta_swarm.core.monitoring import MetricsTracker, start_metrics_server

# Configure logger for standard output and error
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("orchestrator")

class StageMachine:
    """Conductor for the Beta Swarm pipeline, executing stages sequentially with checkpointing."""
    
    def transition_stage(self, stage: str):
        """Active load management during stage transitions."""
        from beta_swarm.agents.health.h5_ram_governor import H5RamGovernorAgent
        
        logger.info(f"Orchestrator: Transitioning to stage {stage}...")
        governor = H5RamGovernorAgent()
        
        try:
            result = governor.execute({"action": "transition_to_stage", "stage": stage})
            if result.get("status") == "success":
                logger.info(f"Orchestrator: Stage transition to {stage} successful.")
                return True
        except Exception as e:
            logger.error(f"Orchestrator: Stage transition failed: {e}. Triggering emergency purge...")
            governor.execute({"action": "emergency_purge"})
            # Retry once
            try:
                governor.execute({"action": "transition_to_stage", "stage": stage})
                return True
            except:
                logger.critical("Orchestrator: Stage transition failed after retry.")
                return False
        return False
    
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.state = {"project_name": project_name, "history": []}
        self.checkpoint_root = "./checkpoints/orchestrator"
        self.run_id = int(time.time())
        os.makedirs(self.checkpoint_root, exist_ok=True)

    def _get_agent_class(self, stage_name: str):
        """Dynamically imports and returns the agent class for a given stage."""
        if stage_name.startswith("s"):
            package = "beta_swarm.agents.stage"
            module_name = stage_name
        elif stage_name.startswith("x"):
            package = "beta_swarm.agents.review"
            mapping = {
                "x1_review": "x1_code_review",
                "x2_security": "x2_security_review",
                "x3_performance": "x3_performance_review",
                "x4_board": "x4_review_board"
            }
            module_name = mapping.get(stage_name, stage_name)
        else:
            return None

        try:
            module = importlib.import_module(f"{package}.{module_name}")
            # Dynamically find the class that inherits from BaseAgent
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module.__name__:
                    # Simple check: starts with S or X and ends with Agent
                    if (name.startswith("S") or name.startswith("X")) and name.endswith("Agent"):
                        return obj
            return None
        except Exception as e:
            logger.error(f"Error importing {module_name}: {e}")
            return None

    def _save_checkpoint(self, stage_name: str):
        """Writes the current state to a timestamped JSON file."""
        path = os.path.join(self.checkpoint_root, f"{self.run_id}_{stage_name}.json")
        with open(path, "w") as f:
            json.dump(self.state, f, indent=2)
        logger.info(f"Checkpoint saved: {path}")

    def _prepare_kwargs(self, agent, state):
        """Intelligently maps accumulated state to agent execution parameters."""
        sig = inspect.signature(agent.execute)
        kwargs = {}
        for p in sig.parameters:
            if p in state:
                kwargs[p] = state[p]
            # Intelligent aliasing for known stage outputs
            elif p == "text_input" and "input" in state: kwargs[p] = state["input"]
            elif p == "research_summary" and "summary" in state: kwargs[p] = state["summary"]
            elif p in ["task", "context", "state"]: kwargs[p] = state
        return kwargs

    def run(self, config: Dict[str, List[str]], initial_input: str):
        """Executes the pipeline defined in the config."""
        self.state["input"] = initial_input
        
        for stage_name in config.get("stages", []):
            logger.info(f"\n[ORCHESTRATOR] >>> Starting Stage: {stage_name}")
            
            # Active load management transition
            self.transition_stage(stage_name)
            
            AgentClass = self._get_agent_class(stage_name)
            
            if not AgentClass:
                if stage_name == "s7_frontend":
                    # TODO: Implement S7FrontendAgent logic if the class is missing
                    logger.warning(f"Agent class for {stage_name} not found. Skipping.")
                    continue
                logger.error(f"FATAL: Agent class for {stage_name} could not be loaded. Halting.")
                sys.exit(1)

            try:
                agent = AgentClass()
                kwargs = self._prepare_kwargs(agent, self.state)
                
                start_time = time.time()
                result = agent.run(**kwargs)
                duration = time.time() - start_time
                
                if isinstance(result, dict) and result.get("status") == "error":
                    MetricsTracker.record_stage(stage_name, duration, success=False)
                    logger.error(f"Stage {stage_name} returned error status: {result.get('message', 'Unknown error')}")
                    agent.recover()
                    sys.exit(1)
                
                MetricsTracker.record_stage(stage_name, duration, success=True)
                
                # Update global state with stage output
                if isinstance(result, dict):
                    self.state.update(result)
                self.state[stage_name] = result
                self.state["history"].append(stage_name)
                
                self._save_checkpoint(stage_name)
                
            except Exception as e:
                MetricsTracker.record_stage(stage_name, time.time() - start_time, success=False)
                logger.error(f"CRITICAL: Pipeline halted due to error in {stage_name}: {e}")
                if 'agent' in locals():
                    agent.recover()
                sys.exit(1)

        logger.info("[ORCHESTRATOR] Pipeline Execution Complete.")

def main():
    parser = argparse.ArgumentParser(description="Beta Swarm Orchestrator CLI")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--input", required=True, help="Initial prompt or idea")
    parser.add_argument("--metrics-port", type=int, default=8000, help="Port for Prometheus metrics")
    args = parser.parse_args()

    # Start monitoring if requested
    start_metrics_server(args.metrics_port)

    pipeline_config = {
        "stages": [
            "s1_ideation", "s2_research", "s3_prd", "s4_architecture", 
            "s5_backend", "s6_api", "s7_frontend", "s8_testing", 
            "s9_deployment", "x1_review", "x4_board"
        ]
    }
    
    machine = StageMachine(args.project)
    machine.run(pipeline_config, args.input)

if __name__ == "__main__":
    main()
