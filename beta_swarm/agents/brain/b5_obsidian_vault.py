import logging
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent
from beta_swarm.brain.obsidian_manager import ObsidianManager

logger = logging.getLogger(__name__)

class B5ObsidianVaultAgent(BaseAgent):
    """
    B5: Obsidian Vault Agent
    Brain: Human-Readable Memory Interface
    Allows the swarm to search, read, and write memories into the user's Obsidian Vault.
    """
    def __init__(self, brain=None):
        super().__init__("b5_obsidian", "Obsidian Vault Agent", "brain", brain)
        self.obsidian = ObsidianManager()

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        operation = task.get("operation", "search")
        
        try:
            if operation == "search":
                query = task.get("query", "")
                results = self.obsidian.search_notes(query)
                return {"status": "complete", "results": results}
                
            elif operation == "read":
                title = task.get("title", "")
                content = self.obsidian.read_note(title)
                if content:
                    return {"status": "complete", "content": content}
                return {"status": "error", "message": f"Note '{title}' not found."}
                
            elif operation == "write":
                title = task.get("title", "Beta Swarm Insight")
                content = task.get("content", "")
                tags = task.get("tags", ["beta_swarm", "insight"])
                fact_type = task.get("type", "insight")
                
                # Canonical mapping
                folder_map = {
                    "insight": "03-Brain/insights",
                    "research": "04-Research",
                    "error": "05-Errors",
                    "agent_config": "02-Agents",
                    "api_doc": "06-APIs",
                    "template": "07-Templates",
                    "daily": "00-Inbox/daily",
                    "project": "01-Projects"
                }
                folder = folder_map.get(fact_type, "03-Brain/insights")
                
                success = self.obsidian.create_note(title, content, tags, folder=folder)
                return {"status": "complete" if success else "error", "message": "Note created." if success else "Failed to create note."}
                
            elif operation == "log_daily":
                content = task.get("content", "")
                success = self.obsidian.append_to_daily_note(content)
                return {"status": "complete" if success else "error", "message": "Logged to daily note." if success else "Failed to log."}
                
            else:
                return {"status": "error", "message": f"Unknown operation: {operation}"}
                
        except Exception as e:
            logger.error(f"[B5] Obsidian operation failed: {e}")
            return {"status": "error", "message": str(e)}
