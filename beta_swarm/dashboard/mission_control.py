import logging
import subprocess
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MissionControl:
    """Interface for controlling the swarm pipeline and individual agents."""
    
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator

    async def abort_all(self):
        """Kill all running swarm processes."""
        logger.warning("ABORT COMMAND RECEIVED")
        if os.name == 'nt':
            subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/T"], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "beta_swarm"], capture_output=True)
        return {"status": "aborted"}

    async def trigger_deployment(self):
        """Manually trigger the S9 Deployment Agent."""
        logger.info("Triggering S9 Deployment...")
        try:
            from beta_swarm.agents.stage.s9_deployment import S9DeploymentAgent
            agent = S9DeploymentAgent()
            # In a real scenario, we'd pass the actual project context
            # result = agent.execute({"project_path": "./workspace/last_project"})
            return {"status": "triggered", "agent": "S9"}
        except ImportError:
            return {"status": "error", "message": "S9 Agent not found"}

    async def trigger_evolution(self):
        """Manually trigger the Brain Evolution cycle."""
        logger.info("Triggering Brain Evolution...")
        # Hook into B3 logic
        return {"status": "triggered", "hook": "B3"}

    async def run_audit(self):
        """Trigger the GitNexus risk analyzer."""
        logger.info("Triggering Security Audit...")
        return {"status": "triggered", "tool": "GitNexus"}
