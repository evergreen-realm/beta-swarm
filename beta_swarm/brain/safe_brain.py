import json
import os
import time
from beta_swarm.brain.kuzu_manager import KuzuBrain

class SafeBrain:
    def __init__(self):
        self.brain = None
        self.cache_file = "beta_swarm/brain/agent_cache.json"
        try:
            self.brain = KuzuBrain(read_only=True)
        except Exception as e:
            print(f"KuzuDB unavailable: {e}")
    
    def query_agents(self):
        if self.brain:
            try:
                # KuzuDB query() returns list of lists without pandas
                rows = self.brain.query("MATCH (a:Agent) RETURN a.id, a.name, a.stage, a.status")
                agents = [{"id": r[0], "name": r[1], "stage": r[2], "status": r[3]} for r in rows]
                if agents:
                    os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
                    with open(self.cache_file, 'w') as f:
                        json.dump(agents, f, indent=2)
                    return agents
            except Exception as e:
                print(f"KuzuDB query failed: {e}")
        
        # Fallback to cache
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except:
                pass
                
        # Fallback to hardcoded 36 agents
        return [
            {"id": "s1", "name": "Ideation Agent", "stage": "S1", "status": "idle"},
            {"id": "s2", "name": "Research Agent", "stage": "S2", "status": "idle"},
            {"id": "s3", "name": "PRD Agent", "stage": "S3", "status": "idle"},
            {"id": "s4", "name": "Architecture Agent", "stage": "S4", "status": "idle"},
            {"id": "s5", "name": "Backend Agent", "stage": "S5", "status": "idle"},
            {"id": "s6", "name": "API Agent", "stage": "S6", "status": "idle"},
            {"id": "s7", "name": "Frontend Agent", "stage": "S7", "status": "idle"},
            {"id": "s8", "name": "Testing Agent", "stage": "S8", "status": "idle"},
            {"id": "s9", "name": "Deployment Agent", "stage": "S9", "status": "idle"},
            {"id": "s10", "name": "Monitoring Agent", "stage": "S10", "status": "idle"},
            {"id": "s11", "name": "Documentation Agent", "stage": "S11", "status": "idle"},
            {"id": "s12", "name": "Maintenance Agent", "stage": "S12", "status": "idle"},
            {"id": "s13", "name": "Design Agent", "stage": "S13", "status": "idle"},
            {"id": "b1", "name": "KuzuDB Manager", "stage": "BRAIN", "status": "idle"},
            {"id": "b2", "name": "Neo4j Manager", "stage": "BRAIN", "status": "idle"},
            {"id": "b3", "name": "Growth Agent", "stage": "GROWTH", "status": "idle"},
            {"id": "b4", "name": "Memory Consolidator", "stage": "BRAIN", "status": "idle"},
            {"id": "b5", "name": "Context Router", "stage": "BRAIN", "status": "idle"},
            {"id": "r1", "name": "Code Review Agent", "stage": "REVIEW", "status": "idle"},
            {"id": "r2", "name": "Security Audit Agent", "stage": "REVIEW", "status": "idle"},
            {"id": "r3", "name": "Performance Agent", "stage": "REVIEW", "status": "idle"},
            {"id": "se1", "name": "Bugsink Sentry", "stage": "SENTRY", "status": "idle"},
            {"id": "se2", "name": "Health Monitor", "stage": "SENTRY", "status": "idle"},
            {"id": "t1", "name": "GitNexus Indexer", "stage": "TOOLS", "status": "idle"},
            {"id": "t2", "name": "GitNexus Risk Analyzer", "stage": "TOOLS", "status": "idle"},
            {"id": "t3", "name": "OpenClaw Browser", "stage": "TOOLS", "status": "idle"},
            {"id": "t4", "name": "Aider Adapter", "stage": "TOOLS", "status": "idle"},
            {"id": "t5", "name": "Goose Adapter", "stage": "TOOLS", "status": "idle"},
            {"id": "t6", "name": "Hermes Adapter", "stage": "TOOLS", "status": "idle"},
            {"id": "t7", "name": "Whisper STT", "stage": "TOOLS", "status": "idle"},
            {"id": "t8", "name": "Edge-TTS", "stage": "TOOLS", "status": "idle"},
            {"id": "t9", "name": "API Router", "stage": "TOOLS", "status": "idle"},
            {"id": "t10", "name": "BitNet Runtime", "stage": "TOOLS", "status": "idle"},
            {"id": "t11", "name": "MergeKit", "stage": "TOOLS", "status": "idle"},
            {"id": "t12", "name": "Speculative Decoder", "stage": "TOOLS", "status": "idle"},
        ]
    
    def query_artifacts(self, project=None):
        if not self.brain:
            return []
        try:
            q = "MATCH (a:Artifact) RETURN a.id, a.project, a.stage, a.data, a.created_at LIMIT 50"
            if project:
                q = f"MATCH (a:Artifact {{project: '{project}'}}) RETURN a.id, a.project, a.stage, a.data, a.created_at LIMIT 50"
            rows = self.brain.query(q)
            return [{"id": r[0], "project": r[1], "stage": r[2], "data": r[3], "created_at": r[4]} for r in rows]
        except:
            return []
    
    def store_artifact(self, agent_id, project, stage, data):
        # We need a writable brain instance here
        try:
            import datetime
            write_brain = KuzuBrain(read_only=False)
            aid = f"{agent_id}_{project}_{int(time.time())}"
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            write_brain.conn.execute(f"CREATE (a:Artifact {{id: '{aid}', project: '{project}', stage: '{stage}', data: '{data[:500]}', created_at: timestamp('{now_str}')}})")
            write_brain.conn.execute(f"MATCH (ag:Agent {{id: '{agent_id}'}}), (ar:Artifact {{id: '{aid}'}}) CREATE (ag)-[:GENERATED]->(ar)")
            return {"artifact_id": aid, "status": "stored"}
        except Exception as e:
            return {"error": str(e)}
