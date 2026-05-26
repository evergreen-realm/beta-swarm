"""Uptime Kuma Advanced Monitor — programmatic integration with Uptime Kuma API."""
import os
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class UptimeKumaClient:
    """Client for Uptime Kuma monitoring platform."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("UPTIME_KUMA_URL", "http://localhost:3001")
        self.token = None

    def login(self, username: str = "admin", password: str = "beta-swarm-admin") -> bool:
        """Authenticate with Uptime Kuma."""
        try:
            resp = requests.post(f"{self.base_url}/api/login", json={
                "username": username, "password": password
            }, timeout=5)
            if resp.status_code == 200:
                self.token = resp.json().get("token")
                return True
        except Exception as e:
            logger.warning(f"Uptime Kuma login failed: {e}")
        return False

    def _headers(self) -> Dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def add_monitor(self, name: str, url: str, monitor_type: str = "http",
                    interval: int = 60) -> Dict[str, Any]:
        """Add a new monitor."""
        try:
            resp = requests.post(f"{self.base_url}/api/monitors", headers=self._headers(),
                json={"name": name, "url": url, "type": monitor_type, "interval": interval},
                timeout=10)
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to add monitor {name}: {e}")
            return {"error": str(e)}

    def get_monitors(self) -> List[Dict]:
        """List all monitors."""
        try:
            resp = requests.get(f"{self.base_url}/api/monitors", headers=self._headers(), timeout=5)
            return resp.json() if resp.status_code == 200 else []
        except Exception as e:
            logger.error(f"Failed to get monitors: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        """Get overall status page data."""
        try:
            resp = requests.get(f"{self.base_url}/api/status-page/default", timeout=5)
            return resp.json() if resp.status_code == 200 else {"status": "unreachable"}
        except Exception:
            return {"status": "unreachable"}

    def health_check(self) -> Dict[str, Any]:
        """Check if Uptime Kuma is reachable."""
        try:
            resp = requests.get(self.base_url, timeout=3)
            return {"reachable": resp.status_code == 200, "status_code": resp.status_code}
        except Exception:
            return {"reachable": False}


def setup_default_monitors():
    """Set up default monitors for Beta Swarm services."""
    client = UptimeKumaClient()
    if not client.login():
        logger.warning("Could not login to Uptime Kuma. Skipping monitor setup.")
        return

    monitors = [
        ("Beta Swarm API", "http://localhost:8000/api/v1/health"),
        ("Neo4j Browser", "http://localhost:7474"),
        ("Grafana", "http://localhost:3000"),
        ("Prometheus", "http://localhost:9090"),
        ("GitNexus MCP", "http://localhost:8765/health"),
    ]
    for name, url in monitors:
        client.add_monitor(name, url)
        logger.info(f"Added monitor: {name}")
