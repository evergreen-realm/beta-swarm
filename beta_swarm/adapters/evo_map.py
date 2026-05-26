import shutil
import subprocess
import json
import os as os_mod
from typing import Dict
from beta_swarm.adapters.base import BaseToolAdapter

class EvoMapAdapter(BaseToolAdapter):
    def check_installed(self) -> bool:
        return shutil.which("evolver") is not None
    
    def run_command(self, cmd, timeout=180, cwd=None) -> Dict:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    
    def evolve(self, gep_prompt: str) -> Dict:
        if not self.check_installed():
            raise RuntimeError("evolver not installed. Run: npm install -g @evomap/evolver")
        cmd = ["evolver", "evolve", "--prompt", gep_prompt]
        result = self.run_command(cmd, timeout=180)
        genes = {}
        capsules = {}
        if result["success"]:
            for line in result["stdout"].split("\n"):
                if "genes.json" in line:
                    path = line.split()[-1]
                    if os_mod.path.exists(path):
                        with open(path) as f:
                            genes = json.load(f)
                if "capsules.json" in line:
                    path = line.split()[-1]
                    if os_mod.path.exists(path):
                        with open(path) as f:
                            capsules = json.load(f)
        return {"success": result["success"], "genes": genes, "capsules": capsules, "raw_output": result["stdout"]}
