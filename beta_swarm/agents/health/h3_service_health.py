from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any, List
import requests

class H3ServiceHealthAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("h3_service", "Service Health", "Health: Container Status", brain)
        self.services = {
            "neo4j": {"url": "http://localhost:7474", "check": "status_code"},
            "letta": {"url": "http://localhost:8283/v1/health", "check": "status_code"},
            "cognee": {"url": "http://localhost:8000/health", "check": "status_code"},
            "prometheus": {"url": "http://localhost:9090/-/healthy", "check": "status_code"},
            "grafana": {"url": "http://localhost:3000/api/health", "check": "status_code"}
        }

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        results = []
        for name, cfg in self.services.items():
            try:
                resp = requests.get(cfg["url"], timeout=5)
                healthy = resp.status_code < 400
                results.append({"service": name, "healthy": healthy, "status": resp.status_code})
            except Exception as e:
                results.append({"service": name, "healthy": False, "error": str(e)})

        all_healthy = all(r["healthy"] for r in results)

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Services: {sum(1 for r in results if r['healthy'])}/{len(results)} up", "health")

        return {"status": "complete", "all_healthy": all_healthy, "services": results}
