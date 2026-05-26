import os
import sys
import tempfile
import shutil
import unittest

# Add root to sys.path to allow importing beta_swarm
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from beta_swarm.core.identity_manager import IdentityManager, AgentIdentity

class TestIdentityManager(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for testing to avoid polluting actual project identities
        self.temp_dir = tempfile.mkdtemp()
        self.im = IdentityManager(project_path=self.temp_dir)

    def tearDown(self):
        # Cleanup temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_load_identity(self):
        # Create identity
        identity = self.im.create_identity(
            agent_id="s5_backend",
            agent_name="Backend Agent",
            role="coding",
            project_id="proj-123",
            task="Design API endpoints"
        )
        
        self.assertEqual(identity.agent_id, "s5_backend")
        self.assertEqual(identity.agent_name, "Backend Agent")
        self.assertEqual(identity.role, "coding")
        self.assertEqual(identity.project_id, "proj-123")
        self.assertEqual(identity.status, "active")
        
        # Verify IDENTITY.md was created
        expected_path = os.path.join(self.temp_dir, "identities", "proj-123", "s5_backend_IDENTITY.md")
        self.assertTrue(os.path.exists(expected_path))
        
        # Load and parse identity from disk
        loaded = self.im.load_identity("s5_backend", "proj-123")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.agent_id, "s5_backend")
        self.assertEqual(loaded.agent_name, "Backend Agent")
        self.assertEqual(loaded.role, "coding")
        self.assertEqual(loaded.project_id, "proj-123")
        self.assertEqual(loaded.task_description.strip(), "Design API endpoints")
        self.assertEqual(loaded.status, "active")
        self.assertTrue(any("Session started" in d for d in loaded.decisions_made))
        self.assertEqual(loaded.files_modified, [])

    def test_update_identity(self):
        # Create
        self.im.create_identity("s5_backend", "Backend Agent", "coding", "proj-123", "Design API")
        
        # Update decisions and files modified
        self.im.update_identity("s5_backend", "proj-123", {
            "decisions_made": ["Selected FastAPI framework", "Added SQLite support"],
            "files_modified": ["main.py", "database.py"],
            "git_commit_hash": "abc123commit",
            "neo4j_node_id": "node-456"
        })
        
        # Load and check updates
        loaded = self.im.load_identity("s5_backend", "proj-123")
        self.assertEqual(loaded.git_commit_hash, "abc123commit")
        self.assertEqual(loaded.neo4j_node_id, "node-456")
        self.assertIn("main.py", loaded.files_modified)
        self.assertIn("database.py", loaded.files_modified)
        
        # Check decisions log
        decisions_text = " ".join(loaded.decisions_made)
        self.assertIn("Session started", decisions_text)
        self.assertIn("Selected FastAPI framework", decisions_text)
        self.assertIn("Added SQLite support", decisions_text)

    def test_mark_crashed_and_restore(self):
        self.im.create_identity("s5_backend", "Backend Agent", "coding", "proj-123", "Design API")
        
        # Mark crashed
        self.im.mark_crashed("s5_backend", "proj-123", "Connection pool exhausted")
        
        # Verify status is crashed
        loaded = self.im.load_identity("s5_backend", "proj-123")
        self.assertEqual(loaded.status, "crashed")
        decisions_text = " ".join(loaded.decisions_made)
        self.assertIn("CRASH: Connection pool exhausted", decisions_text)
        
        # Restore session
        restore = self.im.restore_session("s5_backend", "proj-123")
        self.assertTrue(restore["can_resume"])
        self.assertEqual(restore["last_task"].strip(), "Design API")
        self.assertIn("Session restored from IDENTITY.md", restore["message"])

    def test_mark_completed(self):
        self.im.create_identity("s5_backend", "Backend Agent", "coding", "proj-123", "Design API")
        
        # Mark completed
        self.im.mark_completed("s5_backend", "proj-123")
        
        # Verify status is completed
        loaded = self.im.load_identity("s5_backend", "proj-123")
        self.assertEqual(loaded.status, "completed")
        
        # Restore should fail
        restore = self.im.restore_session("s5_backend", "proj-123")
        self.assertFalse(restore["can_resume"])
        self.assertEqual(restore["message"], "Session already completed")

    def test_list_active_identities(self):
        # Create completed identity
        self.im.create_identity("s1", "Agent 1", "role1", "proj-123", "Task 1")
        self.im.mark_completed("s1", "proj-123")
        
        # Create active identity
        self.im.create_identity("s2", "Agent 2", "role2", "proj-123", "Task 2")
        
        # Create crashed identity
        self.im.create_identity("s3", "Agent 3", "role3", "proj-123", "Task 3")
        self.im.mark_crashed("s3", "proj-123", "Memory leak")
        
        # List active
        active = self.im.list_active_identities("proj-123")
        agent_ids = [a.agent_id for a in active]
        
        # Completed should not be in the list, active and crashed should be
        self.assertNotIn("s1", agent_ids)
        self.assertIn("s2", agent_ids)
        self.assertIn("s3", agent_ids)
        self.assertEqual(len(active), 2)

if __name__ == "__main__":
    unittest.main()
