import logging
import os
import uuid
import datetime
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    GRAPHITI_CORE_AVAILABLE = True
except ImportError:
    GRAPHITI_CORE_AVAILABLE = False

class GraphitiManager:
    def __init__(self, neo4j_uri="bolt://localhost:7687", username="neo4j", password="password"):
        # Resolve config from environment if defaults are provided
        self.neo4j_uri = os.getenv("NEO4J_URI", neo4j_uri)
        self.username = os.getenv("NEO4J_USER", username)
        self.password = os.getenv("NEO4J_PASSWORD", password)
        self._driver = None
        self.graphiti = None

        if GRAPHITI_CORE_AVAILABLE:
            try:
                self.graphiti = Graphiti(self.neo4j_uri, self.username, self.password)
                logger.info("GraphitiManager initialized using official graphiti_core library.")
            except Exception as e:
                logger.warning(f"Failed to initialize official Graphiti library: {e}. Falling back to Cypher/SQLite.")
        else:
            logger.warning("graphiti_core not available. Falling back to Cypher/SQLite manager.")

    def _get_driver(self):
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(self.neo4j_uri, auth=(self.username, self.password))
            except Exception as e:
                logger.warning(f"Could not connect to Neo4j database: {e}")
                self._driver = None
        return self._driver

    async def add_episode(self, content: str, source: str):
        if self.graphiti:
            try:
                await self.graphiti.add_episode(
                    name=f"episode_{datetime.now().timestamp()}",
                    episode_body=content,
                    source=source,
                    source_description="Beta Swarm agent",
                    episode_type=EpisodeType.message
                )
                return {"status": "success", "mode": "graphiti_core"}
            except Exception as e:
                logger.error(f"graphiti_core add_episode failed: {e}. Falling back.")
        
        # Fallback 1: Direct Neo4j Cypher insert
        driver = self._get_driver()
        if driver:
            try:
                episode_id = str(uuid.uuid4())
                query = """
                CREATE (e:Episode {
                    id: $id, 
                    content: $content, 
                    source: $source, 
                    source_description: $source_description, 
                    episode_type: $episode_type,
                    created_at: datetime()
                })
                RETURN e.id as id
                """
                with driver.session() as session:
                    session.run(query, {
                        "id": episode_id,
                        "content": content,
                        "source": source,
                        "source_description": "Beta Swarm agent (Cypher Fallback)",
                        "episode_type": "message"
                    })
                return {"status": "success", "mode": "cypher_fallback", "episode_id": episode_id}
            except Exception as cypher_err:
                logger.error(f"Neo4j Cypher fallback failed: {cypher_err}")

        # Fallback 2: SQLite Local Temporal Facts
        try:
            from beta_swarm.brain.sqlite_brain import get_brain
            brain = get_brain()
            # Storing memory in the SQLite store as a fallback
            res = brain.store_agent_memory(source, content[:500], "episode_fallback")
            return {"status": "success", "mode": "sqlite_fallback", "memory_id": res.get("memory_id")}
        except Exception as sql_err:
            logger.error(f"SQLite fallback failed: {sql_err}")
            return {"status": "error", "error": str(sql_err)}

    async def search(self, query: str, limit: int = 5):
        if self.graphiti:
            try:
                return await self.graphiti.search(query, limit)
            except Exception as e:
                logger.error(f"graphiti_core search failed: {e}. Falling back.")

        # Fallback 1: Neo4j Cypher search
        driver = self._get_driver()
        if driver:
            try:
                cypher_query = """
                MATCH (e:Episode)
                WHERE e.content CONTAINS $query
                RETURN e.content as content, e.source as source
                LIMIT $limit
                """
                with driver.session() as session:
                    res = session.run(cypher_query, {"query": query, "limit": limit})
                    return [dict(r) for r in res]
            except Exception as cypher_err:
                logger.error(f"Neo4j Cypher search failed: {cypher_err}")

        # Fallback 2: SQLite search
        try:
            from beta_swarm.brain.sqlite_brain import get_brain
            brain = get_brain()
            # Storing in thread local SQLite, get summary
            summary = brain.get_all_memories_summary()
            recent_facts = summary.get("recent_facts", [])
            filtered = [f for f in recent_facts if query.lower() in f.get("content", "").lower()]
            return filtered[:limit]
        except Exception as sql_err:
            logger.error(f"SQLite search fallback failed: {sql_err}")
            return []

    # Keeping legacy methods for backward compatibility
    def add_fact(self, entity_id: str, fact_content: str, source: str = "system", timestamp: Any = None) -> Dict[str, Any]:
        try:
            from beta_swarm.brain.sqlite_brain import get_brain
            brain = get_brain()
            res = brain.store_agent_memory(source, fact_content, "fact")
            return {
                "status": "ok",
                "fact_id": res.get("memory_id", str(uuid.uuid4())),
                "entity_id": entity_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def query_facts(self, entity_id: str, as_of: Any = None) -> Dict[str, Any]:
        try:
            from beta_swarm.brain.sqlite_brain import get_brain
            brain = get_brain()
            mems = brain.query_context(entity_id)
            facts_list = [{
                "fact_id": str(uuid.uuid4()),
                "content": m.get("content"),
                "valid_from": m.get("timestamp"),
                "valid_until": None,
                "source": "sqlite",
                "created_at": m.get("timestamp")
            } for m in mems]
            return {
                "status": "ok",
                "entity_id": entity_id,
                "fact_count": len(facts_list),
                "facts": facts_list
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_entity_history(self, entity_id: str) -> Dict[str, Any]:
        return self.query_facts(entity_id)

    def close(self):
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass
