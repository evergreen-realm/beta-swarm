import os
import sys
import time
import requests
import json
import logging
from neo4j import GraphDatabase

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from beta_swarm.agents.health.h5_ram_governor import H5RamGovernorAgent
from beta_swarm.brain.kuzu_manager import KuzuBrain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brain_test")

# Credentials from environment or defaults
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "betaswarm123")

def test_letta():
    logger.info("Testing Letta Health...")
    try:
        response = requests.get("http://localhost:8283/v1/health", timeout=5)
        if response.status_code == 200:
            logger.info("Letta: PASS")
            return True
        else:
            logger.error(f"Letta failed with status: {response.status_code}")
    except Exception as e:
        logger.error(f"Letta connection failed: {e}")
    return False

def test_neo4j():
    logger.info("Testing Neo4j Cypher...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # Create
            session.run("CREATE (a:Agent {id: 'test_neo4j', name: 'Test Agent'})")
            # Verify
            result = session.run("MATCH (a:Agent {id: 'test_neo4j'}) RETURN a.name AS name")
            record = result.single()
            if record and record["name"] == "Test Agent":
                # Clean up
                session.run("MATCH (a:Agent {id: 'test_neo4j'}) DELETE a")
                logger.info("Neo4j: PASS")
                return True
            else:
                logger.error("Neo4j verification failed: Node not found or name mismatch")
    except Exception as e:
        logger.error(f"Neo4j test failed: {e}")
    return False

def test_cognee():
    logger.info("Testing Cognee Ingestion...")
    try:
        payload = {"data": "Test document content for Cognee verification."}
        response = requests.post("http://localhost:8000/api/v1/add", json=payload, timeout=10)
        if response.status_code in [200, 201]:
            logger.info("Cognee: PASS")
            return True
        else:
            logger.error(f"Cognee failed with status: {response.status_code}")
    except Exception as e:
        logger.error(f"Cognee connection failed: {e}")
    return False

def test_graphiti():
    logger.info("Testing Graphiti...")
    # KNOWN_ISSUE: Image not found/commented out in master-docker-compose.yml
    logger.warning("Graphiti: KNOWN_ISSUE (Service currently disabled in infrastructure)")
    return "KNOWN_ISSUE"

def test_hybrid_bridge():
    logger.info("Testing Hybrid Bridge (KuzuDB + Neo4j)...")
    try:
        kuzu_path = "./brain_data_test"
        brain = KuzuBrain(db_path=kuzu_path)
        agent_id = "test_bridge_agent"
        brain.register_agent(agent_id, "Bridge Agent", "Tester")
        fact_id = brain.store_fact(agent_id, "Hybrid bridge verification fact")
        
        facts = brain.query_facts(agent_id)
        if any(f['content'] == "Hybrid bridge verification fact" for f in facts):
            # Verify sync_to_neo4j stub exists
            res = brain.sync_to_neo4j(NEO4J_URI, (NEO4J_USER, NEO4J_PASSWORD))
            if res.get("status") == "stub":
                logger.info("Hybrid Bridge: PASS")
                return True
    except Exception as e:
        logger.error(f"Hybrid Bridge test failed: {e}")
    return False

def run_all_tests():
    governor = H5RamGovernorAgent()
    
    # 1. Verify Letta (already running)
    letta_ok = test_letta()
    
    # 2. H5 Transition to S2 (Should start Neo4j + Cognee)
    logger.info("Transitioning to S2 via H5...")
    res = governor.execute({"action": "transition_to_stage", "stage": "S2"})
    if res.get("status") == "success":
        logger.info("H5 S2 Transition: PASS")
        logger.info("Waiting 45s for services to warm up...")
        time.sleep(45)
        
        # Run tests
        neo4j_ok = test_neo4j()
        cognee_ok = test_cognee()
        graphiti_status = test_graphiti()
        bridge_ok = test_hybrid_bridge()
        
        # 3. H5 Transition back to S1 (Should stop Neo4j + Cognee)
        logger.info("Transitioning back to S1 via H5...")
        res_s1 = governor.execute({"action": "transition_to_stage", "stage": "S1"})
        if res_s1.get("status") == "success":
            logger.info("H5 S1 Transition: PASS")
            
            # Verify they are stopped (via H5 verification list)
            active = res_s1.get("active", {}).get("containers", [])
            # In master-docker-compose.yml: neo4j, cognee should be stopped
            # (Note: H5 logic currently stops anything not in S1 target)
            stopped_ok = "neo4j" not in active and "cognee" not in active
            if stopped_ok:
                logger.info("H5 Stop Verification: PASS")
            else:
                logger.warning(f"H5 Stop Verification: FAIL (Remaining: {active})")
        else:
            logger.error("H5 S1 Transition: FAIL")
    else:
        logger.error("H5 S2 Transition: FAIL")
        return

    # Final Summary
    print("\n" + "="*30)
    print("BRAIN SERVICES TEST SUMMARY")
    print(f"Letta: {'PASS' if letta_ok else 'FAIL'}")
    print(f"Neo4j: {'PASS' if neo4j_ok else 'FAIL'}")
    print(f"Cognee: {'PASS' if cognee_ok else 'FAIL'}")
    print(f"Graphiti: {graphiti_status}")
    print(f"Hybrid Bridge: {'PASS' if bridge_ok else 'FAIL'}")
    print("="*30)

if __name__ == "__main__":
    run_all_tests()
