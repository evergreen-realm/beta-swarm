import shutil
import subprocess
from typing import Dict, List
from beta_swarm.adapters.base import BaseToolAdapter

class LevelCodeAdapter(BaseToolAdapter):
    def check_installed(self) -> bool:
        return shutil.which("levelcode") is not None
    
    def run_command(self, cmd: List[str], timeout: int = 120, cwd: str = None) -> Dict:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    def plan(self, files: List[str]) -> Dict:
        if not self.check_installed():
            raise RuntimeError("levelcode not installed. Run: npm install -g @levelcode/cli")
        cmd = ["levelcode", "plan", "--files"] + files
        return self.run_command(cmd, timeout=120)
    
    def edit(self, file: str, instruction: str) -> Dict:
        if not self.check_installed():
            raise RuntimeError("levelcode not installed. Run: npm install -g @levelcode/cli")
        cmd = ["levelcode", "edit", file, "--instruction", instruction]
        return self.run_command(cmd, timeout=120)
