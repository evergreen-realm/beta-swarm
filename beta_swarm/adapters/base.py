import abc
import shutil
import subprocess
import json
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseToolAdapter(abc.ABC):
    """Abstract base class for interfacing with external CLI tools."""

    def check_installed(self, tool_name: str = None) -> bool:
        """Check if a tool is available in the system PATH.
        
        Subclasses may override without the tool_name parameter
        if they know their own tool name.
        """
        if tool_name:
            return shutil.which(tool_name) is not None
        return False

    def run_command(self, cmd: List[str], timeout: int = 600, cwd: str = None) -> Dict[str, Any]:
        """Execute a CLI command and capture output."""
        logger.info(f"Executing command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                cwd=cwd
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return {
                "success": False, 
                "error": "timeout", 
                "stdout": e.stdout or "", 
                "stderr": e.stderr or "Timeout expired"
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "success": False, 
                "error": str(e), 
                "stdout": "", 
                "stderr": str(e)
            }

    def parse_json_output(self, stdout: str) -> Optional[Dict[str, Any]]:
        """Extract and parse a JSON block from stdout, handling potential surrounding text."""
        try:
            match = re.search(r'(\{.*\})', stdout, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(stdout)
        except (json.JSONDecodeError, ValueError, AttributeError):
            logger.warning("Failed to parse JSON from stdout")
            return None

