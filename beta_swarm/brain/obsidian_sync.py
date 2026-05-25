# obsidian_sync.py - Obsidian Memory Vault Sync Worker
import os
import glob
import datetime
import re
import logging
from beta_swarm.brain.kuzu_manager import get_brain

logger = logging.getLogger("beta_swarm.obsidian_sync")

class ObsidianSync:
    def __init__(self, vault_path=None):
        self.vault_path = vault_path or r"C:\Users\Admin\Documents\Beta Swarnv2\obsidian-vault"
        self.daily_note_dir = os.path.join(self.vault_path, "00-Daily")
        self.agent_note_dir = os.path.join(self.vault_path, "01-Agents")

    def ensure_directories(self):
        try:
            os.makedirs(self.daily_note_dir, exist_ok=True)
            os.makedirs(self.agent_note_dir, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create Obsidian vault directories: {e}")
            return False

    def sync_to_daily_note(self, entry_text, agent_id=None):
        """Append a clean markdown log event containing WikiLinks directly into current Daily-Note"""
        if not self.ensure_directories():
            return False

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        daily_file = os.path.join(self.daily_note_dir, f"{today_str}.md")
        
        # Build note content
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        wiki_agent = f"[[{agent_id}]]" if agent_id else "[[swarm_watchdog]]"
        formatted_entry = f"- [{timestamp}] {wiki_agent}: {entry_text}\n"

        try:
            # Check if file exists, if not initialize template headers
            file_exists = os.path.exists(daily_file)
            with open(daily_file, "a", encoding="utf-8") as f:
                if not file_exists:
                    f.write(f"# Daily Note - {today_str}\n\n## Swarm Knowledge Feed\n\n")
                f.write(formatted_entry)
            logger.info(f"Successfully appended knowledge event to Obsidian daily note: {daily_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to write to Obsidian daily note: {e}")
            return False

    def sync_agent_note(self, agent_id, agent_name, status, role):
        """Create/Update structured agent definition profile in Obsidian vault"""
        if not self.ensure_directories():
            return False

        agent_file = os.path.join(self.agent_note_dir, f"{agent_id}.md")
        
        content = f"""# Agent Profile: {agent_name}

## Metadata
- **ID:** {agent_id}
- **Role:** {role}
- **Current Status:** {status}
- **Last Synced:** {datetime.datetime.now().isoformat()}

## Related Abstractions
- [[letta_memory]]
- [[kuzu_db]]

## Recent Synthesis Notes
- Integrated into Swarm Roster. Running core lifecycle loops.
"""
        try:
            with open(agent_file, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to write agent note: {e}")
            return False

    def pull_recent_timeline(self, limit=30):
        """Query vault directory files and compile timelines"""
        entries = []
        if not os.path.exists(self.daily_note_dir):
            return entries

        files = sorted(glob.glob(os.path.join(self.daily_note_dir, "*.md")), reverse=True)[:limit]
        for f in files:
            try:
                date_str = os.path.basename(f).replace(".md", "")
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()
                
                # Strip title headers to show clean entries
                body = re.sub(r"# Daily Note.*\n\n## Swarm Knowledge Feed\n\n", "", content).strip()
                if body:
                    entries.append({
                        "date": date_str,
                        "preview": body,
                        "path": f
                    })
            except Exception as e:
                logger.error(f"Failed to read daily note {f}: {e}")
        return entries

# Global Sync Instance
obsidian_sync = ObsidianSync()
