import shutil
import subprocess
import os as os_mod
from typing import Dict, List
from beta_swarm.adapters.base import BaseToolAdapter

class HermesAdapter(BaseToolAdapter):
    def _get_hermes_cmd(self) -> List[str]:
        """Find the hermes command, supporting both global binary and local Python script."""
        path = shutil.which("hermes")
        if path:
            return [path]
        
        # Check Windows local AppData installation
        local_hermes = os_mod.path.join(os_mod.path.expanduser("~"), "AppData", "Local", "hermes", "hermes-agent", "cli.py")
        if os_mod.path.exists(local_hermes):
            return ["python", local_hermes]
        
        return ["hermes"]

    def check_installed(self) -> bool:
        cmd = self._get_hermes_cmd()
        if len(cmd) == 1:
            return shutil.which(cmd[0]) is not None
        return os_mod.path.exists(cmd[1])
    
    def run_command(self, cmd, timeout=60, cwd=None) -> Dict:
        # Replace 'hermes' with the actual command sequence
        full_cmd = self._get_hermes_cmd() + cmd[1:]
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    
    def chat(self, message: str) -> Dict:
        if not self.check_installed():
            raise RuntimeError("hermes not installed. Run: curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/install.sh | bash")
        return self.run_command(["hermes", "chat", "--message", message], timeout=60)
    
    def create_skill(self, name: str, pattern: str) -> Dict:
        if not self.check_installed():
            raise RuntimeError("hermes not installed")
        return self.run_command(["hermes", "skill", "create", "--name", name, "--pattern", pattern], timeout=60)
    
    def reflect(self) -> Dict:
        if not self.check_installed():
            raise RuntimeError("hermes not installed")
        return self.run_command(["hermes", "reflect"], timeout=60)
