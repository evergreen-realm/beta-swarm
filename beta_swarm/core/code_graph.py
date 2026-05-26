import os
import ast
import logging
from typing import List, Dict, Any
from beta_swarm.brain.kuzu_manager import KuzuBrain

logger = logging.getLogger(__name__)

class CodeGraphBuilder:
    """Indexes local source code into KuzuDB for graph-based analysis."""
    
    def __init__(self):
        self.kuzu = KuzuBrain()

    def index_directory(self, path: str):
        """Scan directory and index python files."""
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    self.index_file(os.path.join(root, file))

    def index_file(self, file_path: str):
        """Parse a python file and index imports/functions into the graph."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            
            rel_path = os.path.relpath(file_path, os.getcwd())
            self.kuzu.conn.execute("CREATE (f:File {path: $path})", parameters={"path": rel_path})
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._add_dependency(rel_path, alias.name)
                elif isinstance(node, ast.ImportFrom):
                    self._add_dependency(rel_path, node.module)
                elif isinstance(node, ast.FunctionDef):
                    # Index function within file
                    pass
        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")

    def _add_dependency(self, file_path: str, dep_name: str):
        """Create a relationship in KuzuDB."""
        if not dep_name: return
        try:
            # Simplified dependency tracking
            self.kuzu.conn.execute(
                "MATCH (f:File {path: $path}) "
                "MERGE (d:Dependency {name: $dep}) "
                "MERGE (f)-[:DEPENDS_ON]->(d)",
                parameters={"path": file_path, "dep": dep_name}
            )
        except Exception:
            pass
