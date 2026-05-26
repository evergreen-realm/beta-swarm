import shutil
import subprocess
import os
from typing import Dict, List
from beta_swarm.adapters.base import BaseToolAdapter

class ExoAdapter(BaseToolAdapter):
    """
    Adapter for EXO distributed inference engine.
    Allows swarms to offload inference to other devices in the local network.
    """
    def check_installed(self) -> bool:
        return shutil.which("exo") is not None
    
    def run_command(self, cmd: List[str], timeout: int = 60, cwd: str = None) -> Dict:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    
    def start_node(self) -> Dict:
        """Start a local EXO node to join the mesh."""
        if not self.check_installed():
            raise RuntimeError("EXO not installed.")
        return self.run_command(["exo", "node", "start"], timeout=30)

    def list_mesh(self) -> Dict:
        """List all nodes in the current EXO mesh."""
        if not self.check_installed():
            raise RuntimeError("EXO not installed.")
        return self.run_command(["exo", "mesh", "list"], timeout=10)
