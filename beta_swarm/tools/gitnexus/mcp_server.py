"""GitNexus MCP Server — exposes repo intel via Model Context Protocol."""

import json
import sys
import logging
from typing import Dict, Any, List
from pathlib import Path

from beta_swarm.tools.gitnexus.indexer import GitNexusIndexer
from beta_swarm.tools.gitnexus.risk_analyzer import RiskAnalyzer

logger = logging.getLogger(__name__)

class GitNexusMCPServer:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.indexer = GitNexusIndexer(repo_path)
        self.risk = RiskAnalyzer(repo_path)
        self._index_built = False

    def _ensure_index(self):
        if not self._index_built:
            self.indexer.build_index()
            self._index_built = True

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Routes MCP requests to the appropriate GitNexus tool."""
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            if method == "index":
                return self.indexer.build_index()
            elif method == "search":
                self._ensure_index()
                return {"status": "complete", "results": self.indexer.search(params.get("query", ""), params.get("limit", 10))}
            elif method == "risk":
                return self.risk.analyze()
            elif method == "file_content":
                return self._get_file_content(params.get("path", ""))
            elif method == "recent_commits":
                self._ensure_index()
                return {"status": "complete", "commits": self.indexer.index["commits"][:params.get("limit", 10)]}
            elif method == "functions_in_file":
                self._ensure_index()
                file_path = params.get("path", "")
                funcs = [f for f in self.indexer.index["functions"] if f["file"] == file_path]
                return {"status": "complete", "functions": funcs}
            else:
                return {"status": "error", "message": f"Unknown method: {method}"}
        except Exception as e:
            logger.error(f"MCP Request Error: {e}")
            return {"status": "error", "message": str(e)}

    def _get_file_content(self, rel_path: str) -> Dict[str, Any]:
        full = Path(self.repo_path) / rel_path
        try:
            with open(full, "r", encoding="utf-8") as f:
                return {"status": "complete", "content": f.read(), "path": rel_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_stdio(self):
        """Standard Input/Output bridge for integration with desktop AI clients."""
        logger.info("GitNexus MCP Server starting in STDIO mode...")
        for line in sys.stdin:
            try:
                req = json.loads(line)
                resp = self.handle_request(req)
                print(json.dumps(resp), flush=True)
            except json.JSONDecodeError:
                print(json.dumps({"status": "error", "message": "Invalid JSON"}), flush=True)

    def run_http(self, port: int = 8765):
        """HTTP bridge for remote swarm accessibility."""
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class Handler(BaseHTTPRequestHandler):
            def do_POST(inner_self):
                content_len = int(inner_self.headers.get("Content-Length", 0))
                body = inner_self.rfile.read(content_len)
                try:
                    req = json.loads(body)
                    resp = self.handle_request(req)
                    inner_self.send_response(200)
                except Exception as e:
                    resp = {"status": "error", "message": str(e)}
                    inner_self.send_response(500)
                inner_self.send_header("Content-Type", "application/json")
                inner_self.end_headers()
                inner_self.wfile.write(json.dumps(resp).encode())

            def log_message(self, format, *args):
                logger.debug(format % args)

        server = HTTPServer(("0.0.0.0", port), Handler)
        logger.info(f"[GitNexus MCP] Listening on http://0.0.0.0:{port}")
        server.serve_forever()

if __name__ == "__main__":
    # Default to stdio mode for local client integration
    server = GitNexusMCPServer()
    server.run_stdio()
