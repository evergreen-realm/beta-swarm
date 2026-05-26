import sys
import os
import json

# Add root to sys.path (parent of beta_swarm)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from beta_swarm.agents.health.h5_ram_governor import H5RamGovernorAgent

def test_h5():
    agent = H5RamGovernorAgent()
    
    print("--- TEST 1: Check Capacity ---")
    cap = agent.execute({"action": "check_capacity"})
    print(json.dumps(cap, indent=2))
    
    print("\n--- TEST 2: Transition to S1 (Ideation) ---")
    # S1 needs Letta, traefik, core, bitnet-2b, whisper-cpp, etc.
    # It should STOP Neo4j, Cognee, etc.
    res1 = agent.execute({"action": "transition_to_stage", "stage": "S1"})
    print(f"S1 Result: {res1['status']}")
    print(f"Active Containers: {res1['active']['containers']}")
    
    print("\n--- TEST 3: Transition to S2 (Research) ---")
    # S2 needs Neo4j, Cognee, Graphiti, qwen-14b
    res2 = agent.execute({"action": "transition_to_stage", "stage": "S2"})
    print(f"S2 Result: {res2['status']}")
    print(f"Active Containers: {res2['active']['containers']}")

    print("\n--- TEST 4: Emergency Purge ---")
    res3 = agent.execute({"action": "emergency_purge"})
    print(f"Purge Result: {res3['status']}")

if __name__ == "__main__":
    test_h5()
