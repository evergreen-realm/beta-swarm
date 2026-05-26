import subprocess
import requests
import logging
from typing import Dict, Any
from beta_swarm.brain.kuzu_manager import KuzuBrain

logger = logging.getLogger(__name__)

class HealthOrchestrator:
    """Verifies the status of all core swarm services."""
    
    def __init__(self):
        import os
        port = int(os.environ.get("PORT", 8999))
        self.checks = {
            "docker": self._check_docker,
            "ollama": lambda: self._check_url("http://localhost:11434/api/tags"),
            "dashboard": lambda: self._check_url(f"http://localhost:{port}"),
            "kuzudb": self._check_kuzu,
            "prometheus": lambda: self._check_url("http://localhost:9090/-/healthy"),
            "grafana": lambda: self._check_url("http://localhost:3000/api/health"),
        }

    def _check_url(self, url: str) -> bool:
        try:
            return requests.get(url, timeout=2).status_code == 200
        except Exception:
            return False

    def _check_docker(self) -> bool:
        try:
            return subprocess.run(["docker", "ps"], capture_output=True, check=False).returncode == 0
        except Exception:
            return False

    def _check_kuzu(self) -> bool:
        try:
            brain = KuzuBrain(read_only=True)
            # Simple check if brain is responsive
            brain.query("MATCH (a) RETURN count(a) LIMIT 1")
            return True
        except Exception:
            return False

    def run_all_checks(self) -> Dict[str, bool]:
        """Execute all health checks and return results."""
        results = {}
        for name, check in self.checks.items():
            results[name] = check()
        return results

    def auto_repair(self):
        """Attempt to restart failed services."""
        logger.info("Attempting auto-repair...")
        subprocess.run(["docker", "compose", "up", "-d"], capture_output=True)
