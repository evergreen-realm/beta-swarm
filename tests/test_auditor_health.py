import os
import sys
import sqlite3
import unittest
import shutil
from datetime import datetime
from typing import Dict, Any

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from beta_swarm.brain.cognee_client import CogneeClient
from beta_swarm.brain.letta_client import LettaClient
from beta_swarm.core.agent_auditor import AgentAuditor

class TestAuditorHealth(unittest.TestCase):
    def setUp(self):
        self.cognee = CogneeClient(base_url="http://localhost:8000")
        self.letta = LettaClient(base_url="http://localhost:8283")
        
        # Set up a test SQLite DB for the auditor
        self.test_db = "tests/test_auditor_db.db"
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass
            
        with sqlite3.connect(self.test_db) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS artifact_log (
                    artifact_id TEXT PRIMARY KEY,
                    artifact_type TEXT,
                    project_id TEXT,
                    source_agent TEXT,
                    content_hash TEXT,
                    content_preview TEXT,
                    timestamp TEXT
                )
            """)
            # Seed one active agent and one tool usage
            cur.execute("""
                INSERT OR REPLACE INTO artifact_log (artifact_id, artifact_type, project_id, source_agent, content_preview, timestamp)
                VALUES ('art1', 'prd', 'proj1', 's1_ideation', 'This uses bitnet and opencode.', '2026-05-20T20:00:00Z')
            """)
            
        self.auditor = AgentAuditor(db_path=self.test_db)
        self.auditor.checkpoints_dir = "tests/test_checkpoints"
        self.auditor.vault_dir = "tests/test_vault"
        os.makedirs(self.auditor.checkpoints_dir, exist_ok=True)
        os.makedirs(self.auditor.vault_dir, exist_ok=True)

    def tearDown(self):
        # Clean up database connections and delete database file
        try:
            sqlite3.connect(self.test_db).close()
        except Exception:
            pass
        
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass
                
        # clean test directories
        if os.path.exists("tests/test_vault"):
            shutil.rmtree("tests/test_vault", ignore_errors=True)
        if os.path.exists("tests/test_checkpoints"):
            shutil.rmtree("tests/test_checkpoints", ignore_errors=True)

    def test_cognee_health_fallback(self):
        hc = self.cognee.health_check()
        self.assertIn("status", hc)
        self.assertIn("reachable", hc)
        self.assertFalse(hc["reachable"])

    def test_letta_health_fallback(self):
        hc = self.letta.health_check()
        self.assertIn("status", hc)
        self.assertIn("reachable", hc)
        self.assertFalse(hc["reachable"])
        
        flush_res = self.letta.flush_to_neo4j()
        self.assertEqual(flush_res.get("status"), "error")

    def test_agent_auditor_operations(self):
        registered = self.auditor.get_all_registered_agents()
        self.assertEqual(len(registered), 36)
        self.assertIn("s1_ideation", registered)
        self.assertIn("h5_ram", registered)
        
        active = self.auditor.get_active_agents(since_days=30)
        self.assertIn("s1_ideation", active)
        self.assertEqual(len(active), 1)
        
        dormant = self.auditor.get_dormant_agents(since_days=30)
        self.assertEqual(len(dormant), 35) # 36 - 1 active
        
        tools = self.auditor.confirm_tool_usage()
        self.assertTrue(tools["bitnet"])
        self.assertTrue(tools["opencode"])
        self.assertFalse(tools["aider"])
        
        report = self.auditor.generate_report()
        self.assertIn("Total Registered Agents", report)
        self.assertIn("s1_ideation", report)
        self.assertIn("- **Bitnet**: ✅ Active", report)
        
        # Verify file written to test vault
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = os.path.join(self.auditor.vault_dir, "Agent-Audit-Reports", f"{today}.md")
        self.assertTrue(os.path.exists(report_file))


if __name__ == "__main__":
    unittest.main()

