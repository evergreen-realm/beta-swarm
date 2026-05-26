import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from beta_swarm.agents.stage.s1_ideation import S1IdeationAgent
from beta_swarm.agents.stage.s2_research import S2ResearchAgent
from beta_swarm.agents.stage.s3_prd import S3PRDAgent
from beta_swarm.agents.stage.s4_architecture import S4ArchitectureAgent

import shutil

def test_pipeline():
    if os.path.exists("checkpoints"):
        shutil.rmtree("checkpoints")
    # S1: Ideation
    s1 = S1IdeationAgent()
    concept = s1.run({"input": "Build a habit tracker app for iOS with React and Python. It should track daily habits, and should show progress charts."})
    assert concept["status"] == "complete"
    assert "habit tracker" in concept["concept"]["title"].lower()
    assert "react" in concept["concept"]["tech_stack_hints"]
    assert "python" in concept["concept"]["tech_stack_hints"]
    print(f"S1 PASS: {concept['concept']['title']}")

    # S2: Research
    s2 = S2ResearchAgent()
    research = s2.run({"concept": concept["concept"]})
    assert research["status"] == "complete"
    assert len(research["sources"]) > 0
    print(f"S2 PASS: {len(research['sources'])} sources found")

    # S3: PRD
    s3 = S3PRDAgent()
    prd = s3.run({"concept": concept["concept"], "research_summary": research["research_summary"]})
    assert prd["status"] == "complete"
    assert "metadata" in prd["prd"]
    assert "functional_requirements" in prd["prd"]
    assert len(prd["prd"]["user_stories"]) > 0
    print(f"S3 PASS: PRD generated with {len(prd['prd']['functional_requirements'])} FRs")

    # S4: Architecture
    s4 = S4ArchitectureAgent()
    arch = s4.run({"prd": prd["prd"]})
    assert arch["status"] == "complete"
    assert len(arch["architecture"]["components"]) >= 4
    assert len(arch["architecture"]["data_flow"]) > 0
    print(f"S4 PASS: {len(arch['architecture']['components'])} components designed")

    print("\nS1-S4 Pipeline: ALL PASS")

if __name__ == "__main__":
    test_pipeline()
