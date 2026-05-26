"""Speculative decoding setup for llama.cpp with draft model orchestration."""

import os
import subprocess
import logging
import shutil
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SpeculativeDecoder:
    """Configures llama.cpp speculative decoding (draft + target model)."""

    def __init__(self, llama_cpp_path: str = None):
        self.llama_cpp_bin = shutil.which("llama-cli") or shutil.which("main")
        if not self.llama_cpp_bin and llama_cpp_path:
            self.llama_cpp_bin = os.path.join(llama_cpp_path, "main")
            
        self.models_dir = os.path.join(os.getcwd(), "models")
        os.makedirs(self.models_dir, exist_ok=True)

    def setup(self, target_model: str, draft_model: str = None) -> Dict[str, Any]:
        """Validates existence of both models and prepares the execution command."""
        if not self.llama_cpp_bin:
            return {"status": "error", "message": "llama.cpp binary (llama-cli or main) not found in PATH."}

        if draft_model is None:
            draft_model = self._infer_draft_model(target_model)
            
        target_path = os.path.join(self.models_dir, target_model)
        draft_path = os.path.join(self.models_dir, draft_model)
        
        # Check if paths exist, otherwise look for them in global search
        if not os.path.exists(target_path):
            return {"status": "error", "message": f"Target model not found at {target_path}"}
            
        if not os.path.exists(draft_path):
            logger.warning(f"Draft model not found at {draft_path}. Speedup will be unavailable.")
            return {"status": "partial", "message": "Draft model missing. Running baseline only."}
            
        return {
            "status": "ready",
            "target": target_path,
            "draft": draft_path,
            "command": self._build_command(target_path, draft_path)
        }

    def _infer_draft_model(self, target: str) -> str:
        """Heuristic to find a compatible smaller model for speculative decoding."""
        if "70b" in target.lower():
            return target.replace("70b", "8b")
        elif "8b" in target.lower():
            return target.replace("8b", "1b")
        elif "32b" in target.lower():
            return target.replace("32b", "3b")
        return target # No inference possible

    def _build_command(self, target: str, draft: str) -> List[str]:
        """Constructs the llama.cpp speculative command."""
        return [
            self.llama_cpp_bin,
            "-m", target,
            "-md", draft,
            "--draft", "16",
            "-n", "512",
            "--temp", "0.7",
            "--repeat-penalty", "1.1"
        ]

    def run_inference(self, prompt: str, target_model: str, draft_model: str = None) -> Dict[str, Any]:
        """Executes a speculative inference request."""
        setup = self.setup(target_model, draft_model)
        if setup["status"] == "error":
            return setup
            
        cmd = setup["command"] + ["-p", prompt]
        try:
            logger.info(f"Running speculative inference: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return {
                    "status": "complete",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            return {"status": "error", "message": result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def benchmark_speedup(self, prompt: str, target_model: str, draft_model: str = None) -> Dict[str, Any]:
        """Measures the speed gain achieved via speculation."""
        import time
        
        # 1. Baseline (Target only)
        start = time.time()
        baseline_cmd = [self.llama_cpp_bin, "-m", os.path.join(self.models_dir, target_model), "-p", prompt, "-n", "128"]
        subprocess.run(baseline_cmd, capture_output=True, timeout=120)
        baseline_time = time.time() - start
        
        # 2. Speculative
        start = time.time()
        self.run_inference(prompt, target_model, draft_model)
        spec_time = time.time() - start
        
        speedup = baseline_time / spec_time if spec_time > 0 else 1.0
        return {
            "status": "complete",
            "baseline_sec": round(baseline_time, 2),
            "speculative_sec": round(spec_time, 2),
            "speedup_factor": round(speedup, 2)
        }
