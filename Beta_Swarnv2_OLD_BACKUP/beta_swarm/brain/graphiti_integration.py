from typing import Dict, List
from datetime import datetime
import os

class GraphitiBrain:
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", neo4j_user: str = "neo4j", neo4j_password: str = None, openai_api_key: str = None):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD", "betaswarm123")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self._driver = None
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        except Exception:
            self._driver = None
    
    def add_episode(self, content: str, source: str, source_description: str, episode_type: str = "memory") -> Dict:
        if not self._driver:
            return {"status": "error", "message": "Neo4j not connected"}
        with self._driver.session() as session:
            result = session.run("""
                CREATE (e:Episode {id: randomUUID(), content: $content, source: $source, 
                source_description: $source_description, episode_type: $episode_type,
                valid_from: datetime(), valid_until: datetime({year: 2099})})
                RETURN e.id as id
            """, content=content, source=source, source_description=source_description, episode_type=episode_type)
            record = result.single()
            return {"status": "complete", "episode_id": record["id"] if record else None}
    
    def search(self, query: str, group_ids: List[str] = None) -> List[Dict]:
        if not self._driver:
            return []
        with self._driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                WHERE e.content CONTAINS $query AND (e.valid_until > datetime() OR e.valid_until IS NULL)
                RETURN e.content as content, e.source as source, e.episode_type as type
                LIMIT 20
            """, query=query)
            return [dict(r) for r in result]
    
    def get_entity_graph(self, entity_names: List[str]) -> Dict:
        if not self._driver:
            return {"nodes": [], "edges": []}
        with self._driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                WHERE ANY(name IN $names WHERE e.content CONTAINS name)
                RETURN e.content as content, e.source as source
                LIMIT 50
            """, names=entity_names)
            return {"nodes": [dict(r) for r in result], "edges": []}
    
    def close(self):
        if self._driver:
            self._driver.close()
