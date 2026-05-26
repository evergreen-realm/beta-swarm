"""EXO distributed inference mesh configuration."""

import os
import subprocess
import json
import logging
import socket
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class EXOMesh:
    """Configures EXO mesh for T490 (edge) <-> Production (cloud) distributed inference."""

    def __init__(self):
        self.exo_path = os.path.join(os.path.dirname(__file__), "exo")
        self.config_path = os.path.join(os.path.dirname(__file__), "mesh_config.json")
        self.nodes: List[Dict[str, Any]] = []

    def add_node(self, name: str, host: str, port: int, device: str = "cpu", role: str = "worker"):
        """Adds a node to the mesh configuration."""
        self.nodes.append({
            "name": name,
            "host": host,
            "port": port,
            "device": device,
            "role": role
        })

    def setup_t490_production_mesh(self, production_host: str = "prod-node-1.local", t490_host: str = None):
        """Standard topology: Edge T490 connecting to high-perf Production nodes."""
        if t490_host is None:
            # Auto-detect local IP if not provided
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                t490_host = s.getsockname()[0]
                s.close()
            except Exception:
                t490_host = "localhost"

        self.nodes = []
        self.add_node("t490-edge", t490_host, 5000, device="cpu", role="edge")
        self.add_node("prod-primary", production_host, 5000, device="cuda", role="primary")
        
        # Add backup node with convention-based discovery
        backup_host = production_host.replace("-1", "-2") if "-1" in production_host else f"{production_host}-backup"
        self.add_node("prod-backup", backup_host, 5000, device="cuda", role="backup")
        
        self._write_config()
        return {"status": "complete", "nodes": self.nodes, "detected_edge_ip": t490_host}

    def _write_config(self):
        """Writes the mesh_config.json for EXO."""
        config = {
            "mesh": {
                "discovery": "manual",
                "nodes": self.nodes,
                "model": "llama-3.1-8b",
                "shard_size": "4GB",
                "p2p": True
            }
        }
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

    def start_mesh(self) -> Dict[str, Any]:
        """Starts the EXO process with the current mesh configuration."""
        # Check for exo module presence
        try:
            import importlib.util
            exo_spec = importlib.util.find_spec("exo")
            if not exo_spec:
                return {"status": "error", "message": "EXO package not found. Run: pip install exo-explore"}
        except ImportError:
            return {"status": "error", "message": "EXO package not found."}

        try:
            # We use python -m exo to ensure environment consistency
            proc = subprocess.Popen(
                ["python", "-m", "exo", "--config", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"EXO mesh started with PID: {proc.pid}")
            return {"status": "started", "pid": proc.pid, "config": self.config_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def status(self) -> Dict[str, Any]:
        """Queries the current mesh health."""
        try:
            result = subprocess.run(
                ["python", "-m", "exo", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {"status": "complete", "output": result.stdout}
        except Exception as e:
            return {"status": "error", "message": str(e)}
