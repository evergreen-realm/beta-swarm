"""Hermes Agent Bridge — connects host PC Hermes CLI to the Beta Swarm."""

import os
import subprocess
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class HermesBridge:
    """Bridge to the host's Hermes-Agent environment."""

    def __init__(self):
        # Prefer the known absolute path in the Hermes venv
        self.hermes_path = os.path.expandvars(r"%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe")
        # The actual script location usually inside the venv or globally
        self.hermes_script = os.path.expandvars(r"%LOCALAPPDATA%\hermes\hermes-agent\main.py")
        
        if not os.path.exists(self.hermes_path):
            self.hermes_path = "python" # Fallback to PATH
            
        self.sessions: Dict[str, subprocess.Popen] = {}

    def _check_hermes(self) -> Dict[str, Any]:
        """Verifies if the Hermes environment is accessible."""
        if not os.path.exists(self.hermes_script):
            return {"status": "error", "message": f"Hermes script not found at {self.hermes_script}"}
            
        try:
            result = subprocess.run(
                [self.hermes_path, self.hermes_script, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "status": "complete" if result.returncode == 0 else "error",
                "version": result.stdout.strip(),
                "path": self.hermes_path
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_session(self, session_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Spawns a new Hermes session with optional environment context."""
        check = self._check_hermes()
        if check["status"] != "complete":
            return check
            
        env = os.environ.copy()
        if context:
            env["HERMES_CONTEXT"] = json.dumps(context)
            
        try:
            # We run hermes as a persistent process for low-latency communication
            proc = subprocess.Popen(
                [self.hermes_path, self.hermes_script, "session", "--id", session_id],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            self.sessions[session_id] = proc
            logger.info(f"Hermes session '{session_id}' spawned.")
            return {"session_id": session_id, "status": "active", "hermes_version": check["version"]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def send(self, session_id: str, message: str) -> Dict[str, Any]:
        """Sends a message to an active Hermes session."""
        if session_id not in self.sessions:
            return {"status": "error", "message": "Session not found"}
            
        proc = self.sessions[session_id]
        if proc.poll() is not None:
            return {"status": "error", "message": "Session ended unexpectedly"}
            
        try:
            proc.stdin.write(message + "\n")
            proc.stdin.flush()
            return {"status": "sent", "session_id": session_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def receive(self, session_id: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Reads the next line from a Hermes session's output."""
        if session_id not in self.sessions:
            return {"status": "error", "message": "Session not found"}
            
        proc = self.sessions[session_id]
        try:
            # Simple line-based reading with timeout
            # In production, this would use a background thread to prevent blocking
            import select
            ready, _, _ = select.select([proc.stdout], [], [], timeout)
            if ready:
                line = proc.stdout.readline()
                return {"status": "complete", "output": line.strip()}
            return {"status": "timeout", "output": ""}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def close(self, session_id: str) -> Dict[str, Any]:
        """Terminates an active Hermes session."""
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
        return {"status": "closed", "session_id": session_id}

    def swarm_dispatch(self, agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method to dispatch a task and get a synchronous result."""
        session_id = f"bridge_{agent_id}_{int(os.path.getmtime('.'))}"
        self.create_session(session_id, {"agent_id": agent_id, "swarm_mode": True})
        
        self.send(session_id, json.dumps({"action": "execute", "task": task}))
        result = self.receive(session_id, timeout=60.0)
        
        self.close(session_id)
        return result
