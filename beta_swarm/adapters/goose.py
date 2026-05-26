import shutil
import subprocess
import json
import os as os_mod
from typing import Dict
from beta_swarm.adapters.base import BaseToolAdapter

class GooseAdapter(BaseToolAdapter):
    def _get_goose_path(self) -> str:
        """Find the goose executable path, including common Windows install locations."""
        path = shutil.which("goose")
        if path:
            return path
        # Check Windows home directory installation
        home_goose = os_mod.path.join(os_mod.path.expanduser("~"), "goose", "goose.exe")
        if os_mod.path.exists(home_goose):
            return home_goose
        return "goose"

    def check_installed(self) -> bool:
        path = self._get_goose_path()
        return shutil.which(path) is not None or os_mod.path.exists(path)
    
    def run_command(self, cmd, timeout=30, cwd=None) -> Dict:
        # Use full path if goose is the command
        if cmd[0] == "goose":
            cmd[0] = self._get_goose_path()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    
    def session_start(self, name: str) -> Dict:
        if not self.check_installed():
            raise RuntimeError("goose not installed. Run: curl -fsSL https://block.github.io/goose/install.sh | bash")
        return self.run_command(["goose", "session", "--name", name], timeout=30)
    
    def send(self, session_id: str, message: str) -> Dict:
        if not self.check_installed():
            raise RuntimeError("goose not installed")
        return self.run_command(["goose", "send", "--session", session_id, "--message", message], timeout=60)
    
    def mcp_register(self, server_config: dict) -> Dict:
        if not self.check_installed():
            raise RuntimeError("goose not installed")
        config_path = os_mod.path.expanduser("~/.config/goose/mcp-servers.json")
        os_mod.makedirs(os_mod.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(server_config, f, indent=2)
        return self.run_command(["goose", "mcp", "reload"], timeout=30)
