"""
GraphitiManager — Temporal Knowledge Graph for Beta Swarm.

Priority chain:
  1. graphiti_core (if pip-installed and Neo4j reachable)
  2. Direct Neo4j Cypher (if neo4j driver available)
  3. SQLite temporal facts table (always available, zero-dep fallback)

The SQLite fallback stores every fact with valid_from / valid_until timestamps
so time-travel queries work without any external service.
"""
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Try graphiti_core ──────────────────────────────────────────────────── #
try:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    _GRAPHITI_CORE = True
except ImportError:
    _GRAPHITI_CORE = False

# ── SQLite temporal facts DB path ─────────────────────────────────────── #
_DEFAULT_DB = os.path.join(
    os.path.dirname(__file__), "..", "..", "graphiti_temporal.db"
)


class _SQLiteTemporalStore:
    """Minimal SQLite-backed temporal fact store.

    Schema:
        temporal_facts(id, entity_id, content, source,
                       valid_from REAL, valid_until REAL,
                       created_at REAL)
    """

    def __init__(self, db_path: str = _DEFAULT_DB):
        self.db_path = os.path.abspath(db_path)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS temporal_facts (
                    id          TEXT PRIMARY KEY,
                    entity_id   TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    source      TEXT DEFAULT 'system',
                    valid_from  REAL NOT NULL,
                    valid_until REAL,
                    created_at  REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entity ON temporal_facts(entity_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_valid_from ON temporal_facts(valid_from)"
            )

    # ── Write ────────────────────────────────────────────────────────────#
    def add_fact(
        self,
        entity_id: str,
        content: str,
        source: str = "system",
        valid_from: Optional[float] = None,
        valid_until: Optional[float] = None,
    ) -> str:
        fact_id = str(uuid.uuid4())
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO temporal_facts "
                "(id, entity_id, content, source, valid_from, valid_until, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    fact_id,
                    entity_id,
                    content,
                    source,
                    valid_from or now,
                    valid_until,
                    now,
                ),
            )
        return fact_id

    def expire_fact(self, fact_id: str, valid_until: Optional[float] = None) -> bool:
        """Mark a fact as expired (sets valid_until to now if not provided)."""
        ts = valid_until or time.time()
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE temporal_facts SET valid_until=? WHERE id=?", (ts, fact_id)
            )
        return cur.rowcount > 0

    # ── Read ─────────────────────────────────────────────────────────────#
    def query_facts(
        self,
        entity_id: str,
        as_of: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return facts valid at `as_of` (defaults to now)."""
        ts = as_of or time.time()
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, entity_id, content, source, valid_from, valid_until, created_at
                FROM temporal_facts
                WHERE entity_id = ?
                  AND valid_from <= ?
                  AND (valid_until IS NULL OR valid_until > ?)
                ORDER BY valid_from DESC
                LIMIT ?
                """,
                (entity_id, ts, ts, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def search(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        ts = time.time()
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, entity_id, content, source, valid_from, valid_until
                FROM temporal_facts
                WHERE content LIKE ?
                  AND valid_from <= ?
                  AND (valid_until IS NULL OR valid_until > ?)
                ORDER BY valid_from DESC
                LIMIT ?
                """,
                (f"%{keyword}%", ts, ts, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, entity_id, content, source, valid_from, valid_until "
                "FROM temporal_facts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_episode(self, content: str, source: str) -> Dict[str, Any]:
        fid = self.add_fact(source, content, source=source)
        return {"status": "success", "mode": "sqlite_temporal", "fact_id": fid}


# ── Public manager ────────────────────────────────────────────────────── #
class GraphitiManager:
    """
    Unified temporal knowledge graph manager.

    Falls back gracefully:
      graphiti_core → Neo4j Cypher → SQLite temporal store
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
        db_path: str = _DEFAULT_DB,
    ):
        self.neo4j_uri = os.getenv("NEO4J_URI", neo4j_uri)
        self.username = os.getenv("NEO4J_USER", username)
        self.password = os.getenv("NEO4J_PASSWORD", password)
        self._driver = None
        self.graphiti = None

        # Always create the SQLite store (zero-dep guarantee)
        self._sqlite = _SQLiteTemporalStore(db_path)

        if _GRAPHITI_CORE:
            try:
                self.graphiti = Graphiti(self.neo4j_uri, self.username, self.password)
                logger.info("GraphitiManager: using graphiti_core.")
            except Exception as exc:
                logger.warning(
                    f"graphiti_core init failed ({exc}); falling back to Neo4j/SQLite."
                )
        else:
            logger.info(
                "graphiti_core not installed — using Neo4j/SQLite temporal fallback."
            )

    # ── Neo4j driver (lazy) ───────────────────────────────────────────── #
    def _get_driver(self):
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(
                    self.neo4j_uri, auth=(self.username, self.password)
                )
            except Exception as exc:
                logger.debug(f"Neo4j driver unavailable: {exc}")
        return self._driver

    # ── add_episode (async) ───────────────────────────────────────────── #
    async def add_episode(self, content: str, source: str) -> Dict[str, Any]:
        # 1. graphiti_core
        if self.graphiti:
            try:
                await self.graphiti.add_episode(
                    name=f"ep_{time.time()}",
                    episode_body=content,
                    source=source,
                    source_description="Beta Swarm",
                    episode_type=EpisodeType.message,
                )
                return {"status": "success", "mode": "graphiti_core"}
            except Exception as exc:
                logger.warning(f"graphiti_core add_episode failed: {exc}")

        # 2. Neo4j Cypher
        driver = self._get_driver()
        if driver:
            try:
                eid = str(uuid.uuid4())
                with driver.session() as s:
                    s.run(
                        "CREATE (e:Episode {id:$id,content:$c,source:$src,"
                        "valid_from:$vf,created_at:datetime()})",
                        {"id": eid, "c": content, "src": source, "vf": time.time()},
                    )
                return {
                    "status": "success",
                    "mode": "neo4j_cypher",
                    "episode_id": eid,
                }
            except Exception as exc:
                logger.warning(f"Neo4j Cypher add_episode failed: {exc}")

        # 3. SQLite temporal store
        return self._sqlite.add_episode(content, source)

    # ── search (async) ────────────────────────────────────────────────── #
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if self.graphiti:
            try:
                return await self.graphiti.search(query, limit)
            except Exception as exc:
                logger.warning(f"graphiti_core search failed: {exc}")

        driver = self._get_driver()
        if driver:
            try:
                with driver.session() as s:
                    res = s.run(
                        "MATCH (e:Episode) WHERE e.content CONTAINS $q "
                        "RETURN e.content AS content, e.source AS source LIMIT $lim",
                        {"q": query, "lim": limit},
                    )
                    return [dict(r) for r in res]
            except Exception as exc:
                logger.warning(f"Neo4j Cypher search failed: {exc}")

        return self._sqlite.search(query, limit)

    # ── Sync helpers (used by REST endpoints) ────────────────────────── #
    def add_fact(
        self,
        entity_id: str,
        fact_content: str,
        source: str = "system",
        valid_from: Optional[float] = None,
        valid_until: Optional[float] = None,
    ) -> Dict[str, Any]:
        fact_id = self._sqlite.add_fact(
            entity_id, fact_content, source=source,
            valid_from=valid_from, valid_until=valid_until,
        )
        return {
            "status": "ok",
            "fact_id": fact_id,
            "entity_id": entity_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def expire_fact(self, fact_id: str) -> Dict[str, Any]:
        ok = self._sqlite.expire_fact(fact_id)
        return {"status": "ok" if ok else "not_found", "fact_id": fact_id}

    def query_facts(
        self,
        entity_id: str,
        as_of: Optional[float] = None,
    ) -> Dict[str, Any]:
        facts = self._sqlite.query_facts(entity_id, as_of=as_of)
        return {
            "status": "ok",
            "entity_id": entity_id,
            "as_of": as_of or time.time(),
            "fact_count": len(facts),
            "facts": facts,
        }

    def get_entity_history(self, entity_id: str) -> Dict[str, Any]:
        return self.query_facts(entity_id)

    def get_recent_facts(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._sqlite.get_recent(limit)

    def close(self):
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass
