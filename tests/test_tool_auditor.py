import os
import sys
import unittest
import shutil
from datetime import datetime

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from beta_swarm.core.tool_functionality_auditor import ToolFunctionalityAuditor

class TestToolAuditor(unittest.TestCase):
    def setUp(self):
        # Create a mock workspace directory
        self.mock_project = os.path.abspath("tests/mock_workspace")
        if os.path.exists(self.mock_project):
            shutil.rmtree(self.mock_project, ignore_errors=True)
            
        os.makedirs(self.mock_project, exist_ok=True)
        os.makedirs(os.path.join(self.mock_project, "beta_swarm/agents/stage"), exist_ok=True)
        os.makedirs(os.path.join(self.mock_project, "beta_swarm/adapters"), exist_ok=True)
        os.makedirs(os.path.join(self.mock_project, "beta_swarm/orchestration"), exist_ok=True)
        
        # Write dummy files to simulate agent calls
        with open(os.path.join(self.mock_project, "beta_swarm/agents/stage/s1_ideation.py"), "w") as f:
            f.write("# calls bitnet here\n")
            
        with open(os.path.join(self.mock_project, "beta_swarm/agents/stage/s5_levelcode.py"), "w") as f:
            f.write("# calls levelcode here\n")
            
        with open(os.path.join(self.mock_project, "beta_swarm/orchestrator.py"), "w") as f:
            f.write("# select_tool for choosing tools like aider, opencode\n")
            
        self.auditor = ToolFunctionalityAuditor(project_path=self.mock_project)

    def tearDown(self):
        if os.path.exists(self.mock_project):
            shutil.rmtree(self.mock_project, ignore_errors=True)

    def test_file_searching(self):
        called_bitnet = self.auditor._search_files(
            os.path.join(self.mock_project, "beta_swarm/agents/stage"), 
            r"s(1|4|8)_.*\.py", 
            "bitnet"
        )
        self.assertEqual(called_bitnet, ["s1_ideation.py"])
        
        called_levelcode = self.auditor._search_files(
            os.path.join(self.mock_project, "beta_swarm/agents/stage"),
            r"s5.*\.py",
            "levelcode"
        )
        self.assertEqual(called_levelcode, ["s5_levelcode.py"])

    def test_tool_checks_graceful_fail(self):
        # Tools will not be fully functional on a clean test runner without external binaries
        res = self.auditor.test_all()
        
        self.assertIn("bitnet", res)
        self.assertIn("levelcode", res)
        self.assertIn("opencode", res)
        self.assertIn("aider", res)
        self.assertIn("goose", res)
        
        # Checking mock integration strategy detection
        self.assertTrue(res["orchestrator_integration"]["strategy_detected"])
        
        # Check if report got written
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = os.path.join(self.mock_project, "obsidian-vault/Tool-Audit-Reports", f"{today}.md")
        self.assertTrue(os.path.exists(report_file))

if __name__ == "__main__":
    unittest.main()
