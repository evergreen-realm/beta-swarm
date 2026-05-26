from beta_swarm.agents.base import BaseAgent
from typing import Dict, Any
import subprocess
import os

class GitSyncAgent(BaseAgent):
    def __init__(self, brain=None):
        super().__init__("u3_git", "Git Sync", "Utility: Version Control", brain)

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        repo_path = task.get("repo_path", ".")
        action = task.get("action", "status")

        # IMPROVEMENT: Use cwd=repo_path in subprocess instead of os.chdir()
        # os.chdir() changes the current working directory for the entire Python process,
        # which can cause hard-to-debug errors in a multi-agent or asynchronous system.
        if not os.path.exists(repo_path):
            return {"status": "error", "message": f"Path does not exist: {repo_path}"}

        if action == "status":
            result = subprocess.run(["git", "status", "--short"], cwd=repo_path, capture_output=True, text=True)
            return {"status": "complete", "changes": result.stdout.strip().split("\n") if result.stdout.strip() else []}
        elif action == "commit":
            subprocess.run(["git", "add", "-A"], cwd=repo_path, capture_output=True)
            result = subprocess.run(["git", "commit", "-m", task.get("message", "Beta Swarm auto-commit")], cwd=repo_path, capture_output=True, text=True)
            return {"status": "complete", "committed": result.returncode == 0, "output": result.stdout}
        elif action == "push":
            result = subprocess.run(["git", "push", "origin", task.get("branch", "main")], cwd=repo_path, capture_output=True, text=True)
            return {"status": "complete", "pushed": result.returncode == 0, "output": result.stdout}
        elif action == "pull":
            result = subprocess.run(["git", "pull", "origin", task.get("branch", "main")], cwd=repo_path, capture_output=True, text=True)
            return {"status": "complete", "pulled": result.returncode == 0, "output": result.stdout}
        elif action == "diff":
            result = subprocess.run(["git", "diff", "--stat"], cwd=repo_path, capture_output=True, text=True)
            return {"status": "complete", "diff": result.stdout}
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

# Alias for compatibility with compliance checks and testing
U3GitSyncAgent = GitSyncAgent

