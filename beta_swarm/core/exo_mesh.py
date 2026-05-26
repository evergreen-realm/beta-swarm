"""
ExoMesh — manages the Exo distributed inference cluster.

Exo exposes a REST API at http://localhost:52415 (default).
Endpoints used:
  GET /api/topology          → node list + model assignments
  GET /api/models/running    → active model shards
  POST /api/inference        → (optional direct inference)

If the Exo binary is not installed the class degrades gracefully and
reports status from whatever HTTP data it can collect.
"""

import json
import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class ExoMesh:
    """
    Manages the Exo distributed LLM inference mesh.

    Usage:
        mesh = ExoMesh()
        mesh.start()                # spawn background nodes
        status = mesh.get_cluster_status()
        mesh.stop()
    """

    # Default Exo REST port
    EXO_API_PORT = 52415
    # How long to wait for Exo node to become responsive after spawning (seconds)
    STARTUP_WAIT_S = 6
    # HTTP timeout for status queries
    HTTP_TIMEOUT_S = 3

    def __init__(self, listen_port: int = EXO_API_PORT):
        self.listen_port = listen_port
        self._api_base = f"http://localhost:{self.listen_port}"
        self._processes: List[subprocess.Popen] = []
        self._exo_cmd: Optional[str] = self._resolve_exo_cmd()
        self._node_id: str = os.getenv("EXO_NODE_ID", "beta-swarm-primary")
        self._started_at: Optional[float] = None

    # ── Binary resolution ──────────────────────────────────────────────────────

    def _resolve_exo_cmd(self) -> Optional[str]:
        """Tries PATH, pip scripts dir, and common install locations."""
        found = shutil.which("exo")
        if found:
            return found

        candidates = [
            os.path.expandvars(r"%APPDATA%\Python\Scripts\exo.exe"),
            os.path.expanduser("~/.local/bin/exo"),
            "/usr/local/bin/exo",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

        logger.warning("Exo binary not found in PATH or common locations.")
        return None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self, extra_peers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Launch the local Exo node.

        Args:
            extra_peers: list of "ip:port" strings for remote peers
        Returns:
            {"status": "started"|"already_running"|"error", ...}
        """
        if self._is_api_responsive():
            logger.info("Exo API already responsive — skipping spawn.")
            return {"status": "already_running", "api_base": self._api_base}

        if not self._exo_cmd:
            return {
                "status": "error",
                "error": "Exo binary not found. Install with: pip install exo-inference",
            }

        try:
            cmd = [
                self._exo_cmd,
                "--node-id", self._node_id,
                "--listen-port", str(self.listen_port),
            ]
            if extra_peers:
                for peer in extra_peers:
                    cmd += ["--peer", peer]

            use_shell = os.name == "nt"
            proc = subprocess.Popen(
                cmd,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._processes.append(proc)
            self._started_at = time.time()
            logger.info(f"Exo node spawned (PID {proc.pid}). Waiting for API...")

            # Wait for the REST API to become responsive
            deadline = time.time() + self.STARTUP_WAIT_S
            while time.time() < deadline:
                if self._is_api_responsive():
                    logger.info("Exo API is responsive.")
                    return {
                        "status": "started",
                        "pid": proc.pid,
                        "api_base": self._api_base,
                    }
                time.sleep(0.5)

            # Process might still be starting; return partial success
            if proc.poll() is None:
                return {
                    "status": "started",
                    "pid": proc.pid,
                    "api_base": self._api_base,
                    "note": "API not yet responsive within startup window",
                }
            else:
                stderr_out = proc.stderr.read() if proc.stderr else ""
                return {
                    "status": "error",
                    "error": f"Exo process exited early. stderr: {stderr_out[:400]}",
                }
        except Exception as e:
            logger.error(f"Failed to start Exo node: {e}")
            return {"status": "error", "error": str(e)}

    def stop(self) -> Dict[str, Any]:
        """Gracefully terminate all spawned Exo processes."""
        terminated = 0
        for proc in self._processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                terminated += 1
            except subprocess.TimeoutExpired:
                proc.kill()
                terminated += 1
            except Exception as e:
                logger.error(f"Error stopping Exo process {proc.pid}: {e}")
        self._processes = []
        logger.info(f"Exo mesh stopped — {terminated} process(es) terminated.")
        return {"status": "stopped", "terminated": terminated}

    # ── Cluster status ─────────────────────────────────────────────────────────

    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Queries the live Exo REST API for real topology data.
        Falls back to process-level data if the API is not reachable.
        """
        topology = self._query_topology()
        running_models = self._query_running_models()

        if topology is not None:
            nodes = topology.get("nodes", [])
            total_ram = sum(n.get("memory", {}).get("total_gb", 0) for n in nodes)
            free_ram = sum(n.get("memory", {}).get("free_gb", 0) for n in nodes)
            gpu_info = [
                {"node": n.get("id"), "gpu": n.get("gpu", "unknown")}
                for n in nodes
                if n.get("gpu")
            ]
            return {
                "status": "healthy",
                "api_responsive": True,
                "node_count": len(nodes),
                "nodes": [
                    {
                        "id": n.get("id"),
                        "address": n.get("address"),
                        "state": n.get("state", "unknown"),
                        "total_ram_gb": n.get("memory", {}).get("total_gb", 0),
                        "free_ram_gb": n.get("memory", {}).get("free_gb", 0),
                        "gpu": n.get("gpu"),
                    }
                    for n in nodes
                ],
                "active_models": running_models,
                "total_ram_gb": round(total_ram, 2),
                "available_ram_gb": round(free_ram, 2),
                "gpu_devices": gpu_info,
                "uptime_s": round(time.time() - self._started_at, 1) if self._started_at else None,
            }

        # API not reachable — fall back to process-level status
        active = sum(1 for p in self._processes if p.poll() is None)
        return {
            "status": "degraded" if self._processes and active == 0 else ("idle" if not self._processes else "running"),
            "api_responsive": False,
            "active_processes": active,
            "total_processes_spawned": len(self._processes),
            "active_models": [],
            "note": "Exo REST API not reachable; process-level data only.",
        }

    def run_inference(
        self,
        prompt: str,
        model: str = "llama3",
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        """
        Runs inference directly through the Exo cluster REST API.
        Returns {"text": str, "model": str, "via": "exo"} or {"error": str}.
        """
        if not self._is_api_responsive():
            return {"error": "Exo API not responsive. Start the mesh first."}
        try:
            resp = requests.post(
                f"{self._api_base}/api/inference",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                or data.get("response", "")
            )
            return {"text": text, "model": model, "via": "exo"}
        except Exception as e:
            logger.error(f"Exo inference failed: {e}")
            return {"error": str(e)}

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _is_api_responsive(self) -> bool:
        try:
            r = requests.get(
                f"{self._api_base}/api/topology", timeout=self.HTTP_TIMEOUT_S
            )
            return r.status_code < 500
        except Exception:
            return False

    def _query_topology(self) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(
                f"{self._api_base}/api/topology", timeout=self.HTTP_TIMEOUT_S
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def _query_running_models(self) -> List[str]:
        try:
            r = requests.get(
                f"{self._api_base}/api/models/running", timeout=self.HTTP_TIMEOUT_S
            )
            r.raise_for_status()
            data = r.json()
            return [m.get("name", m) if isinstance(m, dict) else str(m) for m in data]
        except Exception:
            return []
