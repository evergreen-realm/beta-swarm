import os
import httpx
import logging

logger = logging.getLogger(__name__)

class LettaClient:
    """Client for Letta (MemGPT) Agent Memory Runtime."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("LETTA_BASE_URL", "http://localhost:8283")
        self.client = httpx.Client(timeout=10.0)
        
    def create_agent(self, name: str, persona: str, human: str) -> dict:
        try:
            url = f"{self.base_url}/api/agents"
            payload = {"name": name, "persona": persona, "human": human}
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create Letta agent: {e}")
            return {}
            
    def send_message(self, agent_id: str, message: str) -> dict:
        try:
            url = f"{self.base_url}/api/agents/{agent_id}/messages"
            payload = {"message": message, "role": "user"}
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send message to Letta agent {agent_id}: {e}")
            return {}
