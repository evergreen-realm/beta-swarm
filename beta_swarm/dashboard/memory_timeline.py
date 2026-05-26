import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MemoryTimeline:
    """Reads project history and decisions from the Obsidian vault."""
    
    def __init__(self, vault_path: str = None):
        self.vault_path = vault_path or os.getenv("OBSIDIAN_VAULT_PATH", "./obsidian-vault")

    def get_timeline_entries(self) -> List[Dict[str, Any]]:
        """Scan daily notes and project files for a chronological view."""
        entries = []
        if not os.path.exists(self.vault_path):
            logger.warning(f"Obsidian vault not found at {self.vault_path}")
            return []

        # Walk through files
        for root, dirs, files in os.walk(self.vault_path):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                    
                    entries.append({
                        "id": file,
                        "title": file.replace(".md", ""),
                        "date": date_str,
                        "timestamp": mtime,
                        "path": file_path,
                        "summary": self._extract_summary(file_path)
                    })
        
        # Sort by timestamp descending
        entries.sort(key=lambda x: x["timestamp"], reverse=True)
        return entries[:20] # Last 20 entries

    def _extract_summary(self, file_path: str) -> str:
        """Extract a short summary from the markdown content."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(500)
                # Strip frontmatter if present
                content = re.sub(r"---.*?---", "", content, flags=re.DOTALL)
                # Strip markdown symbols
                content = re.sub(r"[#*`>\[\]]", "", content)
                return content.strip()[:100] + "..."
        except Exception:
            return "No summary available."

if __name__ == "__main__":
    timeline = MemoryTimeline()
    for entry in timeline.get_timeline_entries():
        print(f"{entry['date']} | {entry['title']}")
