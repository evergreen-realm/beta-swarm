"""
SQLite-backed inter-agent message bus.

Replaces the in-memory asyncio.Queue singleton so that messages survive
process restarts and can be inspected externally.

Schema
──────
  messages (id, topic, sender, payload, created_at, delivered_at, status)

API
───
  bus = MessageBus()
  bus.publish("agent.coder.task", {"action": "write_file", ...}, sender="orchestrator")
  msgs = bus.consume("agent.coder.*", limit=10)   # wildcard match, marks as delivered
  bus.subscribe("agent.*.task", my_async_handler)  # async dispatch loop
  await bus.process()                              # run dispatch loop (blocks)
"""

import asyncio
import fnmatch
import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "message_bus.db",
)

# ── Schema ─────────────────────────────────────────────────────────────────────

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    topic        TEXT    NOT NULL,
    sender       TEXT    NOT NULL DEFAULT 'system',
    payload      TEXT    NOT NULL,
    created_at   REAL    NOT NULL,
    delivered_at REAL,
    status       TEXT    NOT NULL DEFAULT 'pending',  -- pending | delivered | dead
    retry_count  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_messages_topic  ON messages (topic);
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages (status);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at);
"""


class MessageBus:
    """
    SQLite-backed, process-safe, wildcard-aware inter-agent message bus.

    Thread-safe for publish/consume.  Async dispatch via `process()`.
    """

    _instance: Optional["MessageBus"] = None
    _lock = threading.Lock()

    # ── Singleton ─────────────────────────────────────────────────────────────

    def __new__(cls, db_path: Optional[str] = None):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._initialized = False
                cls._instance = inst
            return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if self._initialized:  # type: ignore[has-type]
            return
        self._db_path = os.path.abspath(db_path or _DEFAULT_DB)
        self._handlers: Dict[str, List[Callable]] = {}
        self._async_queue: asyncio.Queue = asyncio.Queue()
        self._initialized = True
        self._setup_db()
        logger.info(f"MessageBus initialised. DB: {self._db_path}")

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _conn(self):
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _setup_db(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)
        logger.debug("MessageBus DB schema ready.")

    # ── Core API ──────────────────────────────────────────────────────────────

    def publish(
        self,
        topic: str,
        message: Any,
        sender: str = "system",
    ) -> int:
        """
        Persist a message to the bus.

        Args:
            topic:   dot-separated routing key (supports fnmatch on consume)
            message: any JSON-serialisable payload
            sender:  agent_id or component name

        Returns:
            Row id of the inserted message.
        """
        payload_str = json.dumps(message, ensure_ascii=False, default=str)
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO messages (topic, sender, payload, created_at) VALUES (?,?,?,?)",
                (topic, sender, payload_str, time.time()),
            )
            row_id = cur.lastrowid
        logger.debug(f"MessageBus published → topic={topic} id={row_id}")

        # Wake the async dispatch loop if running
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon_threadsafe(
                    self._async_queue.put_nowait, (topic, message)
                )
        except Exception:
            pass
        return row_id

    # Async-friendly alias
    async def async_publish(self, topic: str, message: Any, sender: str = "system") -> int:
        return self.publish(topic, message, sender=sender)

    def consume(
        self,
        topic_pattern: str,
        limit: int = 50,
        mark_delivered: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetch pending messages matching *topic_pattern* (fnmatch wildcards).

        Args:
            topic_pattern:  e.g. "agent.coder.*" or "brain.store"
            limit:          max rows to return
            mark_delivered: if True, mark rows as 'delivered'

        Returns:
            List of message dicts with keys: id, topic, sender, payload, created_at
        """
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE status='pending' ORDER BY created_at LIMIT ?",
                (limit * 5,),  # over-fetch then filter by pattern
            ).fetchall()

        matched = [
            dict(r)
            for r in rows
            if fnmatch.fnmatch(r["topic"], topic_pattern)
        ][:limit]

        if matched and mark_delivered:
            ids = [m["id"] for m in matched]
            with self._conn() as conn:
                conn.execute(
                    f"UPDATE messages SET status='delivered', delivered_at=? "
                    f"WHERE id IN ({','.join('?' * len(ids))})",
                    [time.time()] + ids,
                )

        # Deserialise payloads
        for m in matched:
            try:
                m["payload"] = json.loads(m["payload"])
            except Exception:
                pass

        return matched

    def peek(self, topic_pattern: str = "*", limit: int = 20) -> List[Dict[str, Any]]:
        """Non-destructive read — does NOT mark as delivered."""
        return self.consume(topic_pattern, limit=limit, mark_delivered=False)

    def subscribe(self, topic_pattern: str, handler: Callable) -> None:
        """
        Register a callback (sync or async coroutine) for a topic pattern.
        Handlers are invoked by `process()`.

        Args:
            topic_pattern: fnmatch pattern, e.g. "agent.*.task"
            handler:       fn(topic: str, payload: Any)
        """
        if topic_pattern not in self._handlers:
            self._handlers[topic_pattern] = []
        self._handlers[topic_pattern].append(handler)
        logger.info(f"MessageBus: subscribed handler to '{topic_pattern}'")

    async def process(self, poll_interval: float = 0.1) -> None:
        """
        Async dispatch loop.  Blocks indefinitely.

        Pulls new messages from the in-process async queue AND polls
        the SQLite DB so that messages published by other processes are
        also dispatched.
        """
        logger.info("MessageBus dispatch loop started.")
        last_db_poll = 0.0

        while True:
            try:
                # 1. Drain the in-process async queue (non-blocking)
                while not self._async_queue.empty():
                    topic, payload = self._async_queue.get_nowait()
                    await self._dispatch(topic, payload)
                    self._async_queue.task_done()

                # 2. Poll SQLite for cross-process messages every second
                now = time.time()
                if now - last_db_poll >= 1.0:
                    pending = self.consume("*", limit=100)
                    for msg in pending:
                        await self._dispatch(msg["topic"], msg["payload"])
                    last_db_poll = now

                await asyncio.sleep(poll_interval)

            except Exception as exc:
                logger.error(f"MessageBus dispatch error: {exc}", exc_info=True)
                await asyncio.sleep(1)

    async def _dispatch(self, topic: str, payload: Any) -> None:
        """Match topic to all registered handlers and invoke them."""
        for pattern, handlers in self._handlers.items():
            if fnmatch.fnmatch(topic, pattern):
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(topic, payload)
                        else:
                            handler(topic, payload)
                    except Exception as e:
                        logger.error(
                            f"Handler error on topic '{topic}': {e}", exc_info=True
                        )

    # ── Admin ─────────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Return live bus statistics from the DB."""
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE status='pending'"
            ).fetchone()[0]
            delivered = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE status='delivered'"
            ).fetchone()[0]
            topics = conn.execute(
                "SELECT topic, COUNT(*) as cnt FROM messages GROUP BY topic ORDER BY cnt DESC LIMIT 10"
            ).fetchall()

        return {
            "db_path": self._db_path,
            "total_messages": total,
            "pending": pending,
            "delivered": delivered,
            "registered_patterns": list(self._handlers.keys()),
            "top_topics": [{"topic": r["topic"], "count": r["cnt"]} for r in topics],
        }

    def purge_delivered(self, older_than_s: float = 86400) -> int:
        """Remove delivered messages older than *older_than_s* seconds."""
        cutoff = time.time() - older_than_s
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM messages WHERE status='delivered' AND delivered_at < ?",
                (cutoff,),
            )
            deleted = cur.rowcount
        logger.info(f"MessageBus purge: removed {deleted} delivered message(s).")
        return deleted

    def dead_letter(self, message_id: int, reason: str = "") -> bool:
        """Mark a message as dead-letter so it won't be reprocessed."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE messages SET status='dead', payload=json_set(payload,'$.dead_reason',?) WHERE id=?",
                (reason, message_id),
            )
        return True
