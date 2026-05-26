"""Goose Server — headless background server for Goose CLI sessions."""
import os
import json
import logging
import subprocess
import shutil
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class GooseServer:
    """Manages headless Goose CLI sessions for background code generation."""

    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.goose_path = self._find_goose()

    def _find_goose(self) -> str:
        path = shutil.which("goose")
        if path:
            return path
        home_goose = os.path.join(os.path.expanduser("~"), "goose", "goose.exe")
        if os.path.exists(home_goose):
            return home_goose
        return "goose"

    def check_installed(self) -> bool:
        return shutil.which(self.goose_path) is not None or os.path.exists(self.goose_path)

    def create_session(self, name: str, provider: str = "google") -> Dict[str, Any]:
        """Create a new named Goose session."""
        if not self.check_installed():
            return {"error": "goose not installed"}
        try:
            result = subprocess.run(
                [self.goose_path, "session", "--name", name],
                capture_output=True, text=True, timeout=30
            )
            self.sessions[name] = {"name": name, "provider": provider, "status": "active"}
            return {"status": "created", "session": name, "output": result.stdout[:200]}
        except Exception as e:
            return {"error": str(e)}

    def send_message(self, session_name: str, message: str) -> Dict[str, Any]:
        """Send a message/instruction to an active session."""
        if not self.check_installed():
            return {"error": "goose not installed"}
        try:
            result = subprocess.run(
                [self.goose_path, "run", "--instructions", message],
                capture_output=True, text=True, timeout=120
            )
            return {
                "status": "sent",
                "session": session_name,
                "success": result.returncode == 0,
                "stdout": result.stdout[:500],
                "stderr": result.stderr[:200] if result.stderr else ""
            }
        except subprocess.TimeoutExpired:
            return {"error": "timeout", "session": session_name}
        except Exception as e:
            return {"error": str(e)}

    def list_sessions(self) -> List[Dict]:
        """Return all tracked sessions."""
        return list(self.sessions.values())

    def close_session(self, name: str) -> Dict[str, Any]:
        """Close/remove a tracked session."""
        if name in self.sessions:
            del self.sessions[name]
            return {"status": "closed", "session": name}
        return {"error": f"Session {name} not found"}
