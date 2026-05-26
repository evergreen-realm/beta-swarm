import sys
sys.path.insert(0, r"C:\Users\Admin\Documents\Beta Swarnv2")

from beta_swarm.agents.verify_registry import AGENT_MANIFEST, verify_and_register
from beta_swarm.brain.output_pipeline import OutputPipeline
from beta_swarm.brain.safe_query import SafeBrain

def test_agent(agent_id: str, brain):
    print(f"\n--- Testing {agent_id} ---")

    # 1. Registry check
    safe_brain = SafeBrain(brain=brain)
    agents = safe_brain.query_agents()
    found = [a for a in agents if a.get("id") == agent_id]
    reg_status = "PASS" if found else "FAIL"
    print(f"  Registry: {reg_status}")

    # 2. Vault file check
    import glob, os
    vault_dir = r"C:\Users\Admin\Documents\Beta Swarnv2\obsidian-vault\03-Agents"
    files = glob.glob(os.path.join(vault_dir, f"{agent_id}-*.md"))
    vault_status = "PASS" if files else "FAIL"
    print(f"  Vault file: {vault_status}")

    # 3. Output storage test
    pipeline = OutputPipeline(brain=brain)
    result = pipeline.store(agent_id, "test_output", f"Test output from {agent_id}", project="verification")
    db_status = "PASS" if "FAIL" not in result["db_status"] else "FAIL"
    print(f"  DB storage: {db_status}")

    # 4. Cache check
    cache_file = "beta_swarm/brain/output_cache.json"
    cache_status = "PASS" if os.path.exists(cache_file) else "FAIL"
    print(f"  Cache: {cache_status}")

    return all([reg_status == "PASS", vault_status == "PASS", db_status == "PASS", cache_status == "PASS"])

def main():
    print("=" * 60)
    print("BETA SWARM V3.2 — PER-AGENT VERIFICATION")
    print("=" * 60)

    # Initialize KuzuBrain ONCE to avoid lock contention
    try:
        from beta_swarm.brain.kuzu_manager import KuzuBrain
        # read_only=False so verify_and_register and store_artifact can write
        brain = KuzuBrain(read_only=False)
    except Exception as e:
        print(f"Failed to initialize KuzuBrain: {e}")
        brain = None

    # First, ensure registry
    print("\n[1/3] Ensuring all agents registered...")
    verify_and_register(brain=brain)

    # Test each agent
    print("\n[2/3] Testing each agent...")
    results = {}
    for agent in AGENT_MANIFEST:
        results[agent["id"]] = test_agent(agent["id"], brain=brain)

    # Summary
    print("\n[3/3] SUMMARY")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    print(f"PASS: {passed}/{len(AGENT_MANIFEST)}")
    print(f"FAIL: {failed}/{len(AGENT_MANIFEST)}")

    for aid, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  {aid}: {status}")

    if failed == 0:
        print("\nALL AGENTS VERIFIED. SWARM IS PRODUCTION-READY.")
    else:
        print(f"\n{failed} AGENTS NEED FIXING. Check logs above.")

    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
