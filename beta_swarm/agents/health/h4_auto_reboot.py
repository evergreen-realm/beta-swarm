from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any
import psutil
import subprocess
import platform

class H4AutoRebootAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("h4_reboot", "Auto-Reboot Agent", "Health: Emergency Recovery", brain)
        self.warning_threshold = 75.0
        self.critical_threshold = 90.0

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)

        status = "healthy"
        action = "none"

        if ram.percent >= self.critical_threshold or cpu >= self.critical_threshold:
            status = "critical"
            action = self._trigger_reboot()
        elif ram.percent >= self.warning_threshold or cpu >= self.warning_threshold:
            status = "warning"
            action = "alert_raised"

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Reboot check: {status}, action={action}", "health")

        return {"status": "complete", "health_status": status, "action": action, "ram": ram.percent, "cpu": cpu}

    def _trigger_reboot(self) -> str:
        system = platform.system()
        if system == "Linux":
            subprocess.run(["sudo", "reboot"], capture_output=True)
            return "reboot_initiated_linux"
        elif system == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "60"], capture_output=True)
            return "reboot_initiated_windows"
        return "reboot_unsupported_os"
