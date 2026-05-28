"""
SQLite Message Bus — Phase 2 inter-agent communication.
Agents can publish messages to named topics and subscribe/consume from them.
Thread-safe, persistent, WAL-mode SQLite.
"""
import sqlite3, json, time, uuid, logging, threading
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
_BUS_PATH = "brain_message_bus.db"


class MessageBus:
    """Lightweight SQLite-backed pub/sub message bus."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = _BUS_PATH):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._db_path = db_path
                inst._local = threading.local()
                inst._init_schema()
                cls._instance = inst
            return cls._instance

    @classmethod
    def get_instance(cls, db_path: str = _BUS_PATH) -> "MessageBus":
        return cls(db_path)

    def _conn(self):
        if not hasattr(self._local, "conn"):
            conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self):
        conn = self._conn()
        with conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                sender TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at REAL,
                consumed_at REAL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_topic_status ON messages(topic, status)")

    # ── Publish ─────────────────────────────────────────────────────────#
    def publish(self, topic: str, payload: Dict[str, Any], sender: str = "system") -> str:
        msg_id = str(uuid.uuid4())
        conn = self._conn()
        with conn:
            conn.execute(
                "INSERT INTO messages (id, topic, sender, payload, status, created_at) VALUES (?,?,?,?,?,?)",
                (msg_id, topic, sender, json.dumps(payload), "pending", time.time())
            )
        logger.debug(f"[Bus] Published to '{topic}' from '{sender}': {msg_id}")
        return msg_id

    # ── Consume (pop oldest pending) ────────────────────────────────────#
    def consume(self, topic: str, consumer: str = "anon") -> Optional[Dict[str, Any]]:
        conn = self._conn()
        with conn:
            cursor = conn.execute(
                "SELECT id, topic, sender, payload FROM messages WHERE topic=? AND status='pending' "
                "ORDER BY created_at ASC LIMIT 1",
                (topic,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE messages SET status='consumed', consumed_at=? WHERE id=?",
                (time.time(), row["id"])
            )
        msg = {"id": row["id"], "topic": row["topic"], "sender": row["sender"],
               "payload": json.loads(row["payload"])}
        logger.debug(f"[Bus] '{consumer}' consumed '{row['id']}' from '{topic}'")
        return msg

    # ── Peek (non-destructive) ──────────────────────────────────────────#
    def peek(self, topic: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._conn()
        cursor = conn.execute(
            "SELECT id, topic, sender, payload, created_at FROM messages WHERE topic=? AND status='pending' "
            "ORDER BY created_at ASC LIMIT ?",
            (topic, limit)
        )
        return [{"id": r["id"], "topic": r["topic"], "sender": r["sender"],
                 "payload": json.loads(r["payload"]), "created_at": r["created_at"]}
                for r in cursor.fetchall()]

    # ── Drain all pending for a topic ───────────────────────────────────#
    def drain(self, topic: str) -> List[Dict[str, Any]]:
        msgs = []
        while True:
            m = self.consume(topic, consumer="drain")
            if m is None:
                break
            msgs.append(m)
        return msgs

    # ── Stats ────────────────────────────────────────────────────────── #
    def stats(self) -> Dict[str, Any]:
        conn = self._conn()
        pending  = conn.execute("SELECT count(*) FROM messages WHERE status='pending'").fetchone()[0]
        consumed = conn.execute("SELECT count(*) FROM messages WHERE status='consumed'").fetchone()[0]
        topics   = conn.execute("SELECT DISTINCT topic FROM messages WHERE status='pending'").fetchall()
        return {
            "pending": pending,
            "consumed": consumed,
            "active_topics": [r[0] for r in topics]
        }

    # ── Purge old consumed messages ──────────────────────────────────── #
    def purge(self, older_than_hours: float = 24.0) -> int:
        cutoff = time.time() - older_than_hours * 3600
        conn = self._conn()
        with conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE status='consumed' AND consumed_at < ?", (cutoff,)
            )
        return cursor.rowcount
