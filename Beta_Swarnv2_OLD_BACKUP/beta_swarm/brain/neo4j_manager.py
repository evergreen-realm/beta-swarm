import os
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)

class Neo4jBrain:
    def __init__(self, uri: str = None, auth: tuple = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        if auth:
            self.user, self.password = auth
        else:
            self.user = os.getenv("NEO4J_USER", "neo4j")
            self.password = os.getenv("NEO4J_PASSWORD", "betaswarm123")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def store_memory(self, agent_id: str, fact: str, fact_type: str = "observation"):
        query = """
        MERGE (a:Agent {id: $agent_id})
        CREATE (m:Fact {content: $fact, type: $type, timestamp: timestamp()})
        CREATE (a)-[:PRODUCED]->(m)
        """
        try:
            with self.driver.session() as session:
                session.run(query, agent_id=agent_id, fact=fact, type=fact_type)
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error storing Neo4j memory: {e}")
            return {"status": "error", "message": str(e)}

    def query_context(self, agent_id: str, query_text: str):
        # Basic context retrieval from global graph
        query = """
        MATCH (a:Agent {id: $agent_id})-[:PRODUCED]->(f:Fact)
        RETURN f.content AS content, f.type AS type, f.timestamp AS timestamp
        ORDER BY f.timestamp DESC LIMIT 10
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, agent_id=agent_id)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Error querying Neo4j context: {e}")
            return []

    def add_global_knowledge(self, topic: str, content: str):
        query = """
        MERGE (t:Topic {name: $topic})
        MERGE (k:Knowledge {content: $content})
        MERGE (t)-[:HAS_KNOWLEDGE]->(k)
        """
        try:
            with self.driver.session() as session:
                session.run(query, topic=topic, content=content)
        except Exception as e:
            logger.error(f"Error adding global knowledge to Neo4j: {e}")

    def query_knowledge(self, topic: str):
        query = """
        MATCH (t:Topic {name: $topic})-[:HAS_KNOWLEDGE]->(k:Knowledge)
        RETURN k.content AS content
        """
        results = []
        try:
            with self.driver.session() as session:
                result = session.run(query, topic=topic)
                for record in result:
                    results.append(record["content"])
        except Exception as e:
            logger.error(f"Error querying Neo4j: {e}")
        return results

    def execute_query(self, query: str, parameters: dict = None):
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Neo4j query execution error: {e}")
            return []
