import os
import httpx
import logging

logger = logging.getLogger(__name__)

class CogneeClient:
    """Client for Cognee Knowledge Graph Pipeline."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("COGNEE_BASE_URL", "http://localhost:8000")
        self.client = httpx.Client(timeout=30.0)
        
    def add_document(self, content: str, doc_id: str = None) -> dict:
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
            return {}
            
    def cognify(self) -> dict:
        try:
            url = f"{self.base_url}/api/v1/cognify"
            response = self.client.post(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to trigger Cognee cognify: {e}")
            return {}
