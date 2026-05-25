import os
import httpx
import logging
import time
import subprocess
from typing import Dict

logger = logging.getLogger(__name__)

class CogneeClient:
    """Client for Cognee Knowledge Graph Pipeline."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("COGNEE_BASE_URL", "http://localhost:8000")
        self.client = httpx.Client(timeout=30.0)
        
    def health_check(self) -> Dict:
        """Check status of the Cognee service."""
        for path in ["/health", "/docs"]:
            try:
                response = self.client.get(f"{self.base_url}{path}", timeout=3.0)
                if response.status_code == 200:
                    return {"status": "running", "reachable": True, "version": "unknown"}
            except Exception:
                pass
        return {"status": "stopped", "reachable": False, "version": "unknown"}

    def _ensure_service(self) -> bool:
        """Check if service is running, otherwise try starting via Docker."""
        hc = self.health_check()
        if hc["reachable"]:
            return True
            
        logger.warning("Cognee service unreachable. Attempting Docker start...")
        for container_name in ["beta-cognee", "cognee"]:
            try:
                res = subprocess.run(["docker", "start", container_name], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    logger.info(f"Triggered docker start for {container_name}")
                    break
            except Exception as e:
                logger.warning(f"Could not check/run docker start for {container_name}: {e}")
                
        # Wait 10 seconds for service to start up
        time.sleep(10)
        hc = self.health_check()
        return hc["reachable"]

    def add_document(self, content: str, doc_id: str = None) -> dict:
        if not self._ensure_service():
            raise ConnectionError("Cognee not available")
            
        try:
            url = f"{self.base_url}/api/v1/add"
            payload = {"text": content}
            if doc_id:
                payload["id"] = doc_id
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to add document to Cognee: {e}")
            return {"status": "error", "fallback_needed": True, "detail": str(e)}
            
    def cognify(self) -> dict:
        if not self._ensure_service():
            raise ConnectionError("Cognee not available")
            
        try:
            url = f"{self.base_url}/api/v1/cognify"
            response = self.client.post(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to trigger Cognee cognify: {e}")
            return {"status": "error", "fallback_needed": True, "detail": str(e)}

if __name__ == "__main__":
    client = CogneeClient()
    print(client.health_check())

