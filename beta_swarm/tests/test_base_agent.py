import sys
import os

# Add root to sys.path to allow importing beta_swarm
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import tempfile
from beta_swarm.agents.base import BaseAgent, AgentState

class MockAgent(BaseAgent):
    def execute(self, task):
        if task.get("fail"):
            raise ValueError("Simulated failure")
        return {"status": "complete", "result": task.get("input", "done")}

def test_checkpoint_and_recovery():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            agent = MockAgent("test_01", "Test Agent", "Testing")
            
            # Run a task
            result = agent.run({"input": "hello"})
            assert result["status"] == "complete"
            assert result["result"] == "hello"
            
            # Verify checkpoint exists
            checkpoints = os.listdir("./checkpoints/test_01")
            assert len(checkpoints) >= 1
            
            # Simulate crash: create new agent instance, call recover
            agent2 = MockAgent("test_01", "Test Agent", "Testing")
            recovered = agent2.recover()
            assert recovered is not None, "Recover returned None"
            assert recovered["status"] == "complete"
            
            print("PASS: Checkpoint and recovery work")
        finally:
            os.chdir(cwd)

def test_idempotency_key():
    agent = MockAgent("test_02", "Test Agent", "Testing")
    key1 = agent._generate_idempotency_key({"a": 1, "b": 2})
    key2 = agent._generate_idempotency_key({"b": 2, "a": 1})
    assert key1 == key2, "Idempotency key must be order-independent"
    print("PASS: Idempotency keys are deterministic")

def test_error_handling():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            agent = MockAgent("test_03", "Test Agent", "Testing")
            
            try:
                agent.run({"fail": True})
                assert False, "Should have raised"
            except ValueError:
                pass
            
            # Verify error was checkpointed
            assert agent.state.status == "error"
            assert agent.state.error_count == 1
            assert agent.state.checkpoint_data is not None
            
            print("PASS: Error handling and checkpointing work")
        finally:
            os.chdir(cwd)

if __name__ == "__main__":
    test_checkpoint_and_recovery()
    test_idempotency_key()
    test_error_handling()
    print("\nAll BaseAgent tests passed!")
