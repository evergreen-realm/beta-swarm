import shutil
import subprocess
import logging
from typing import Dict, List, Any, Optional
from beta_swarm.adapters.base import BaseToolAdapter

logger = logging.getLogger(__name__)

class GitNexusAdapter(BaseToolAdapter):
    """
    Adapter for GitNexus CLI.
    GitNexus creates a knowledge graph of the codebase and exposes it via MCP.
    """

    def check_installed(self) -> bool:
        """Check if gitnexus is available in the system PATH or via npx."""
        return shutil.which("gitnexus") is not None

    def analyze(self, path: str = ".") -> Dict[str, Any]:
        """
        Indexes the repository at the given path to create/update the knowledge graph.
        """
        if not self.check_installed():
            logger.info("gitnexus not in PATH, attempting via npx")
            return self.run_command(["npx", "gitnexus", "analyze", path])
        return self.run_command(["gitnexus", "analyze", path])

    def setup(self, editor: Optional[str] = None) -> Dict[str, Any]:
        """
        Detects installed editors and configures the MCP server automatically.
        """
        cmd = ["gitnexus", "setup"]
        if not self.check_installed():
            cmd = ["npx", "gitnexus", "setup"]
        
        if editor:
            cmd.extend(["--editor", editor])
            
        return self.run_command(cmd)

    def list_indexed(self) -> Dict[str, Any]:
        """
        Lists all repositories currently indexed by GitNexus.
        """
        cmd = ["gitnexus", "list"]
        if not self.check_installed():
            cmd = ["npx", "gitnexus", "list"]
        return self.run_command(cmd)

    def start_mcp(self) -> Dict[str, Any]:
        """
        Starts the GitNexus MCP server in stdio mode.
        Note: This is usually called by an MCP-compliant client (e.g. Cursor, Claude Desktop).
        """
        cmd = ["gitnexus", "mcp"]
        if not self.check_installed():
            cmd = ["npx", "gitnexus", "mcp"]
        return self.run_command(cmd)
