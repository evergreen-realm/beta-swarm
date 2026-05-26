import logging
import psutil
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class G1HealthMonitorAgent(BaseAgent):
    def __init__(self):
        super().__init__("G1", "Health Monitor", "growth")

    def execute(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        logger.info(f"G1: Health check - CPU: {cpu}%, RAM: {ram}%")
        if cpu > 90 or ram > 90:
            self._trigger_reboot()
        return {"status": "complete", "cpu": cpu, "ram": ram}

    def _trigger_reboot(self):
        logger.warning("G1: Critical state! Triggering reboot.")
