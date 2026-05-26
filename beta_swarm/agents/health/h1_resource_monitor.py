from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any
import psutil
import time

class H1ResourceMonitorAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("h1_resource", "Resource Monitor", "Health: Passive Metrics", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        metrics = {
            "timestamp": time.time(),
            "ram_percent": ram.percent,
            "ram_available_mb": ram.available // (1024 * 1024),
            "cpu_percent": cpu,
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free // (1024 * 1024 * 1024),
            "net_sent_mb": net.bytes_sent // (1024 * 1024),
            "net_recv_mb": net.bytes_recv // (1024 * 1024)
        }

        if self.brain:
            self.brain.store_fact(self.agent_id, f"RAM={ram.percent}%, CPU={cpu}%", "health")

        return {"status": "complete", "metrics": metrics}
