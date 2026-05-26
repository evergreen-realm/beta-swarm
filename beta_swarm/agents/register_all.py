#!/usr/bin/env python3
"""Register all 36 agents in the KuzuDB brain with schema verification."""

import os
import sys
import logging

# Ensure project root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from beta_swarm.brain.kuzu_manager import KuzuBrain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AGENTS = [
    # Stage Agents (13)
    ("s1_ideation", "Ideation Agent", "Stage 1: Input Processing"),
    ("s2_research", "Research Agent", "Stage 2: Deep Research"),
    ("s3_prd", "PRD Agent", "Stage 3: Product Requirements"),
    ("s4_architecture", "Architecture Agent", "Stage 4: System Design"),
    ("s5_backend", "Backend Agent", "Stage 5: Backend Development"),
    ("s6_api", "API Integration Agent", "Stage 6: API Integration"),
    ("s7_frontend", "Frontend Agent", "Stage 7: Frontend Generation"),
    ("s8_testing", "Testing Agent", "Stage 8: Quality Assurance"),
    ("s9_deployment", "Deployment Agent", "Stage 9: Deployment"),
    ("s10_monitoring", "Monitoring Agent", "Stage 10: Observability"),
    ("s11_docs", "Documentation Agent", "Stage 11: Documentation"),
    ("s12_maintenance", "Maintenance Agent", "Stage 12: Maintenance"),
    ("s13_design", "Design Agent", "Stage 13: Visual Design"),
    # Review Agents (4)
    ("x1_review", "Code Review Agent", "Review: Structural Analysis"),
    ("x2_security", "Security Review Agent", "Review: Security Audit"),
    ("x3_performance", "Performance Review Agent", "Review: Performance"),
    ("x4_board", "Review Board", "Review: Multi-Agent Consensus"),
    # Brain Agents (5)
    ("b1_local", "LocalBrainAgent", "Brain: KuzuDB Management"),
    ("b2_global", "GlobalBrainAgent", "Brain: Neo4j Management"),
    ("b3_evolver", "EvolverAgent", "Brain: Self-Evolution"),
    ("b4_intel", "CodeIntelAgent", "Brain: Structural Awareness"),
    ("b5_obsidian", "B5ObsidianAgent", "Brain: Human-Readable Memory"),
    # Growth Agents (4)
    ("g1_health", "HealthMonitorAgent", "Growth: System Health"),
    ("g2_domain", "BusinessDomainAgent", "Growth: Domain Logic"),
    ("g3_reflection", "ReflectionAgent", "Growth: Self-Correction"),
    ("g4_cloud", "CloudResearchAgent", "Growth: Cloud Offload"),
    # Sentry (1)
    ("sentry", "SentryLayerAgent", "Security: Triple Gate"),
    # Health Agents (5)
    ("h1_resource", "H1ResourceMonitorAgent", "Health: Passive Metrics"),
    ("h2_model", "H2ModelHealthAgent", "Health: LLM Status"),
    ("h3_service", "H3ServiceHealthAgent", "Health: Service Status"),
    ("h4_reboot", "H4AutoRebootAgent", "Health: Emergency Recovery"),
    ("h5_ram", "H5RamGovernorAgent", "Health: Memory Limiter"),
    # Utility Agents (4)
    ("u1_scrape", "WebScrapingBrainAgent", "Utility: Content Extraction"),
    ("u2_annotate", "AutoAnnotationAgent", "Utility: Entity Extraction"),
    ("u3_git", "GitSyncAgent", "Utility: Version Control"),
    ("u4_docs", "DocumentationAgent", "Utility: Docs Generation"),
]

def register_all():
    brain = KuzuBrain(read_only=False)
    
    registered = 0
    failed = 0
    for agent_id, name, role in AGENTS:
        try:
            res = brain.register_agent(agent_id, name, role)
            if res.get("status") == "success":
                print(f"[Register] \u2713 {agent_id}: {name}")
                registered += 1
            else:
                print(f"[Register] \u2717 {agent_id}: FAILED - {res.get('message')}")
                failed += 1
        except Exception as e:
            print(f"[Register] \u2717 {agent_id}: FAILED - {e}")
            failed += 1
            
    print(f"\n[Register] Total: {registered}/{len(AGENTS)} registered, {failed} failed")
    return {"registered": registered, "failed": failed, "total": len(AGENTS)}

if __name__ == "__main__":
    result = register_all()
    sys.exit(0 if result["failed"] == 0 else 1)
