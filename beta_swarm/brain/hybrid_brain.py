from beta_swarm.brain.sqlite_brain import KuzuBrain
from beta_swarm.brain.neo4j_manager import Neo4jBrain
from beta_swarm.brain.obsidian_manager import ObsidianManager
from typing import Dict, List, Optional
import os

class HybridBrain:
    def __init__(self, kuzu_db_path: str = "./brain/kuzu.db", neo4j_uri: str = "bolt://localhost:7687", neo4j_auth: tuple = None):
        self.kuzu = KuzuBrain(kuzu_db_path)
        neo4j_auth = neo4j_auth or (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "betaswarm123"))
        self.neo4j = Neo4jBrain(neo4j_uri, neo4j_auth)
        
        # Connect to the Obsidian Vault using the project folder
        vault_path = os.getenv("OBSIDIAN_VAULT_PATH", os.path.join(os.getcwd(), "obsidian-vault"))
        self.obsidian = ObsidianManager(vault_path)
    
    def store_memory(self, agent_id: str, fact: str, fact_type: str = "observation") -> Dict:
        kuzu_result = self.kuzu.store_agent_memory(agent_id, fact, fact_type)
        neo4j_result = self.neo4j.store_memory(agent_id, fact, fact_type)
        
        # If this is a high-level insight or research, mirror it to Obsidian
        obsidian_status = "skipped"
        if fact_type in ["insight", "research", "synthesis", "decision"]:
            folder_map = {
                "insight": "03-Brain/insights",
                "research": "04-Research",
                "synthesis": "03-Brain/insights",
                "decision": "01-Projects"
            }
            folder = folder_map.get(fact_type, "03-Brain/insights")
            
            success = self.obsidian.create_note(
                title=f"{agent_id}_{fact_type}_{kuzu_result.get('memory_id', 'note')[:8]}",
                content=fact,
                tags=["beta_swarm", agent_id, fact_type],
                folder=folder
            )
            self.obsidian.append_to_daily_note(f"**{agent_id} ({fact_type})**: {fact}")
            obsidian_status = "synced" if success else "failed"

        return {"kuzu": kuzu_result, "neo4j": neo4j_result, "obsidian": obsidian_status}
    
    def query_context(self, agent_id: str, query: str) -> List[Dict]:
        local = self.kuzu.query_context(agent_id, query)
        if local:
            return local
        return self.neo4j.query_context(agent_id, query)
    
    def sync(self) -> Dict:
        facts = self.kuzu.export_all_facts()
        for fact in facts:
            self.neo4j.store_memory(fact["agent_id"], fact["fact"], fact.get("fact_type", "observation"))
        return {"synced": len(facts)}
