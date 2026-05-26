"""MergeKit DARE-TIES model merging for Beta Swarm."""

import os
import subprocess
import yaml
import logging
import shutil
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MergeKitDARE:
    """Merges models using DARE-TIES via MergeKit CLI."""

    def __init__(self):
        self.mergekit_bin = shutil.which("mergekit-yaml")
        self.output_dir = os.path.join(os.getcwd(), "merged_models")
        os.makedirs(self.output_dir, exist_ok=True)

    def check_install(self) -> Dict[str, Any]:
        """Checks if mergekit is installed and available."""
        if not self.mergekit_bin:
            return {"status": "error", "message": "mergekit-yaml not found in PATH. Install with: pip install mergekit"}
        return {"status": "complete", "bin": self.mergekit_bin}

    def install(self) -> Dict[str, Any]:
        """Attempts to install mergekit automatically."""
        try:
            result = subprocess.run(
                ["pip", "install", "mergekit"],
                capture_output=True,
                text=True,
                timeout=300
            )
            self.mergekit_bin = shutil.which("mergekit-yaml")
            return {
                "status": "complete" if result.returncode == 0 else "error",
                "stdout": result.stdout[-500:],
                "stderr": result.stderr[-500:]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def merge(self, models: List[str], merge_name: str = "swarm-merged", density: float = 0.6) -> Dict[str, Any]:
        """Creates a DARE-TIES merge recipe and executes it."""
        if not self.mergekit_bin:
            return {"status": "error", "message": "mergekit not installed."}

        # Validate model existence (assuming they are HuggingFace IDs or local paths)
        config = {
            "models": [
                {"model": m, "parameters": {"weight": round(1.0 / len(models), 2)}} 
                for m in models
            ],
            "merge_method": "dare_ties",
            "base_model": models[0],
            "parameters": {
                "density": density,
                "weight": 0.5
            },
            "dtype": "float16",
            "tokenizer_source": "base"
        }
        
        config_path = os.path.join(self.output_dir, f"{merge_name}_config.yaml")
        try:
            with open(config_path, "w") as f:
                yaml.dump(config, f, sort_keys=False)
            
            out_path = os.path.join(self.output_dir, merge_name)
            logger.info(f"Starting MergeKit merge: {merge_name}")
            
            # Execute merge with sharding to prevent RAM overflow
            cmd = [
                self.mergekit_bin, 
                config_path, 
                out_path, 
                "--copy-tokenizer", 
                "--out-shard-size", "2B", 
                "--lazy-unpickle"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200) # 2hr timeout
            
            if result.returncode == 0:
                return {
                    "status": "complete",
                    "output_path": out_path,
                    "config": config_path
                }
            else:
                return {"status": "error", "message": result.stderr[-1000:], "code": result.returncode}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_merged(self) -> List[str]:
        return [d for d in os.listdir(self.output_dir) if os.path.isdir(os.path.join(self.output_dir, d))]
