import shutil
import subprocess
from typing import Dict, List
from beta_swarm.adapters.base import BaseToolAdapter

class OpenCodeAdapter(BaseToolAdapter):
    def check_installed(self) -> bool:
        return shutil.which("opencode") is not None
    
    def run_command(self, cmd, timeout=300, cwd=None) -> Dict:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    
    def code(self, task: str, files: List[str]) -> Dict:
        if not self.check_installed():
            raise RuntimeError("opencode not installed. Run: npm install -g opencode")
        cmd = ["opencode", "code", "--task", task, "--files"] + files
        return self.run_command(cmd, timeout=300)
    
    def skill_add(self, repo: str) -> Dict:
        if not self.check_installed():
            raise RuntimeError("opencode not installed")
        return self.run_command(["opencode", "skill", "add", repo], timeout=60)
