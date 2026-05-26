"""OpenClaw browser automation — wraps the host PC's `npx openclaw` CLI tool."""

import subprocess
import json
import os
import tempfile
import shutil
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class OpenClaw:
    """Bridge to the real OpenClaw Node.js CLI (npx openclaw)."""

    def __init__(self):
        self.npx_path = shutil.which("npx")
        if not self.npx_path:
            logger.warning("npx not found in PATH. Browser automation may fail.")

    def _check_install(self):
        if not self.npx_path:
            raise RuntimeError("npx not found. Please install Node.js.")
            
        result = subprocess.run(
            [self.npx_path, "openclaw", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError("npx openclaw not available. Install with: npm install -g openclaw")

    def browse(self, url: str, task: str = "scrape", actions: List[Dict] = None) -> Dict[str, Any]:
        """Browse a single URL via OpenClaw CLI."""
        if not self.npx_path:
            return {"status": "error", "message": "npx not found"}
            
        cmd = [self.npx_path, "openclaw", "browse", "--url", url, "--task", task, "--format", "json"]
        if actions:
            actions_json = json.dumps(actions)
            cmd.extend(["--actions", actions_json])
            
        try:
            logger.info(f"OpenClaw browsing: {url}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"status": "complete", "raw": result.stdout}
            return {"status": "error", "message": result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def search_and_navigate(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """DuckDuckGo search then browse top results."""
        if not self.npx_path:
            return {"status": "error", "message": "npx not found"}
            
        cmd = [self.npx_path, "openclaw", "search", "--query", query, "--max", str(max_results), "--format", "json"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                return {"status": "error", "message": result.stderr}
            
            try:
                search_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"status": "error", "message": "Invalid JSON from search"}
                
            enriched = []
            for item in search_data.get("results", [])[:max_results]:
                url = item.get("url")
                if url:
                    page = self.browse(url, task="scrape")
                    item["page_content"] = page
                enriched.append(item)
            return {"status": "complete", "query": query, "results": enriched}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def extract_structured(self, url: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract structured data using CSS selectors."""
        if not self.npx_path:
            return {"status": "error", "message": "npx not found"}
            
        cmd = [self.npx_path, "openclaw", "extract", "--url", url, "--selectors", json.dumps(selectors), "--format", "json"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                try:
                    return {"status": "complete", "data": json.loads(result.stdout)}
                except json.JSONDecodeError:
                    return {"status": "complete", "raw": result.stdout}
            return {"status": "error", "message": result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def screenshot(self, url: str, output_path: str = None) -> Dict[str, Any]:
        """Capture screenshot via OpenClaw."""
        if not self.npx_path:
            return {"status": "error", "message": "npx not found"}
            
        if output_path is None:
            output_path = os.path.join(tempfile.gettempdir(), f"openclaw_{int(os.path.getmtime('.'))}.png")
            
        cmd = [self.npx_path, "openclaw", "screenshot", "--url", url, "--output", output_path]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return {"status": "complete", "path": output_path}
            return {"status": "error", "message": result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}
