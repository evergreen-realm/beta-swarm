"""Goose CLI multi-session manager."""

import subprocess
import os
import shutil
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class GooseManager:
    def __init__(self):
        self.sessions: Dict[str, subprocess.Popen] = {}
        # Auto-detect goose path
        self.goose_path = shutil.which("goose")
        if not self.goose_path:
            # Fallback for common windows path mentioned in previous debug sessions
            home_goose = os.path.join(os.path.expanduser("~"), "goose", "goose.exe")
            if os.path.exists(home_goose):
                self.goose_path = home_goose

    def check_installed(self) -> bool:
        """Check if goose CLI is available."""
        try:
            subprocess.run(["goose", "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def code(self, prompt: str) -> Dict:
        """Run goose in non-interactive mode to execute a coding task."""
        if not self.goose_path:
            return {"status": "error", "message": "goose not installed"}
        try:
            result = subprocess.run(
                [self.goose_path, "run", "--instructions", prompt],
                capture_output=True, text=True, timeout=300
            )
            return {"status": "complete" if result.returncode == 0 else "error",
                    "stdout": result.stdout, "stderr": result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_session(self, session_id: str, provider: str = "openrouter") -> Dict[str, Any]:
        if not self.goose_path:
            return {"status": "error", "message": "goose not installed. Run: npm install -g @block/goose@latest"}
            
        cmd = [self.goose_path, "session", "--name", session_id, "--provider", provider]
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.sessions[session_id] = process
            logger.info(f"Goose session '{session_id}' created.")
            return {"session_id": session_id, "status": "active", "provider": provider}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"status": "error", "message": "Session not found"}
        process = self.sessions[session_id]
        if process.poll() is not None:
            return {"status": "error", "message": "Session has ended"}
        
        try:
            process.stdin.write(message + "\n")
            process.stdin.flush()
            # Simple confirmation, usually you'd want to read stdout to confirm reception
            return {"status": "sent", "session_id": session_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_sessions(self) -> Dict[str, Any]:
        active = []
        ended = []
        for sid, proc in self.sessions.items():
            if proc.poll() is None:
                active.append(sid)
            else:
                ended.append(sid)
        return {"active": active, "ended": ended, "total": len(self.sessions)}

    def close_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            return {"status": "error", "message": "Session not found"}
        proc = self.sessions[session_id]
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        del self.sessions[session_id]
        logger.info(f"Goose session '{session_id}' closed.")
        return {"status": "closed", "session_id": session_id}
