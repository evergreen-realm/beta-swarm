import os
import kuzu
import logging

logger = logging.getLogger(__name__)

class KuzuBrain:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("KUZU_DB_PATH", "./kuzu_db")
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        self.db = kuzu.Database(self.db_path)
        self.conn = kuzu.Connection(self.db)
        self._init_schema()

    def _init_schema(self):
        """Initialize basic schema for agent memory if not exists."""
        try:
            # Check if schema exists, if not create
            tables = self.conn.execute("CALL show_tables() RETURN *;").get_as_df()
            if tables.empty or "Agent" not in tables['name'].values:
                self.conn.execute("CREATE NODE TABLE Agent (id STRING, name STRING, stage STRING, PRIMARY KEY (id));")
                self.conn.execute("CREATE NODE TABLE Memory (id STRING, content STRING, type STRING, timestamp INT64, PRIMARY KEY (id));")
                self.conn.execute("CREATE REL TABLE HAS_MEMORY (FROM Agent TO Memory);")
                logger.info("KuzuDB schema initialized.")
        except Exception as e:
            logger.error(f"Error initializing KuzuDB schema: {e}")

    def add_agent(self, agent_id: str, name: str, stage: str):
        query = "MERGE (a:Agent {id: $id, name: $name, stage: $stage})"
        self.conn.execute(query, parameters={"id": agent_id, "name": name, "stage": stage})

    def store_agent_memory(self, agent_id: str, fact: str, fact_type: str = "observation"):
        import time
        import uuid
        memory_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        query = """
        MATCH (a:Agent {id: $agent_id})
        CREATE (m:Memory {id: $mem_id, content: $content, type: $type, timestamp: $ts})
        CREATE (a)-[:HAS_MEMORY]->(m)
        """
        try:
            self.conn.execute(query, parameters={
                "agent_id": agent_id,
                "mem_id": memory_id,
                "content": fact,
                "type": fact_type,
                "ts": timestamp
            })
            return {"status": "success", "memory_id": memory_id}
        except Exception as e:
            logger.error(f"Error storing Kuzu memory: {e}")
            return {"status": "error", "message": str(e)}

    def query_context(self, agent_id: str, query_text: str):
        # Basic context retrieval: get all memories for this agent
        # In a real scenario, this would use vector search or keyword matching
        cypher = """
        MATCH (a:Agent {id: $agent_id})-[:HAS_MEMORY]->(m:Memory)
        RETURN m.content AS content, m.type AS type, m.timestamp AS timestamp
        ORDER BY m.timestamp DESC LIMIT 10
        """
        try:
            df = self.conn.execute(cypher, parameters={"agent_id": agent_id}).get_as_df()
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error querying Kuzu context: {e}")
            return []

    def export_all_facts(self):
        cypher = """
        MATCH (a:Agent)-[:HAS_MEMORY]->(m:Memory)
        RETURN a.id AS agent_id, m.content AS fact, m.type AS fact_type
        """
        try:
            df = self.conn.execute(cypher).get_as_df()
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error exporting Kuzu facts: {e}")
            return []

    def query(self, query: str, parameters: dict = None):
        return self.conn.execute(query, parameters=parameters or {}).get_as_df()
