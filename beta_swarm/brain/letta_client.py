import os
import httpx
import logging
import time
import json
import subprocess
from typing import Dict

logger = logging.getLogger(__name__)

class LettaClient:
    """Client for Letta (MemGPT) Agent Memory Runtime."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("LETTA_BASE_URL", "http://localhost:8283")
        self.client = httpx.Client(timeout=10.0)
        
    def health_check(self) -> Dict:
        """Check status of the Letta service."""
        try:
            response = self.client.get(f"{self.base_url}/api/agents", timeout=3.0)
            if response.status_code == 200:
                agents = response.json().get("agents", [])
                return {"status": "running", "reachable": True, "agents_count": len(agents)}
        except Exception:
            pass
        return {"status": "stopped", "reachable": False, "agents_count": 0}

    def _ensure_service(self) -> bool:
        """Check if service is running, otherwise try starting via Docker."""
        hc = self.health_check()
        if hc["reachable"]:
            return True
            
        logger.warning("Letta service unreachable. Attempting Docker start...")
        for container_name in ["beta-letta", "letta"]:
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

    def create_agent(self, name: str, persona: str, human: str) -> dict:
        if not self._ensure_service():
            raise ConnectionError("Letta not available")
            
        try:
            url = f"{self.base_url}/api/agents"
            payload = {"name": name, "persona": persona, "human": human}
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create Letta agent: {e}")
            return {"status": "error", "detail": str(e)}
            
    def send_message(self, agent_id: str, message: str) -> dict:
        if not self._ensure_service():
            raise ConnectionError("Letta not available")
            
        try:
            url = f"{self.base_url}/api/agents/{agent_id}/messages"
            payload = {"message": message, "role": "user"}
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send message to Letta agent {agent_id}: {e}")
            return {"status": "error", "detail": str(e)}

    def flush_to_neo4j(self) -> Dict:
        """Flush Letta archival memory to Neo4j graph brain."""
        try:
            if not self._ensure_service():
                return {"status": "error", "message": "Letta not running"}
            
            # Get all agents
            resp = self.client.get(f"{self.base_url}/api/agents")
            agents = resp.json().get("agents", [])
            
            from beta_swarm.brain.neo4j_manager import Neo4jBrain
            neo4j = Neo4jBrain()
            flushed = 0
            
            for agent in agents:
                agent_id = agent.get("id")
                # Get agent messages/memory
                try:
                    msg_resp = self.client.get(f"{self.base_url}/api/agents/{agent_id}/messages")
                    messages = msg_resp.json().get("messages", [])
                    
                    for msg in messages:
                        content = msg.get("content", "")[:500]
                        if content:
                            neo4j.store_fact(
                                agent_id=f"letta_{agent_id}",
                                topic="archival_memory",
                                content=content,
                                metadata=json.dumps({"source": "letta_archival", "timestamp": msg.get("created_at")})
                            )
                            flushed += 1
                except Exception as e:
                    logger.debug(f"Failed to flush agent {agent_id} messages: {e}")
                    continue
            
            return {"status": "ok", "flushed": flushed}
        except Exception as e:
            return {"status": "error", "message": str(e)}

