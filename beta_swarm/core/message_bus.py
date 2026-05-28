"""
SQLite Message Bus — Phase 2/3 inter-agent communication.
Agents can publish messages to named topics and subscribe/consume from them.
Thread-safe, persistent, WAL-mode SQLite with full pub/sub subscriptions.
"""
import sqlite3, json, time, uuid, logging, threading
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)
_BUS_PATH = "C:/Users/Admin/Documents/Beta Swarnv2/brain_message_bus.db"


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
            conn.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                callback_module TEXT NOT NULL,
                callback_name TEXT NOT NULL,
                created_at REAL,
                UNIQUE(agent_id, topic)
            )""")
        # In-memory registry: (agent_id, topic) -> (callback, thread, stop_event)
        self._subs: Dict[tuple, tuple] = {}
        self._subs_lock = threading.Lock()

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

    # ── Subscribe ────────────────────────────────────────────────────── #
    def subscribe(self, agent_id: str, topic: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe agent_id to topic; fires callback(payload) for each new message.
        Persists subscription to SQLite and starts a background polling thread.
        """
        key = (agent_id, topic)
        with self._subs_lock:
            if key in self._subs:
                logger.debug(f"[Bus] {agent_id} already subscribed to '{topic}'. Skipping.")
                return

            # Persist to DB
            sub_id = str(uuid.uuid4())
            cb_module = getattr(callback, "__module__", "__main__") or "__main__"
            cb_name = getattr(callback, "__qualname__", callback.__name__)
            conn = self._conn()
            try:
                with conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO subscriptions "
                        "(id, agent_id, topic, callback_module, callback_name, created_at) "
                        "VALUES (?,?,?,?,?,?)",
                        (sub_id, agent_id, topic, cb_module, cb_name, time.time())
                    )
            except Exception as e:
                logger.warning(f"[Bus] Could not persist subscription: {e}")

            # Start background listener thread
            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._listen_loop,
                args=(agent_id, topic, callback, stop_event),
                daemon=True,
                name=f"bus-listener-{agent_id}-{topic}"
            )
            self._subs[key] = (callback, thread, stop_event)
            thread.start()
            logger.info(f"[Bus] {agent_id} subscribed to '{topic}' (thread={thread.name})")

    # ── Unsubscribe ──────────────────────────────────────────────────── #
    def unsubscribe(self, agent_id: str, topic: str) -> None:
        """Stop the listener thread and remove the subscription."""
        key = (agent_id, topic)
        with self._subs_lock:
            entry = self._subs.pop(key, None)
        if entry:
            _, thread, stop_event = entry
            stop_event.set()
            thread.join(timeout=5)
            logger.info(f"[Bus] {agent_id} unsubscribed from '{topic}'")
        # Remove from DB
        conn = self._conn()
        try:
            with conn:
                conn.execute(
                    "DELETE FROM subscriptions WHERE agent_id=? AND topic=?",
                    (agent_id, topic)
                )
        except Exception as e:
            logger.warning(f"[Bus] Could not remove subscription from DB: {e}")

    # ── Background listener ──────────────────────────────────────────── #
    def _listen_loop(self, agent_id: str, topic: str,
                     callback: Callable, stop_event: threading.Event) -> None:
        """Polls the messages table every 2 s for pending messages on topic.
        When found, calls callback(payload) and marks message consumed.
        Runs until stop_event is set.
        """
        poll_interval = 2
        logger.debug(f"[Bus] Listener started: agent={agent_id} topic='{topic}'")
        while not stop_event.is_set():
            try:
                msg = self.consume(topic, consumer=agent_id)
                if msg:
                    try:
                        callback(msg["payload"])
                    except Exception as cb_err:
                        logger.error(
                            f"[Bus] Callback error for {agent_id}/{topic}: {cb_err}"
                        )
            except Exception as poll_err:
                logger.warning(f"[Bus] Poll error for {agent_id}/{topic}: {poll_err}")
            stop_event.wait(timeout=poll_interval)
        logger.debug(f"[Bus] Listener stopped: agent={agent_id} topic='{topic}'")
