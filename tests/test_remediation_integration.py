# tests/test_remediation_integration.py
import sys
import os
sys.path.insert(0, r"C:\Users\Admin\Documents\Beta Swarnv2")

import shutil
import tempfile
import unittest
import asyncio
from unittest.mock import MagicMock, patch

from beta_swarm.core.remediation_engine import RemediationEngine

class TestRemediationIntegration(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for simulated project
        self.test_dir = tempfile.mkdtemp()
        self.project_id = "test-remediation-project"
        
        # Create a dummy file with issues
        self.risky_file_path = os.path.join(self.test_dir, "risky.py")
        with open(self.risky_file_path, "w", encoding="utf-8") as f:
            f.write("import sys\nimport os\n\ndef main():\n    print('Hello World')\n")
            
        # Create dummy main.py
        self.main_file_path = os.path.join(self.test_dir, "main.py")
        with open(self.main_file_path, "w", encoding="utf-8") as f:
            f.write("print('Main')\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_extract_fix_tasks_priority(self):
        """Verify that issues are extracted correctly and sorted by severity."""
        engine = RemediationEngine()
        
        mock_review = {
            "consensus": "block",
            "x1_code_review": {
                "pass": False,
                "issues": [
                    {"message": "unused import 'sys'", "severity": "medium", "file": "risky.py"}
                ]
            },
            "x2_security": {
                "pass": False,
                "findings": [
                    {"message": "hardcoded api key", "severity": "critical", "file": "risky.py"}
                ]
            },
            "x3_performance": {
                "pass": False,
                "findings": [
                    {"message": "slow loop", "severity": "high", "file": "risky.py"}
                ]
            }
        }
        
        tasks = engine._extract_fix_tasks(mock_review)
        
        # Verify extraction and sorting (critical first, then high, then medium)
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0]["severity"], "critical")
        self.assertEqual(tasks[1]["severity"], "high")
        self.assertEqual(tasks[2]["severity"], "medium")
        
        self.assertEqual(tasks[0]["file"], "risky.py")
        self.assertEqual(tasks[1]["file"], "risky.py")
        self.assertEqual(tasks[2]["file"], "risky.py")

    @patch("beta_swarm.orchestration.aider_manager.AiderManager.code")
    @patch("beta_swarm.core.remediation_engine.RemediationEngine._run_sentry_recheck")
    @patch("beta_swarm.core.remediation_engine.RemediationEngine._run_review_recheck")
    def test_process_block_resolution_loop(self, mock_review_recheck, mock_sentry_recheck, mock_aider_code):
        """Test the process_block async engine resolves the issues on successful re-check."""
        # 1. Setup mock returns for aider code call, sentry and review board rechecks
        mock_aider_code.return_value = {"status": "complete", "stdout": "fixed", "stderr": ""}
        mock_sentry_recheck.return_value = {"all_gates_passed": True, "gate_results": {}}
        mock_review_recheck.return_value = {
            "consensus": "pass", 
            "x1_code_review": {"pass": True, "issues": []}, 
            "x2_security": {"pass": True, "findings": []}, 
            "x3_performance": {"pass": True, "findings": []}
        }
        
        # 2. Initialize RemediationEngine with mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.project_id = self.project_id
        mock_orchestrator.project_path = self.test_dir
        # Mock adapters to not interfere
        mock_orchestrator.adapters = {}
        
        engine = RemediationEngine(orchestrator=mock_orchestrator, max_retries=2)
        
        mock_review = {
            "consensus": "block",
            "x1_code_review": {
                "pass": False,
                "issues": [
                    {"message": "unused import 'sys'", "severity": "medium", "file": "risky.py"}
                ]
            }
        }
        
        # 3. Process block (will use AwaitableDict and execute _process_block_async)
        context = {"project_id": self.project_id, "project_path": self.test_dir}
        result = engine.process_block(mock_review, context)
        
        # Resolve AwaitableDict if run in active loop or directly
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
        elif hasattr(result, "_coro_func") and len(result) == 0:
            result = asyncio.run(result._coro_func(*result._args, **result._kwargs))
            
        # 4. Assertions
        self.assertEqual(result.get("status"), "resolved")
        self.assertEqual(result.get("attempts"), 1)
        self.assertEqual(result.get("fixes_applied"), 1)
        
        # Verify the mock aider call was made
        mock_aider_code.assert_called_once()

    @patch("beta_swarm.orchestration.aider_manager.AiderManager.code")
    @patch("beta_swarm.core.remediation_engine.RemediationEngine._run_sentry_recheck")
    @patch("beta_swarm.core.remediation_engine.RemediationEngine._run_review_recheck")
    def test_process_block_exhausted_retries(self, mock_review_recheck, mock_sentry_recheck, mock_aider_code):
        """Test that remediation engine exhausts retries and returns failed if issues persist."""
        mock_aider_code.return_value = {"status": "complete", "stdout": "fixed", "stderr": ""}
        mock_sentry_recheck.return_value = {"all_gates_passed": False, "gate_results": {}}
        
        # The recheck should continue returning consensus: block with issues to trigger another retry
        mock_review_recheck.return_value = {
            "consensus": "block",
            "x1_code_review": {
                "pass": False,
                "issues": [
                    {"message": "unused import 'sys'", "severity": "medium", "file": "risky.py"}
                ]
            },
            "x2_security": {"pass": True},
            "x3_performance": {"pass": True}
        }
        
        mock_orchestrator = MagicMock()
        mock_orchestrator.project_id = self.project_id
        mock_orchestrator.project_path = self.test_dir
        mock_orchestrator.adapters = {}
        
        engine = RemediationEngine(orchestrator=mock_orchestrator, max_retries=2)
        
        mock_review = {
            "consensus": "block",
            "x1_code_review": {
                "pass": False,
                "issues": [
                    {"message": "unused import 'sys'", "severity": "medium", "file": "risky.py"}
                ]
            }
        }
        
        context = {"project_id": self.project_id, "project_path": self.test_dir}
        result = engine.process_block(mock_review, context)
        
        if asyncio.iscoroutine(result):
            result = asyncio.run(result)
        elif hasattr(result, "_coro_func") and len(result) == 0:
            result = asyncio.run(result._coro_func(*result._args, **result._kwargs))
            
        self.assertEqual(result.get("status"), "failed")
        self.assertEqual(result.get("attempts"), 2)
        self.assertEqual(mock_aider_code.call_count, 2)

if __name__ == "__main__":
    unittest.main()
