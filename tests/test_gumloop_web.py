import os
import sys
import unittest
from typing import Dict, Any

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from beta_swarm.orchestration.gumloop_web import GumloopWebManager
from beta_swarm.agents.stage.s2_research import S2ResearchAgent

class TestGumloopWeb(unittest.TestCase):
    def setUp(self):
        self.manager = GumloopWebManager(project_path="C:/Users/Admin/Documents/Beta Swarnv2")

    def test_structured_findings_extraction(self):
        raw_text = """
        Research Results:
        We found some details at https://github.com/google/research and https://example.com/api
        They are using React, FastAPI, Python, and Redis for this implementation.
        These technologies are standard.
        """
        parsed = self.manager.extract_structured_findings(raw_text)
        
        self.assertIn("findings", parsed)
        self.assertEqual(len(parsed["sources"]), 2)
        self.assertIn("React", parsed["technologies"])
        self.assertIn("FastAPI", parsed["technologies"])
        self.assertIn("Python", parsed["technologies"])
        self.assertIn("Redis", parsed["technologies"])
        self.assertGreaterEqual(parsed["confidence"], 0.7)

    def test_run_research_fallback(self):
        # Without credentials set, this should fallback to DDG search and return findings
        os.environ.pop("GUMLOOP_EMAIL", None)
        os.environ.pop("GUMLOOP_PASSWORD", None)
        
        result = self.manager.run_research("FastAPI web development best practices", depth="quick")
        self.assertIsNotNone(result)
        self.assertIn("findings", result)
        self.assertIsInstance(result["sources"], list)
        self.assertIsInstance(result["technologies"], list)

    def test_s2_agent_fallback_chain(self):
        agent = S2ResearchAgent()
        task = {
            "project_id": "test-project-gumloop",
            "concept": {
                "title": "Simple API webapp",
                "key_features": ["User login", "Database storage"]
            }
        }
        res = agent.execute(task)
        self.assertEqual(res.get("status"), "complete")
        self.assertIn("research_summary", res)
        self.assertIn("sources", res)

if __name__ == "__main__":
    unittest.main()
