from beta_swarm.brain.sqlite_brain import get_brain
import datetime

def init_schema():
    # Schema creation is now handled internally by KuzuBrain's new SQLite emulator `_init_schema()`
    brain = get_brain(read_only=False)
    print("Schema initialized via SQLite engine.")

def seed_agents():
    brain = get_brain(read_only=False)
    agents = [
        # Stage agents — IDs must match pipeline.py and dashboard agent_cache keys
        ("s1_ideation","Ideation Agent","S1"), ("s2_research","Research Agent","S2"),
        ("s3_prd","PRD Agent","S3"), ("s4_architecture","Architecture Agent","S4"),
        ("s5_backend","Backend Agent","S5"), ("s6_api","API Agent","S6"),
        ("s7_frontend_huashu","Frontend Agent","S7"), ("s8_testing","Testing Agent","S8"),
        ("s9_deployment","Deployment Agent","S9"), ("s10_monitoring","Monitoring Agent","S10"),
        ("s11_documentation","Documentation Agent","S11"), ("s12_maintenance","Maintenance Agent","S12"),
        ("s13_design","Design Agent","S13"),
        # Brain agents
        ("b1_local_brain","KuzuDB Manager","BRAIN"), ("b2_global_brain","Neo4j Manager","BRAIN"),
        ("b3_evolver","Growth Agent","GROWTH"), ("b4_code_intel","Memory Consolidator","BRAIN"),
        # Review agents
        ("x1_code_review","Code Review Agent","REVIEW"), ("x2_security_review","Security Audit Agent","REVIEW"),
        ("x3_performance_review","Performance Agent","REVIEW"), ("x4_review_board","Review Board","REVIEW"),
        # Sentry / Health
        ("sentry","Bugsink Sentry","SENTRY"), ("g1_health_monitor","Health Monitor","HEALTH"),
        ("g2_business_domain","Business Domain Agent","GROWTH"), ("g3_reflection","Reflection Agent","GROWTH"),
        ("g4_research_cloud","Research Cloud Agent","GROWTH"),
        # Tools
        ("t1_web_scraper", "Web Scraper", "TOOLS"), ("t2_github", "Github Integration", "TOOLS"),
        ("t3_vscode", "VS Code Bridge", "TOOLS"), ("t4_figma", "Figma Exporter", "TOOLS"),
        ("t5_docker", "Docker Deployer", "TOOLS"), ("t6_db_migrator", "DB Migrator", "TOOLS"),
        ("t7_vercel", "Vercel SDK", "TOOLS"), ("t8_stripe", "Stripe Connect", "TOOLS"),
        ("t9_api_router", "API Router", "TOOLS"), ("t10_bitnet", "BitNet Runtime", "TOOLS"),
        ("t11_mergekit", "MergeKit", "TOOLS"), ("t12_speculative", "Speculative Decoder", "TOOLS"),
    ]
    
    for aid, name, stage in agents:
        res = brain.register_agent(aid, name, stage)
        if res.get("status") == "success":
            print(f"SEEDED: {aid}")
        else:
            print(f"ERROR: {res.get('message')}")

if __name__ == "__main__":
    init_schema()
    seed_agents()
    print("Schema ready")
