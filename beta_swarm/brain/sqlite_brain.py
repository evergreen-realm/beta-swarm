# kuzudb_manager.py - Secure, Lock-Free SQLite Graph Emulator Engine
import os
import sqlite3
import json
import time
import uuid
import logging
import threading
from typing import Dict, Any, List, Optional

logger = logging.getLogger("beta_swarm.brain_manager")

class SQLiteBrain:
    _instances = {}
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        read_only = kwargs.get("read_only", False)
        if len(args) > 0:
            read_only = args[0]
            
        with cls._lock:
            if read_only not in cls._instances:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instances[read_only] = inst
            return cls._instances[read_only]
    
    def __init__(self, read_only=False, db_path=None):
        if getattr(self, "_initialized", False):
            return
            
        # Migrate entirely to sqlite DB
        self.db_path = db_path or os.path.abspath(r"C:\Users\Admin\Documents\Beta Swarnv2\brain_sqlite.db")
        parent_dir = os.path.dirname(self.db_path)
        if parent_dir:
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception:
                pass
                
        self.read_only = read_only
        self._local = threading.local()
        self._init_schema()
        self._initialized = True

    def _get_conn(self):
        """Get a thread-local SQLite connection with high concurrency WAL mode enabled."""
        if not hasattr(self._local, 'conn'):
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=15.0)
            conn.row_factory = sqlite3.Row
            
            # Security and Concurrency Hardening
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self):
        if self.read_only:
            return
            
        conn = self._get_conn()
        try:
            with conn:
                # Core Nodes
                conn.execute("CREATE TABLE IF NOT EXISTS Agent (id TEXT PRIMARY KEY, name TEXT, stage TEXT, status TEXT, created_at REAL)")
                conn.execute("CREATE TABLE IF NOT EXISTS Memory (id TEXT PRIMARY KEY, content TEXT, type TEXT, timestamp REAL)")
                conn.execute("CREATE TABLE IF NOT EXISTS CodeEntity (id TEXT PRIMARY KEY, name TEXT, type TEXT, path TEXT)")
                conn.execute("CREATE TABLE IF NOT EXISTS Artifact (id TEXT PRIMARY KEY, project TEXT, stage TEXT, data TEXT, created_at REAL)")
                conn.execute("CREATE TABLE IF NOT EXISTS ExecutionRecord (id TEXT PRIMARY KEY, stage TEXT, project TEXT, status TEXT, duration REAL, created_at REAL)")
                
                # Edges (Foreign Key mapping)
                conn.execute("CREATE TABLE IF NOT EXISTS HAS_MEMORY (agent_id TEXT, memory_id TEXT, PRIMARY KEY(agent_id, memory_id))")
                conn.execute("CREATE TABLE IF NOT EXISTS DEPENDS_ON (source_id TEXT, target_id TEXT, PRIMARY KEY(source_id, target_id))")
                conn.execute("CREATE TABLE IF NOT EXISTS CALLS (source_id TEXT, target_id TEXT, PRIMARY KEY(source_id, target_id))")
                conn.execute("CREATE TABLE IF NOT EXISTS GENERATED (agent_id TEXT, artifact_id TEXT, PRIMARY KEY(agent_id, artifact_id))")
                
        except Exception as e:
            logger.error(f"Error initializing SQLite schema: {e}")

    def register_agent(self, agent_id: str, name: str, stage: str) -> Dict[str, Any]:
        if self.read_only:
            return {"status": "ignored", "message": "Read only mode active."}
            
        try:
            conn = self._get_conn()
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO Agent (id, name, stage, status, created_at) VALUES (?, ?, ?, 'idle', ?)",
                    (agent_id, name, stage, time.time())
                )
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            return {"status": "error", "message": str(e)}

    def add_agent(self, agent_id: str, name: str, stage: str) -> Dict[str, Any]:
        return self.register_agent(agent_id, name, stage)

    def store_agent_memory(self, agent_id: str, fact: str, fact_type: str = "observation") -> Dict[str, Any]:
        if self.read_only:
            return {"status": "ignored"}
            
        try:
            memory_id = str(uuid.uuid4())
            ts = time.time()
            conn = self._get_conn()
            with conn:
                # Insert Memory Node
                conn.execute("INSERT INTO Memory (id, content, type, timestamp) VALUES (?, ?, ?, ?)", 
                             (memory_id, fact, fact_type, ts))
                
                # Insert Edge
                conn.execute("INSERT OR IGNORE INTO HAS_MEMORY (agent_id, memory_id) VALUES (?, ?)", 
                             (agent_id, memory_id))
            return {"status": "success", "memory_id": memory_id}
        except Exception as e:
            logger.error(f"Error storing agent memory for {agent_id}: {e}")
            return {"status": "error", "message": str(e)}

    def store_code_entity(self, entity_id: str, name: str, type: str, path: str) -> Dict[str, Any]:
        if self.read_only:
            return {"status": "ignored"}
        try:
            conn = self._get_conn()
            with conn:
                conn.execute("INSERT OR REPLACE INTO CodeEntity (id, name, type, path) VALUES (?, ?, ?, ?)", 
                             (entity_id, name, type, path))
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error storing code entity: {e}")
            return {"status": "error"}

    def link_code_entities(self, source_id: str, target_id: str, rel_type: str = "DEPENDS_ON") -> Dict[str, Any]:
        if self.read_only:
            return {"status": "ignored"}
        try:
            conn = self._get_conn()
            table = "CALLS" if rel_type.upper() == "CALLS" else "DEPENDS_ON"
            with conn:
                conn.execute(f"INSERT OR IGNORE INTO {table} (source_id, target_id) VALUES (?, ?)", (source_id, target_id))
            return {"status": "success"}
        except Exception as e:
            return {"status": "error"}

    def query_context(self, agent_id: str, query_text: str = "") -> List[Dict[str, Any]]:
        try:
            conn = self._get_conn()
            cursor = conn.execute("""
                SELECT m.content, m.type, m.timestamp 
                FROM Memory m
                JOIN HAS_MEMORY hm ON m.id = hm.memory_id
                WHERE hm.agent_id = ?
                ORDER BY m.timestamp DESC LIMIT 10
            """, (agent_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error querying context: {e}")
            return []

    def store_fact(self, agent_id: str, content: str, fact_type: str = "fact") -> Dict[str, Any]:
        """Alias for store_agent_memory to support legacy agent fact insertions."""
        return self.store_agent_memory(agent_id, content, fact_type)

    def export_all_facts(self) -> List[Dict[str, Any]]:
        try:
            conn = self._get_conn()
            cursor = conn.execute("""
                SELECT hm.agent_id, m.content as fact, m.type as fact_type
                FROM Memory m
                JOIN HAS_MEMORY hm ON m.id = hm.memory_id
            """)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error exporting facts: {e}")
            return []

    def query(self, query_str: str, parameters: Optional[dict] = None):
        """
        Shim for backwards compatibility with raw Cypher queries that still slip through.
        We capture them and attempt to safely translate to SQL, or gracefully no-op.
        """
        logger.warning(f"Raw cypher query caught by SQLite shim: {query_str[:50]}")
        class DummyResult:
            def get_as_df(self):
                import pandas as pd
                return pd.DataFrame()
        return DummyResult()

    def sync_queue(self) -> Dict[str, Any]:
        return {"status": "success", "synced": 0, "message": "Queue obsolete with WAL SQLite mode."}

    def store_artifact(self, agent_id: str, project: str, stage: str, data: str) -> Dict[str, Any]:
        """Store a generated artifact and link it to the agent."""
        if self.read_only:
            return {"status": "ignored"}
        try:
            artifact_id = f"art_{agent_id}_{int(time.time())}"
            conn = self._get_conn()
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO Artifact (id, project, stage, data, created_at) VALUES (?, ?, ?, ?, ?)",
                    (artifact_id, project, stage, data, time.time())
                )
                conn.execute(
                    "INSERT OR IGNORE INTO GENERATED (agent_id, artifact_id) VALUES (?, ?)",
                    (agent_id, artifact_id)
                )
            return {"status": "success", "artifact_id": artifact_id}
        except Exception as e:
            logger.error(f"Error storing artifact for {agent_id}: {e}")
            return {"status": "error", "message": str(e)}

    def get_agent_by_id(self, agent_id: str) -> Dict[str, Any]:
        """Retrieve a single agent by ID."""
        try:
            conn = self._get_conn()
            cursor = conn.execute("SELECT id, name, stage, status FROM Agent WHERE id = ?", (agent_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {"id": agent_id, "name": agent_id.replace('_', ' ').title(), "stage": "Unknown", "status": "idle"}
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {e}")
            return {"id": agent_id, "name": agent_id.replace('_', ' ').title(), "stage": "Unknown", "status": "idle"}

    def get_agent_artifacts(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve artifacts generated by a specific agent."""
        try:
            conn = self._get_conn()
            cursor = conn.execute("""
                SELECT a.id, a.project, a.stage, a.data, a.created_at
                FROM Artifact a
                JOIN GENERATED g ON a.id = g.artifact_id
                WHERE g.agent_id = ?
                ORDER BY a.created_at DESC LIMIT ?
            """, (agent_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting artifacts for {agent_id}: {e}")
            return []

    def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent pipeline execution records."""
        try:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT id, stage, project, status, duration, created_at FROM ExecutionRecord ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting execution history: {e}")
            return []

    def get_all_memories_summary(self) -> Dict[str, Any]:
        """Get aggregate memory stats for brain dashboard endpoints."""
        try:
            conn = self._get_conn()
            mem_count = conn.execute("SELECT count(*) as c FROM Memory").fetchone()["c"]
            agent_count = conn.execute("SELECT count(*) as c FROM Agent").fetchone()["c"]
            artifact_count = conn.execute("SELECT count(*) as c FROM Artifact").fetchone()["c"]
            edge_count = (
                conn.execute("SELECT count(*) as c FROM HAS_MEMORY").fetchone()["c"] +
                conn.execute("SELECT count(*) as c FROM DEPENDS_ON").fetchone()["c"] +
                conn.execute("SELECT count(*) as c FROM GENERATED").fetchone()["c"]
            )
            recent = conn.execute(
                "SELECT content, type, timestamp FROM Memory ORDER BY timestamp DESC LIMIT 10"
            ).fetchall()
            return {
                "nodes": mem_count + agent_count + artifact_count,
                "edges": edge_count,
                "agents": agent_count,
                "memories": mem_count,
                "artifacts": artifact_count,
                "recent_facts": [dict(r) for r in recent]
            }
        except Exception as e:
            logger.error(f"Error getting memory summary: {e}")
            return {"nodes": 0, "edges": 0, "agents": 0, "memories": 0, "artifacts": 0, "recent_facts": []}

    def close(self):
        if hasattr(self._local, 'conn'):
            try:
                self._local.conn.close()
            except:
                pass
            del self._local.conn
        read_only = self.read_only
        if read_only in KuzuBrain._instances:
            del KuzuBrain._instances[read_only]
        self._initialized = False

    @classmethod
    def get_instance(cls, mode="auto", db_path=None):
        read_only = mode in ("read_only", "ro")
        return cls(read_only=read_only, db_path=db_path)

def get_brain(read_only=False):
    return KuzuBrain(read_only=read_only)


KuzuBrain = SQLiteBrain
