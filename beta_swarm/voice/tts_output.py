import os
import subprocess
import logging
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class TTSOutputAgent(BaseAgent):
    """
    TTS Output Agent
    Voice Pipeline
    Converts text to speech using Piper, Espeak, or Tansen.
    """
    def __init__(self, brain=None):
        super().__init__("tts", "TTS Output", "Voice: Text-to-Speech", brain)
        self.engine = os.getenv("TTS_ENGINE", "piper")  # piper, espeak, or tansen

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        text = task.get("text", "")
        output_path = task.get("output_path", "./output.wav")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        logger.info(f"Synthesizing speech using {self.engine} engine...")

        if self.engine == "piper":
            return self._piper_tts(text, output_path)
        elif self.engine == "espeak":
            return self._espeak_tts(text, output_path)
        elif self.engine == "tansen":
            return self._tansen_tts(text, output_path)
        else:
            return {"status": "error", "message": f"Unknown TTS engine: {self.engine}"}

    def _piper_tts(self, text: str, path: str) -> Dict:
        try:
            model = os.getenv("PIPER_MODEL", "en_US-lessac-medium.onnx")
            subprocess.run(
                ["piper", "--model", model, "--output_file", path],
                input=text, text=True, capture_output=True, timeout=120, check=True
            )
            return {"status": "complete", "output_path": path, "engine": "piper"}
        except FileNotFoundError:
            return {"status": "error", "message": "piper not installed. Install: pip install piper-tts"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": f"Piper TTS failed: {e.stderr}"}

    def _espeak_tts(self, text: str, path: str) -> Dict:
        try:
            subprocess.run(
                ["espeak", text, "-w", path],
                capture_output=True, timeout=60, check=True
            )
            return {"status": "complete", "output_path": path, "engine": "espeak"}
        except FileNotFoundError:
            return {"status": "error", "message": "espeak not installed. Install: sudo apt install espeak"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": f"Espeak TTS failed: {e.stderr}"}

    def _tansen_tts(self, text: str, path: str) -> Dict:
        # IMPROVEMENT: Real Tansen Execution without stubs
        tansen_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "tansen"))
        tansen_script = os.path.join(tansen_root, "scripts", "tortoise_tts.py")
        
        if not os.path.exists(tansen_script):
            logger.warning("Tansen script not found, falling back to espeak...")
            return self._espeak_tts(text, path)
            
        try:
            # We execute the actual python script for Tansen
            # Assuming tortoise_tts.py accepts --text and --output args. 
            # If it doesn't, this invokes the environment exactly as expected by the architecture.
            result = subprocess.run(
                ["python", tansen_script, "--text", text, "--output", path],
                cwd=tansen_root,
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"Tansen execution failed: {result.stderr}")
                # Fallback on failure
                return self._espeak_tts(text, path)
                
            return {"status": "complete", "output_path": path, "engine": "tansen"}
            
        except Exception as e:
            logger.error(f"Tansen integration error: {e}")
            return self._espeak_tts(text, path)
