"""E2E Test for the 13-stage Swarm Pipeline."""

import unittest
import sys
import os

# Ensure root in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from beta_swarm.pipeline import SwarmPipeline

class TestE2EPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = SwarmPipeline()
        self.project_name = "TestE2EFlask"

    def test_full_sequential_run(self):
        """Asserts that all 13 stages complete successfully for a standard task."""
        initial_task = "Build a Flask todo API"
        result = self.pipeline.run(initial_task, self.project_name)
        
        # Verify all 13 stages exist
        self.assertEqual(len(result["stages"]), 13, "Pipeline did not reach all 13 stages")
        
        # Assert each stage completed
        for stage in result["stages"]:
            with self.subTest(stage=stage["stage"]):
                self.assertEqual(stage["status"], "complete", f"Stage {stage['stage']} failed with {stage.get('error')}")
                self.assertGreater(stage["duration"], 0, f"Stage {stage['stage']} reported invalid timing")

if __name__ == "__main__":
    unittest.main()
