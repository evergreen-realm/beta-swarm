import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)

def _load_env_file():
    import os
    try:
        # Check current directory and up to 3 parent directories for .env
        paths_to_check = [
            ".env",
            os.path.join(os.path.dirname(__file__), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        ]
        for path in paths_to_check:
            if os.path.exists(path):
                with open(path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                k, v = parts[0].strip(), parts[1].strip()
                                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                    v = v[1:-1]
                                if k not in os.environ:
                                    os.environ[k] = v
                break
    except Exception as e:
        logger.debug(f"Failed to load .env: {e}")

class GraphitiManager:
    """Manager for Graphiti-like Temporal Knowledge Graphs using Neo4j Cypher."""

    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", username: str = "neo4j", password: str = "password"):
        try:
            import os
            _load_env_file()
            self.neo4j_uri = neo4j_uri
            if neo4j_uri == "bolt://localhost:7687":
                self.neo4j_uri = os.getenv("NEO4J_URI", neo4j_uri)
                
            self.username = username
            if username == "neo4j":
                self.username = os.getenv("NEO4J_USER", username)
                
            self.password = password
            if password == "password":
                self.password = os.getenv("NEO4J_PASSWORD", password)
                
            self._driver = None
        except Exception as e:
            logger.error(f"Initialization error in GraphitiManager: {e}")

    def _get_driver(self):
        try:
            if self._driver is None:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(self.neo4j_uri, auth=(self.username, self.password))
            return self._driver
        except Exception as e:
            raise e

    def add_fact(self, entity_id: str, fact_content: str, source: str = "system", timestamp: Any = None) -> Dict[str, Any]:
        try:
            driver = self._get_driver()
            
            if timestamp is None:
                valid_from_str = datetime.now(timezone.utc).isoformat()
            elif isinstance(timestamp, datetime):
                valid_from_str = timestamp.isoformat()
            else:
                valid_from_str = str(timestamp)
                
            created_at_str = datetime.now(timezone.utc).isoformat()
            fact_id = str(uuid.uuid4())

            def _add_fact_tx(tx, ent_id, f_id, content, src, val_from, cre_at):
                tx.run("MERGE (e:Entity {id: $entity_id})", entity_id=ent_id)
                tx.run("""
                    MATCH (e:Entity {id: $entity_id})-[:HAS_FACT]->(old_f:Fact)
                    WHERE old_f.valid_until IS NULL AND old_f.created_at < datetime($valid_from)
                    SET old_f.valid_until = datetime($valid_from)
                """, entity_id=ent_id, valid_from=val_from)
                tx.run("""
                    MATCH (e:Entity {id: $entity_id})
                    CREATE (f:Fact {
                        id: $fact_id,
                        content: $fact_content,
                        valid_from: datetime($valid_from),
                        valid_until: null,
                        source: $source,
                        created_at: datetime($created_at)
                    })
                    CREATE (e)-[:HAS_FACT {valid_from: datetime($valid_from)}]->(f)
                """, entity_id=ent_id, fact_id=f_id, fact_content=content, 
                     valid_from=val_from, source=src, created_at=cre_at)

            with driver.session() as session:
                session.execute_write(_add_fact_tx, entity_id, fact_id, fact_content, source, valid_from_str, created_at_str)

            return {
                "status": "ok",
                "fact_id": fact_id,
                "entity_id": entity_id,
                "timestamp": valid_from_str
            }
        except Exception as e:
            logger.error(f"Error in add_fact: {e}")
            return {
                "status": "error",
                "error": str(e),
                "note": "Neo4j may not be running. Start with: docker start neo4j"
            }

    def query_facts(self, entity_id: str, as_of: Any = None) -> Dict[str, Any]:
        try:
            driver = self._get_driver()
            
            if as_of is not None:
                if isinstance(as_of, datetime):
                    as_of_str = as_of.isoformat()
                else:
                    as_of_str = str(as_of)
            else:
                as_of_str = None

            def _query_facts_tx(tx, ent_id, as_of_t):
                if as_of_t is not None:
                    query = """
                    MATCH (e:Entity {id: $entity_id})-[:HAS_FACT]->(f:Fact)
                    WHERE f.valid_from <= datetime($as_of) AND (f.valid_until IS NULL OR f.valid_until > datetime($as_of))
                    RETURN f.id AS id, f.content AS content, toString(f.valid_from) AS valid_from, 
                           toString(f.valid_until) AS valid_until, f.source AS source, toString(f.created_at) AS created_at
                    """
                    result = tx.run(query, entity_id=ent_id, as_of=as_of_t)
                else:
                    query = """
                    MATCH (e:Entity {id: $entity_id})-[:HAS_FACT]->(f:Fact)
                    WHERE f.valid_until IS NULL
                    RETURN f.id AS id, f.content AS content, toString(f.valid_from) AS valid_from, 
                           toString(f.valid_until) AS valid_until, f.source AS source, toString(f.created_at) AS created_at
                    """
                    result = tx.run(query, entity_id=ent_id)
                
                facts = []
                for record in result:
                    facts.append({
                        "fact_id": record["id"],
                        "content": record["content"],
                        "valid_from": record["valid_from"],
                        "valid_until": record["valid_until"],
                        "source": record["source"],
                        "created_at": record["created_at"]
                    })
                return facts

            with driver.session() as session:
                facts_list = session.execute_read(_query_facts_tx, entity_id, as_of_str)

            return {
                "status": "ok",
                "entity_id": entity_id,
                "fact_count": len(facts_list),
                "facts": facts_list
            }
        except Exception as e:
            logger.error(f"Error in query_facts: {e}")
            return {
                "status": "error",
                "error": str(e),
                "note": "Neo4j may not be running. Start with: docker start neo4j"
            }

    def get_entity_history(self, entity_id: str) -> Dict[str, Any]:
        try:
            driver = self._get_driver()

            def _get_history_tx(tx, ent_id):
                query = """
                MATCH (e:Entity {id: $entity_id})-[:HAS_FACT]->(f:Fact)
                RETURN f.id AS id, f.content AS content, toString(f.valid_from) AS valid_from, 
                       toString(f.valid_until) AS valid_until, f.source AS source, toString(f.created_at) AS created_at
                ORDER BY f.valid_from ASC
                """
                result = tx.run(query, entity_id=ent_id)
                history = []
                for record in result:
                    history.append({
                        "fact_id": record["id"],
                        "content": record["content"],
                        "valid_from": record["valid_from"],
                        "valid_until": record["valid_until"],
                        "source": record["source"],
                        "created_at": record["created_at"]
                    })
                return history

            with driver.session() as session:
                history_list = session.execute_read(_get_history_tx, entity_id)

            return {
                "status": "ok",
                "entity_id": entity_id,
                "version_count": len(history_list),
                "history": history_list
            }
        except Exception as e:
            logger.error(f"Error in get_entity_history: {e}")
            return {
                "status": "error",
                "error": str(e),
                "note": "Neo4j may not be running. Start with: docker start neo4j"
            }

    def close(self):
        try:
            if self._driver is not None:
                self._driver.close()
                self._driver = None
        except Exception as e:
            logger.error(f"Error closing GraphitiManager: {e}")

if __name__ == "__main__":
    gm = GraphitiManager()
    result = gm.add_fact("test_project", "Project created with React frontend", "s1_ideation")
    print(result)
    print(gm.query_facts("test_project"))
    gm.close()
