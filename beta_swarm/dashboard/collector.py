import os
import psutil
import docker
import time
import logging
from typing import Dict, Any, List
from beta_swarm.brain.kuzu_manager import KuzuBrain
from beta_swarm.tools.api_stack.router import router

from beta_swarm.dashboard.memory_timeline import MemoryTimeline
from beta_swarm.dashboard.skills_browser import SkillsBrowser

logger = logging.getLogger(__name__)

class SwarmCollector:
    """Collects real-time metrics and status from the Beta Swarm ecosystem."""
    
    def __init__(self):
        self.kuzu = KuzuBrain(read_only=True)
        self.timeline = MemoryTimeline()
        self.skills = SkillsBrowser()
        try:
            self.docker_client = docker.from_env()
        except Exception:
            self.docker_client = None
            logger.warning("Docker client not available. Container monitoring disabled.")

    def get_system_vitals(self) -> Dict[str, float]:
        """CPU, RAM, Disk usage."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }

    def get_docker_status(self) -> List[Dict[str, str]]:
        """Status of swarm containers."""
        if not self.docker_client:
            return [{"name": "Docker N/A", "status": "offline"}]
        
        containers = []
        try:
            for container in self.docker_client.containers.list(all=True):
                # Filter for beta_swarm related containers
                if "beta_swarm" in container.name or any("swarm" in t for t in container.labels):
                    containers.append({
                        "name": container.name,
                        "status": container.status,
                        "image": container.image.tags[0] if container.image.tags else "unknown"
                    })
        except Exception as e:
            logger.error(f"Error fetching docker containers: {e}")
            
        return containers if containers else [{"name": "No Swarm Containers", "status": "idle"}]

    def get_agent_status(self) -> List[Dict[str, Any]]:
        """Retrieve agent statuses from KuzuDB."""
        # We query the ExecutionRecord and Agent tables
        cypher = """
        MATCH (a:Agent)
        OPTIONAL MATCH (a)-[:PRODUCED]->(art:Artifact)
        RETURN a.id, a.name, a.role, a.stage, count(art) as artifact_count
        """
        agents = []
        try:
            rows = self.kuzu.query(cypher)
            for row in rows:
                agents.append({
                    "id": row[0],
                    "name": row[1],
                    "role": row[2],
                    "stage": row[3],
                    "artifacts": row[4],
                    "status": "idle" # Default until real-time bus integrated
                })
        except Exception as e:
            logger.error(f"Error fetching agent statuses: {e}")
            
        return agents

    def get_pipeline_progress(self) -> Dict[str, Any]:
        """Current state of the S1-S13 pipeline."""
        cypher = "MATCH (e:ExecutionRecord) RETURN e.stage, e.status, e.duration ORDER BY e.stage"
        try:
            rows = self.kuzu.query(cypher)
            completed = [row[0] for row in rows if row[1] == "complete"]
            return {
                "completed_stages": completed,
                "current_stage": completed[-1] if completed else "s1_ideation",
                "progress_percent": (len(completed) / 13) * 100
            }
        except Exception:
            return {"completed_stages": [], "current_stage": "idle", "progress_percent": 0}

    def get_router_health(self) -> Dict[str, Any]:
        """Health of LLM providers."""
        return router.get_status()

    def predict_completion_time(self) -> Dict[str, Any]:
        """Predict remaining pipeline time based on historical execution records."""
        try:
            # Query average duration per stage
            cypher = "MATCH (e:ExecutionRecord) RETURN e.stage, avg(e.duration)"
            rows = self.kuzu.query(cypher)
            avg_durations = {row[0]: row[1] for row in rows}
            
            # Identify remaining stages
            progress = self.get_pipeline_progress()
            completed = set(progress["completed_stages"])
            all_stages = [f"s{i}" for i in range(1, 14)] # Simplified stage IDs
            remaining = [s for s in all_stages if s not in completed]
            
            # Sum up predicted time
            total_predicted = sum(avg_durations.get(s, 300) for s in remaining) # Default 5m per stage
            return {
                "remaining_seconds": total_predicted,
                "eta_minutes": round(total_predicted / 60, 1),
                "confidence": "medium" if avg_durations else "low"
            }
        except Exception:
            return {"remaining_seconds": 0, "eta_minutes": 0, "confidence": "n/a"}

    def get_full_snapshot(self) -> Dict[str, Any]:
        """Consolidated snapshot for UI updates."""
        return {
            "timestamp": time.time(),
            "system": self.get_system_vitals(),
            "docker": self.get_docker_status(),
            "agents": self.get_agent_status(),
            "pipeline": self.get_pipeline_progress(),
            "router": self.get_router_health(),
            "timeline": self.timeline.get_timeline_entries(),
            "skills": self.skills.list_skills(),
            "prediction": self.predict_completion_time()
        }


