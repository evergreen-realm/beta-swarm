from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any
import requests

class H2ModelHealthAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("h2_model", "Model Health", "Health: LLM Status", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        lmstudio_url = task.get("lmstudio_url", "http://localhost:1234/v1/models")
        model_name = task.get("model_name", "")

        try:
            resp = requests.get(lmstudio_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                target = next((m for m in models if model_name in m.get("id", "")), None)
                status = "loaded" if target else "not_loaded"
                latency_ms = resp.elapsed.total_seconds() * 1000
            else:
                status = "unreachable"
                latency_ms = 0
        except Exception as e:
            status = f"error: {e}"
            latency_ms = 0

        if self.brain:
            self.brain.store_fact(self.agent_id, f"Model {model_name}: {status}", "health")

        return {"status": "complete", "model_status": status, "latency_ms": latency_ms}
