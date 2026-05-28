import os
import datetime
import logging

logger = logging.getLogger(__name__)

class ObsidianLogger:
    """Logs swarm actions to the Obsidian daily notes."""
    
    def __init__(self, vault_path: str = None):
        self.vault_path = vault_path or os.getenv("OBSIDIAN_VAULT_PATH", r"c:\Users\Admin\Documents\Beta Swarnv2\obsidian-vault")
        self.daily_notes_dir = os.path.join(self.vault_path, "00-Daily")
        os.makedirs(self.daily_notes_dir, exist_ok=True)

    def log_action(self, action: str, agent_id: str = "SYSTEM", status: str = "OK"):
        """Append an entry to today's daily note."""
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        
        file_path = os.path.join(self.daily_notes_dir, f"{date_str}.md")
        entry = f"- [{time_str}] ACTION: {action} | AGENT: {agent_id} | STATUS: {status}\n"
        
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.error(f"Failed to log to Obsidian: {e}")

    def generate_summary(self):
        """Placeholder for 24hr summary generation."""
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        file_path = os.path.join(self.daily_notes_dir, f"{date_str}.md")
        
        summary = "\n## Swarm 24hr Summary\n- Total tasks: [Simulated]\n- Status: Healthy\n"
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(summary)
        except Exception:
            pass
