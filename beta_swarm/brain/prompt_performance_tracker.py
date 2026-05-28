import sqlite3
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional

class PromptPerformanceTracker:
    def __init__(self, db_path: str = "C:/Users/Admin/Documents/Beta Swarnv2/brain_sqlite.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    task_type TEXT,
                    prompt_hash TEXT,
                    prompt_preview TEXT,
                    success BOOLEAN,
                    latency_ms REAL,
                    timestamp TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent ON prompt_logs(agent_id)")

    def log(self, agent_id: str, task_type: str, prompt: str, success: bool, latency: float):
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16]
        preview = prompt[:200]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO prompt_logs (agent_id, task_type, prompt_hash, prompt_preview, success, latency_ms, timestamp) VALUES (?,?,?,?,?,?,?)",
                (agent_id, task_type, prompt_hash, preview, int(success), latency * 1000, datetime.now().isoformat())
            )

    def get_underperforming_agents(self, threshold: float = 0.6) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                SELECT agent_id, 
                       AVG(CASE WHEN success=1 THEN 1.0 ELSE 0 END) as success_rate,
                       COUNT(*) as total_calls
                FROM prompt_logs
                GROUP BY agent_id
                HAVING success_rate < ?
            """, (threshold,))
            return [{"agent_id": row[0], "success_rate": row[1], "total_calls": row[2]} for row in cur.fetchall()]

    def get_best_prompts(self, agent_id: str, limit: int = 5) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                SELECT prompt_preview, COUNT(*) as uses
                FROM prompt_logs
                WHERE agent_id = ? AND success = 1
                GROUP BY prompt_hash
                ORDER BY uses DESC
                LIMIT ?
            """, (agent_id, limit))
            return [{"preview": row[0], "uses": row[1]} for row in cur.fetchall()]
