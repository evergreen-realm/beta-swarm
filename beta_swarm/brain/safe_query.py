import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

AGENT_BASELINE = [
    {"id": "s1", "name": "Ideation Agent", "status": "idle", "stage": "S1"},
    {"id": "s2", "name": "Research Agent", "status": "idle", "stage": "S2"},
    {"id": "s3", "name": "PRD Agent", "status": "idle", "stage": "S3"},
    {"id": "s4", "name": "Architecture Agent", "status": "idle", "stage": "S4"},
    {"id": "s5", "name": "Backend Agent", "status": "idle", "stage": "S5"},
    {"id": "s6", "name": "API Agent", "status": "idle", "stage": "S6"},
    {"id": "s7", "name": "Frontend Agent", "status": "idle", "stage": "S7"},
    {"id": "s8", "name": "Testing Agent", "status": "idle", "stage": "S8"},
    {"id": "s9", "name": "Deployment Agent", "status": "idle", "stage": "S9"},
    {"id": "s10", "name": "Monitoring Agent", "status": "idle", "stage": "S10"},
    {"id": "s11", "name": "Documentation Agent", "status": "idle", "stage": "S11"},
    {"id": "s12", "name": "Maintenance Agent", "status": "idle", "stage": "S12"},
    {"id": "s13", "name": "Design Agent", "status": "idle", "stage": "S13"},
    {"id": "b1", "name": "KuzuDB Manager", "status": "idle", "stage": "BRAIN"},
    {"id": "b2", "name": "Neo4j Manager", "status": "idle", "stage": "BRAIN"},
    {"id": "b3", "name": "Growth Agent", "status": "idle", "stage": "GROWTH"},
    {"id": "b4", "name": "Memory Consolidator", "status": "idle", "stage": "BRAIN"},
    {"id": "b5", "name": "Context Router", "status": "idle", "stage": "BRAIN"},
    {"id": "r1", "name": "Code Review Agent", "status": "idle", "stage": "REVIEW"},
    {"id": "r2", "name": "Security Audit Agent", "status": "idle", "stage": "REVIEW"},
    {"id": "r3", "name": "Performance Agent", "status": "idle", "stage": "REVIEW"},
    {"id": "se1", "name": "Bugsink Sentry", "status": "idle", "stage": "SENTRY"},
    {"id": "se2", "name": "Health Monitor", "status": "idle", "stage": "SENTRY"},
    {"id": "t1", "name": "GitNexus Indexer", "status": "idle", "stage": "TOOLS"},
    {"id": "t2", "name": "GitNexus Risk Analyzer", "status": "idle", "stage": "TOOLS"},
    {"id": "t3", "name": "OpenClaw Browser", "status": "idle", "stage": "TOOLS"},
    {"id": "t4", "name": "Aider Adapter", "status": "idle", "stage": "TOOLS"},
    {"id": "t5", "name": "Goose Adapter", "status": "idle", "stage": "TOOLS"},
    {"id": "t6", "name": "Hermes Adapter", "status": "idle", "stage": "TOOLS"},
    {"id": "t7", "name": "Whisper STT", "status": "idle", "stage": "TOOLS"},
    {"id": "t8", "name": "Edge-TTS", "status": "idle", "stage": "TOOLS"},
    {"id": "t9", "name": "API Router", "status": "idle", "stage": "TOOLS"},
    {"id": "t10", "name": "BitNet Runtime", "status": "idle", "stage": "TOOLS"},
    {"id": "t11", "name": "MergeKit", "status": "idle", "stage": "TOOLS"},
    {"id": "t12", "name": "Speculative Decoder", "status": "idle", "stage": "TOOLS"},
]

class SafeBrain:
    def __init__(self, brain=None):
        self.brain = brain
        self.cache_path = "beta_swarm/brain/agent_cache.json"
        if self.brain is None:
            try:
                from beta_swarm.brain.kuzu_manager import KuzuBrain
                self.brain = KuzuBrain(read_only=True)
            except Exception as e:
                logger.error(f"KuzuDB init failed: {e}")

    def query_agents(self) -> List[Dict]:
        result = self._query_kuzu()
        if result is None:
            result = self._query_cache()
        if not result:
            result = AGENT_BASELINE
        return result

    def _query_kuzu(self) -> Optional[List[Dict]]:
        if not self.brain:
            return None
        try:
            # Table Schema: id, name, role, stage. We map 'idle' as status.
            rows = self.brain.query("MATCH (a:Agent) RETURN a.id, a.name, 'idle' as status, a.stage")
            return [{"id": r[0], "name": r[1], "status": r[2], "stage": r[3]} for r in rows]
        except Exception as e:
            logger.warning(f"KuzuDB agent query failed: {e}")
            return None

    def _query_cache(self) -> Optional[List[Dict]]:
        try:
            with open(self.cache_path) as f:
                return json.load(f)
        except:
            return None
