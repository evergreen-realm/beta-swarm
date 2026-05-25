import os
import logging
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class B5ObsidianAgent(BaseAgent):
    """
    B5: Obsidian Vault Agent
    Brain: Human-Readable Memory
    Syncs brain memories and project progress into an Obsidian vault.
    """
    def __init__(self, brain=None):
        super().__init__("b5_obsidian", "Obsidian Vault Agent", "brain", brain)
        self.vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "./obsidian-vault")
        os.makedirs(self.vault_path, exist_ok=True)
        os.makedirs(os.path.join(self.vault_path, "Projects"), exist_ok=True)
        os.makedirs(os.path.join(self.vault_path, "Agents"), exist_ok=True)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        project_id = task.get("project_id", "default")
        stage_id = task.get("stage_id", "unknown")
        content = task.get("content", "")
        
        # 1. Update Project Note
        self._update_project_note(project_id, stage_id, content)
        
        # 2. Update Agent Log
        self._update_agent_log(stage_id, content)
        
        return {
            "status": "complete",
            "vault_path": self.vault_path,
            "updated": [f"Projects/{project_id}.md", f"Agents/{stage_id}.md"]
        }

    def _update_project_note(self, project_id: str, stage_id: str, content: str):
        path = os.path.join(self.vault_path, "Projects", f"{project_id}.md")
        header = f"# Project: {project_id}\n\n## Timeline\n"
        
        entry = f"### [{stage_id}] - {os.popen('date /t').read().strip()}\n{content}\n\n"
        
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(header + entry)
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(entry)

    def _update_agent_log(self, agent_id: str, content: str):
        path = os.path.join(self.vault_path, "Agents", f"{agent_id}.md")
        header = f"# Agent Activity: {agent_id}\n\n"
        
        entry = f"#### {os.popen('date /t').read().strip()} {os.popen('time /t').read().strip()}\n{content}\n---\n"
        
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(header + entry)
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(entry)
