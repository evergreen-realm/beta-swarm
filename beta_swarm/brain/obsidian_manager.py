import os
import logging
from typing import List, Dict, Optional
import datetime

logger = logging.getLogger(__name__)

class ObsidianManager:
    """
    Manages interaction with a local Obsidian Vault (a directory of Markdown files).
    Allows the Beta Swarm to read, write, and search human-readable memories.
    """
    def __init__(self, vault_path: Optional[str] = None):
        # Default to OBSIDIAN_VAULT_PATH env var, or a local 'obsidian_vault' folder
        self.vault_path = vault_path or os.getenv("OBSIDIAN_VAULT_PATH", os.path.join(os.getcwd(), "obsidian_vault"))
        
        if not os.path.exists(self.vault_path):
            try:
                os.makedirs(self.vault_path, exist_ok=True)
                logger.info(f"Created new Obsidian vault directory at {self.vault_path}")
            except Exception as e:
                logger.error(f"Failed to create Obsidian vault directory: {e}")

        # Ensure a Swarm_Memories folder exists inside the vault
        self.memories_path = os.path.join(self.vault_path, "Swarm_Memories")
        os.makedirs(self.memories_path, exist_ok=True)

    def create_note(self, title: str, content: str, tags: List[str] = None, folder: str = "Swarm_Memories") -> bool:
        """Create a new markdown note in the vault."""
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
        if not safe_title:
            safe_title = "Untitled_Memory"
            
        # Note: folder parameter should now match canonical paths like "03-Brain/insights"
        target_dir = os.path.join(self.vault_path, folder)
        os.makedirs(target_dir, exist_ok=True)
        
        file_path = os.path.join(target_dir, f"{safe_title}.md")
        
        # Format frontmatter
        tags_str = "\n".join([f"  - {t}" for t in (tags or [])])
        frontmatter = f"---\ndate: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\ntags:\n{tags_str}\n---\n\n"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter + content)
            logger.info(f"Obsidian note created: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create Obsidian note {safe_title}: {e}")
            return False

    def append_to_daily_note(self, content: str) -> bool:
        """Append content to a daily note in the canonical path 00-Inbox/daily (e.g., 2026-05-14.md)."""
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        daily_notes_dir = os.path.join(self.vault_path, "00-Inbox", "daily")
        os.makedirs(daily_notes_dir, exist_ok=True)
        
        file_path = os.path.join(daily_notes_dir, f"{today_str}.md")
        
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        formatted_content = f"\n### {timestamp} - Beta Swarm Insight\n{content}\n"
        
        try:
            # If file doesn't exist, initialize with frontmatter
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"---\ndate: {today_str}\ntags:\n  - daily_note\n---\n\n# {today_str}\n")
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(formatted_content)
            return True
        except Exception as e:
            logger.error(f"Failed to append to daily note: {e}")
            return False

    def search_notes(self, query: str) -> List[Dict[str, str]]:
        """Basic text search across markdown files in the vault."""
        results = []
        for root, _, files in os.walk(self.vault_path):
            if ".obsidian" in root: # Skip hidden config folder
                continue
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if query.lower() in content.lower():
                                results.append({
                                    "title": file.replace('.md', ''),
                                    "path": file_path,
                                    "snippet": content[:200] + "..." # Just return start of note for context
                                })
                    except Exception:
                        continue
        return results

    def read_note(self, title: str) -> Optional[str]:
        """Read a specific note by title."""
        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if file == f"{title}.md":
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            return f.read()
                    except Exception:
                        return None
        return None
