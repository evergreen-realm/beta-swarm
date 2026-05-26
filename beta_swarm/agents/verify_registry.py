import os
import json
from datetime import datetime

AGENT_MANIFEST = [
    # Stage Agents (S1-S13)
    {"id": "s1", "name": "Ideation Agent", "stage": "S1", "function": "Breaks user request into structured tasks"},
    {"id": "s2", "name": "Research Agent", "stage": "S2", "function": "Researches patterns, libraries, and best practices"},
    {"id": "s3", "name": "PRD Agent", "stage": "S3", "function": "Writes Product Requirement Documents"},
    {"id": "s4", "name": "Architecture Agent", "stage": "S4", "function": "Designs system architecture and data models"},
    {"id": "s5", "name": "Backend Agent", "stage": "S5", "function": "Generates backend code and APIs"},
    {"id": "s6", "name": "API Agent", "stage": "S6", "function": "Designs and implements API endpoints"},
    {"id": "s7", "name": "Frontend Agent", "stage": "S7", "function": "Builds UI components and pages"},
    {"id": "s8", "name": "Testing Agent", "stage": "S8", "function": "Writes unit, integration, and E2E tests"},
    {"id": "s9", "name": "Deployment Agent", "stage": "S9", "function": "Creates Docker, CI/CD, and deploy configs"},
    {"id": "s10", "name": "Monitoring Agent", "stage": "S10", "function": "Sets up Prometheus, Grafana, and alerts"},
    {"id": "s11", "name": "Documentation Agent", "stage": "S11", "function": "Generates README, API docs, and guides"},
    {"id": "s12", "name": "Maintenance Agent", "stage": "S12", "function": "Dependency updates and security patches"},
    {"id": "s13", "name": "Design Agent", "stage": "S13", "function": "UI/UX polish and accessibility review"},
    # Brain Agents
    {"id": "b1", "name": "KuzuDB Manager", "stage": "BRAIN", "function": "Graph database operations"},
    {"id": "b2", "name": "Neo4j Manager", "stage": "BRAIN", "function": "Graph RAG and relationships"},
    {"id": "b3", "name": "Growth Agent", "stage": "GROWTH", "function": "Self-improvement and skill evolution"},
    {"id": "b4", "name": "Memory Consolidator", "stage": "BRAIN", "function": "Compresses and archives old memory"},
    {"id": "b5", "name": "Context Router", "stage": "BRAIN", "function": "Routes context between agents"},
    # Review / Sentry
    {"id": "r1", "name": "Code Review Agent", "stage": "REVIEW", "function": "Reviews code quality and patterns"},
    {"id": "r2", "name": "Security Audit Agent", "stage": "REVIEW", "function": "Scans for vulnerabilities"},
    {"id": "r3", "name": "Performance Agent", "stage": "REVIEW", "function": "Benchmarks and optimizes"},
    {"id": "se1", "name": "Bugsink Sentry", "stage": "SENTRY", "function": "Error tracking and alerting"},
    {"id": "se2", "name": "Health Monitor", "stage": "SENTRY", "function": "System health checks"},
    # Sub-agents / Tools
    {"id": "t1", "name": "GitNexus Indexer", "stage": "TOOLS", "function": "Codebase indexing and search"},
    {"id": "t2", "name": "GitNexus Risk Analyzer", "stage": "TOOLS", "function": "Security risk analysis"},
    {"id": "t3", "name": "OpenClaw Browser", "stage": "TOOLS", "function": "Web browsing and extraction"},
    {"id": "t4", "name": "Aider Adapter", "stage": "TOOLS", "function": "Coding assistant integration"},
    {"id": "t5", "name": "Goose Adapter", "stage": "TOOLS", "function": "Orchestration integration"},
    {"id": "t6", "name": "Hermes Adapter", "stage": "TOOLS", "function": "Nous Hermes integration"},
    {"id": "t7", "name": "Whisper STT", "stage": "TOOLS", "function": "Speech-to-text processing"},
    {"id": "t8", "name": "Edge-TTS", "stage": "TOOLS", "function": "Text-to-speech output"},
    {"id": "t9", "name": "API Router", "stage": "TOOLS", "function": "Provider fallback routing"},
    {"id": "t10", "name": "BitNet Runtime", "stage": "TOOLS", "function": "Quantized model inference"},
    {"id": "t11", "name": "MergeKit", "stage": "TOOLS", "function": "Model merging and fusion"},
    {"id": "t12", "name": "Speculative Decoder", "stage": "TOOLS", "function": "Draft model acceleration"},
]

def verify_and_register(brain=None):
    if brain is None:
        try:
            from beta_swarm.brain.kuzu_manager import KuzuBrain
            brain = KuzuBrain()
        except Exception as e:
            print(f"Failed to load KuzuBrain: {e}")
            brain = None

    results = []

    for agent in AGENT_MANIFEST:
        # 1. Check if exists in KuzuDB
        existing = 0
        if brain:
            try:
                rows = brain.query(f"MATCH (a:Agent {{id: '{agent['id']}'}}) RETURN count(a)")
                existing = rows[0][0] if rows else 0
            except:
                existing = 0

        if existing == 0 and brain:
            # Register in KuzuDB
            try:
                brain.add_agent(agent['id'], agent['name'], agent['stage'])
                status = "REGISTERED"
            except Exception as e:
                status = f"FAILED: {e}"
        else:
            status = "EXISTS" if brain else "FAILED: No DB"

        # 2. Create Obsidian vault entry
        vault_dir = r"C:\Users\Admin\Documents\Beta Swarnv2\obsidian-vault\03-Agents"
        os.makedirs(vault_dir, exist_ok=True)
        agent_file = os.path.join(vault_dir, f"{agent['id']}-{agent['name'].replace(' ', '_')}.md")

        if not os.path.exists(agent_file) or status == "REGISTERED":
            with open(agent_file, "w", encoding="utf-8") as f:
                f.write(f"# {agent['name']}\n\n")
                f.write(f"**ID:** `{agent['id']}`\n\n")
                f.write(f"**Stage:** {agent['stage']}\n\n")
                f.write(f"**Function:** {agent['function']}\n\n")
                f.write(f"**Status:** {status}\n\n")
                f.write(f"**Registered:** {datetime.now().isoformat()}\n\n")
                f.write("## Activity Log\n\n")
                f.write("- [ ] No activity yet\n\n")
                f.write("## Memory\n\n")
                f.write("- [ ] No memory stored\n\n")
                f.write("## Outputs\n\n")
                f.write("- [ ] No outputs generated\n\n")

        results.append({"agent": agent["id"], "status": status, "vault": agent_file})

    # 3. Update JSON cache
    cache_path = "beta_swarm/brain/agent_cache.json"
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(AGENT_MANIFEST, f, indent=2)

    return results

if __name__ == "__main__":
    results = verify_and_register()
    for r in results:
        print(f"{r['agent']}: {r['status']} | Vault: {r['vault']}")
    print(f"\nTotal: {len(results)} agents processed")
