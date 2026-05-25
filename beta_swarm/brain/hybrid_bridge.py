import logging
from .kuzudb_manager import KuzuBrain
from .neo4j_manager import Neo4jBrain

logger = logging.getLogger(__name__)

class HybridBridge:
    """
    Bridges local memory (KuzuDB) and global knowledge (Neo4j).
    Supports syncing important insights from local to global, and fetching patterns from global to local.
    """
    def __init__(self):
        self.local_brain = KuzuBrain()
        self.global_brain = Neo4jBrain()

    def sync_to_global(self, agent_id: str, topic: str, insight: str):
        """Extract insight from local memory and promote to global knowledge."""
        logger.info(f"Syncing insight from agent {agent_id} to global topic {topic}")
        self.global_brain.add_global_knowledge(topic, insight)
        
    def fetch_from_global(self, topic: str) -> list[str]:
        """Fetch global knowledge for a specific topic."""
        return self.global_brain.query_knowledge(topic)

    def close(self):
        self.global_brain.close()
