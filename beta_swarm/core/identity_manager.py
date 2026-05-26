# beta_swarm/core/identity_manager.py
import os
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class AgentIdentity:
    agent_id: str
    agent_name: str
    role: str
    project_id: str
    current_stage: str
    task_description: str
    decisions_made: List[str] = field(default_factory=list)
    context_summary: str = ""
    files_modified: List[str] = field(default_factory=list)
    git_commit_hash: str = ""
    neo4j_node_id: str = ""
    timestamp_created: str = ""
    timestamp_updated: str = ""
    status: str = "active"  # "active", "paused", "completed", "crashed"

class IdentityManager:
    def __init__(self, project_path: str = "C:/Users/Admin/Documents/Beta Swarnv2"):
        self.project_path = project_path
        self.identities_dir = os.path.join(self.project_path, "identities")

    def _get_path(self, agent_id: str, project_id: str) -> str:
        return os.path.join(self.identities_dir, project_id, f"{agent_id}_IDENTITY.md")

    def create_identity(self, agent_id: str, agent_name: str, role: str, project_id: str, task: str) -> AgentIdentity:
        timestamp = datetime.now().isoformat()
        identity = AgentIdentity(
            agent_id=agent_id, agent_name=agent_name, role=role, project_id=project_id,
            current_stage=agent_id, task_description=task, timestamp_created=timestamp,
            timestamp_updated=timestamp, status="active", decisions_made=["Session started"]
        )
        self._write_to_disk(identity)
        return identity

    def _write_to_disk(self, identity: AgentIdentity):
        filepath = self._get_path(identity.agent_id, identity.project_id)
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            decisions_str = "".join([f"- {d}\n" if (d.startswith("- ") or d.startswith("[")) else f"- [{datetime.now().isoformat()}] {d}\n" for d in identity.decisions_made])
            files_str = "".join([f"- {f}\n" for f in identity.files_modified]) or "- None yet\n"
            content = f"""# IDENTITY: {identity.agent_name}

**Agent ID:** {identity.agent_id}
**Role:** {identity.role}
**Project:** {identity.project_id}
**Status:** {identity.status}
**Created:** {identity.timestamp_created}
**Updated:** {identity.timestamp_updated}

## Current Task
{identity.task_description}

## Decisions Log
{decisions_str}
## Files Modified
{files_str}
## Context Summary
{identity.context_summary}

## State Links
- Git Commit: {identity.git_commit_hash}
- Neo4j Node: {identity.neo4j_node_id}

---
*This file is auto-updated by Beta Swarm IdentityManager*"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Failed to write identity to disk: {e}")

    def load_identity(self, agent_id: str, project_id: str) -> Optional[AgentIdentity]:
        filepath = self._get_path(agent_id, project_id)
        if not os.path.exists(filepath): return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            def get_val(pat, d="", flags=0):
                m = re.search(pat, content, flags)
                return m.group(1).strip() if m else d
            decisions, files = [], []
            m_dec = re.search(r"## Decisions Log\n(.*?)\n## Files Modified", content, re.DOTALL)
            if m_dec: decisions = [l.strip("- *").strip() for l in m_dec.group(1).strip().split("\n") if l.strip()]
            m_files = re.search(r"## Files Modified\n(.*?)\n## Context Summary", content, re.DOTALL)
            if m_files: files = [l.strip("- *").strip() for l in m_files.group(1).strip().split("\n") if l.strip() and l.strip("- *").strip().lower() != "none yet"]
            return AgentIdentity(
                agent_id=get_val(r"\*\*Agent ID:\*\*`?[ \t]*(.*)", agent_id),
                agent_name=get_val(r"# IDENTITY:[ \t]*(.*)", agent_id),
                role=get_val(r"\*\*Role:\*\*[ \t]*(.*)", "unknown"),
                project_id=get_val(r"\*\*Project:\*\*[ \t]*(.*)", project_id),
                current_stage=agent_id,
                task_description=get_val(r"## Current Task\n(.*?)\n## Decisions Log", "", re.DOTALL),
                decisions_made=decisions,
                context_summary=get_val(r"## Context Summary\n(.*?)\n## State Links", "", re.DOTALL),
                files_modified=files,
                git_commit_hash=get_val(r"-[ \t]*Git Commit:[ \t]*(.*)", ""),
                neo4j_node_id=get_val(r"-[ \t]*Neo4j Node:[ \t]*(.*)", ""),
                timestamp_created=get_val(r"\*\*Created:\*\*[ \t]*(.*)", ""),
                timestamp_updated=get_val(r"\*\*Updated:\*\*[ \t]*(.*)", ""),
                status=get_val(r"\*\*Status:\*\*[ \t]*(.*)", "active")
            )
        except Exception as e:
            print(f"Failed to load identity: {e}")
            return None

    def update_identity(self, agent_id: str, project_id: str, updates: Dict) -> AgentIdentity:
        identity = self.load_identity(agent_id, project_id)
        if not identity:
            identity = AgentIdentity(
                agent_id=agent_id, agent_name=agent_id, role="unknown", project_id=project_id,
                current_stage=agent_id, task_description="Automatic state", timestamp_created=datetime.now().isoformat()
            )
        for k, v in updates.items():
            if k == "decisions_made":
                for dec in v: identity.decisions_made.append(f"[{datetime.now().isoformat()}] {dec}")
            elif k == "files_modified":
                for f in v:
                    if f not in identity.files_modified: identity.files_modified.append(f)
            elif hasattr(identity, k):
                setattr(identity, k, v)
        identity.timestamp_updated = datetime.now().isoformat()
        self._write_to_disk(identity)
        return identity

    def restore_session(self, agent_id: str, project_id: str) -> Dict:
        identity = self.load_identity(agent_id, project_id)
        if not identity: return {"can_resume": False, "message": "No prior session found"}
        if identity.status == "completed": return {"can_resume": False, "message": "Session already completed"}
        if identity.status in ["crashed", "paused", "active"]:
            return {
                "can_resume": True, "last_task": identity.task_description, "decisions": identity.decisions_made,
                "files_modified": identity.files_modified, "git_commit": identity.git_commit_hash,
                "context": identity.context_summary, "message": "Session restored from IDENTITY.md"
            }
        return {"can_resume": False, "message": f"Session status is {identity.status}, no restore needed"}

    def mark_crashed(self, agent_id: str, project_id: str, error_info: str):
        self.update_identity(agent_id, project_id, {"status": "crashed", "decisions_made": [f"CRASH: {error_info}"]})

    def mark_completed(self, agent_id: str, project_id: str):
        self.update_identity(agent_id, project_id, {"status": "completed", "decisions_made": ["Session completed successfully"]})

    def list_active_identities(self, project_id: str) -> List[AgentIdentity]:
        active_list = []
        dirpath = os.path.join(self.identities_dir, project_id)
        if not os.path.exists(dirpath): return active_list
        try:
            for file in os.listdir(dirpath):
                if file.endswith("_IDENTITY.md"):
                    agent_id = file.replace("_IDENTITY.md", "")
                    identity = self.load_identity(agent_id, project_id)
                    if identity and identity.status != "completed": active_list.append(identity)
        except Exception as e:
            print(f"Failed to list active identities: {e}")
        return active_list

if __name__ == "__main__":
    im = IdentityManager()
    identity = im.create_identity("s5_backend", "Backend Agent", "coding", "test-001", "Build API")
    print(f"Created: {identity.agent_id} -> {identity.status}")
    im.update_identity("s5_backend", "test-001", {
        "decisions_made": ["Chose FastAPI over Flask"],
        "files_modified": ["main.py", "models.py"]
    })
    im.mark_crashed("s5_backend", "test-001", "OOM error")
    restore = im.restore_session("s5_backend", "test-001")
    print(f"Can resume: {restore['can_resume']}")
    print(f"Decisions: {restore['decisions']}")
