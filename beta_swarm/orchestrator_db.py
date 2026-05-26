import json
import sqlite3
import uuid
from typing import Optional


class OrchestratorDB:
    def __init__(self, db_path: str = "beta_swarm/orchestrator_state.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS workflow_runs (
                run_id        TEXT PRIMARY KEY,
                project_id    TEXT NOT NULL,
                current_stage TEXT DEFAULT '',
                status        TEXT DEFAULT 'pending',
                context_json  TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS stage_runs (
                run_id        TEXT NOT NULL,
                stage_id      TEXT NOT NULL,
                status        TEXT DEFAULT 'pending',
                output_json   TEXT DEFAULT '{}',
                error_json    TEXT DEFAULT '{}',
                attempt_count INTEGER DEFAULT 0,
                PRIMARY KEY (run_id, stage_id),
                FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id)
            );
        """)
        self.conn.commit()

    def create_run(self, project_id: str, context: dict) -> str:
        run_id = uuid.uuid4().hex
        self.conn.execute(
            "INSERT INTO workflow_runs (run_id, project_id, context_json) VALUES (?, ?, ?)",
            (run_id, project_id, json.dumps(context)),
        )
        self.conn.commit()
        return run_id

    def get_run(self, project_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM workflow_runs WHERE project_id = ? ORDER BY rowid DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def update_stage(
        self,
        run_id: str,
        stage_id: str,
        status: str,
        output: Optional[dict] = None,
        error: Optional[dict] = None,
    ):
        self.conn.execute(
            """
            INSERT INTO stage_runs (run_id, stage_id, status, output_json, error_json, attempt_count)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(run_id, stage_id) DO UPDATE SET
                status        = excluded.status,
                output_json   = excluded.output_json,
                error_json    = excluded.error_json,
                attempt_count = attempt_count + 1
            """,
            (
                run_id,
                stage_id,
                status,
                json.dumps(output or {}),
                json.dumps(error or {}),
            ),
        )
        self.conn.commit()

    def get_stage_status(self, run_id: str, stage_id: str) -> str:
        row = self.conn.execute(
            "SELECT status FROM stage_runs WHERE run_id = ? AND stage_id = ?",
            (run_id, stage_id),
        ).fetchone()
        if row is None:
            return "not_started"
        return row["status"]
