import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PersistenceManager:
    """Manager for maintaining IDENTITY.md and project state."""
    
    def __init__(self, workspace_root: str = "."):
        self.root = workspace_root
        self.state_file = os.path.join(self.root, ".beta_swarm_state.json")
        self.identity_file = os.path.join(self.root, "IDENTITY.md")
        self.state = self._load_initial_state()
        
    def _load_initial_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        return {}

    def save_state(self, key: str, value: Any):
        self.state[key] = value
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"Persisted state for {key}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
        
    def load_state(self, key: str) -> Any:
        return self.state.get(key)

    def update_identity(self, project_name: str, objective: str, version: str = "3.1"):
        """Update the IDENTITY.md file for the current project."""
        content = f"""# Project Identity: {project_name}
        
## Objective
{objective}

## Swarm Version
Beta Swarm v{version}

## Status
Active

## Last Updated
{os.path.getmtime(self.state_file) if os.path.exists(self.state_file) else "Just now"}
"""
        try:
            with open(self.identity_file, "w") as f:
                f.write(content)
            logger.info(f"Updated {self.identity_file}")
        except Exception as e:
            logger.error(f"Failed to update identity: {e}")
