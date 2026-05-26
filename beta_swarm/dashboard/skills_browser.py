import os
import yaml
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SkillsBrowser:
    """Scans and manages the installed Beta Swarm skills."""
    
    def __init__(self, skills_dir: str = None):
        self.skills_dir = skills_dir or os.path.join(os.getcwd(), "skills")

    def list_skills(self) -> List[Dict[str, Any]]:
        """Scan the skills directory for SKILL.md files."""
        skills = []
        if not os.path.exists(self.skills_dir):
            # Try searching up if in dashboard subdir
            self.skills_dir = os.path.join(os.path.dirname(os.getcwd()), "skills")
            if not os.path.exists(self.skills_dir):
                return []

        for item in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(skill_path):
                md_path = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(md_path):
                    skills.append(self._parse_skill(item, md_path))
        
        return skills

    def install_from_github(self, repo_url: str) -> Dict[str, Any]:
        """Clone a remote skill repository into the local skills/ directory."""
        import subprocess
        try:
            folder_name = repo_url.split("/")[-1].replace(".git", "")
            target_path = os.path.join(self.skills_dir, folder_name)
            
            if os.path.exists(target_path):
                return {"status": "error", "message": "Skill already installed."}
            
            logger.info(f"Installing skill from {repo_url}...")
            result = subprocess.run(["git", "clone", repo_url, target_path], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Try to install dependencies if requirements.txt exists
                req_path = os.path.join(target_path, "requirements.txt")
                if os.path.exists(req_path):
                    subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path])
                
                return {"status": "success", "id": folder_name}
            else:
                return {"status": "error", "message": result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _parse_skill(self, folder_name: str, md_path: str) -> Dict[str, Any]:
        """Extract name and description from SKILL.md frontmatter."""
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Basic YAML frontmatter extraction
                match = re.search(r"---(.*?)---", content, re.DOTALL)
                if match:
                    data = yaml.safe_load(match.group(1))
                    return {
                        "id": folder_name,
                        "name": data.get("name", folder_name),
                        "description": data.get("description", "No description available."),
                        "path": md_path
                    }
        except Exception as e:
            logger.error(f"Error parsing skill {folder_name}: {e}")
            
        return {"id": folder_name, "name": folder_name, "description": "Parsing failed."}

import re # Needed for the _parse_skill regex
