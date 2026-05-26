import shutil
import subprocess
from typing import Dict, List
from beta_swarm.adapters.base import BaseToolAdapter

class AiderAdapter(BaseToolAdapter):
    def check_installed(self) -> bool:
        return shutil.which("aider") is not None
    
    def run_command(self, cmd: List[str], timeout: int = 300, cwd: str = None) -> Dict:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    def architect(self, prompt: str, files: List[str]) -> Dict:
        if not self.check_installed():
            raise RuntimeError("aider not installed. Run: pip install aider-chat")
        cmd = ["aider", "--model", "gemini/gemini-2.5-flash", "--no-auto-commits", "--architect", "-m", prompt] + files
        return self.run_command(cmd, timeout=300)
    
    def code(self, prompt: str, files: List[str]) -> Dict:
        if not self.check_installed():
            raise RuntimeError("aider not installed. Run: pip install aider-chat")
        cmd = ["aider", "--model", "gemini/gemini-2.5-flash", "--no-auto-commits", "-m", prompt] + files
        return self.run_command(cmd, timeout=300)
