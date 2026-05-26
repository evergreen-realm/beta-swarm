"""Hardened Voice Pipeline: Whisper -> PRD -> TTS."""

import os
import subprocess
import tempfile
import logging
import shutil
from typing import Dict, Any

logger = logging.getLogger(__name__)

class VoicePipeline:
    """End-to-end voice: transcribe (Whisper) -> process (PRD) -> speak (TTS)."""

    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.whisper_bin = self._find_whisper()

    def _find_whisper(self) -> str:
        """Finds the best available whisper binary."""
        for c in ["whisper-cli", "whisper", "whisper.exe"]:
            if shutil.which(c):
                return c
        return None

    def transcribe(self, audio_path: str, model: str = "base") -> Dict[str, Any]:
        """Converts audio to text using Whisper."""
        if not os.path.exists(audio_path):
            return {"status": "error", "message": f"Audio not found: {audio_path}"}
        
        if not self.whisper_bin:
            return {"status": "error", "message": "Whisper binary not found. Install with: pip install openai-whisper"}

        output_dir = os.path.join(self.temp_dir, "whisper_out")
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            logger.info(f"Transcribing: {audio_path}")
            # Improved flags for better accuracy in swarm context
            result = subprocess.run(
                [self.whisper_bin, audio_path, "--model", model, "--output_dir", output_dir, "--output_format", "txt", "--task", "transcribe"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Whisper creates a .txt file with the same name as audio
            base_name = os.path.basename(audio_path).rsplit(".", 1)[0]
            txt_file = os.path.join(output_dir, f"{base_name}.txt")
            
            transcript = ""
            if os.path.exists(txt_file):
                with open(txt_file, "r", encoding="utf-8") as f:
                    transcript = f.read().strip()
            
            if transcript:
                return {"status": "complete", "transcript": transcript}
            return {"status": "error", "message": "Transcript empty", "stderr": result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def prd_from_transcript(self, transcript: str, project_name: str = "Voice-Initiated") -> Dict[str, Any]:
        """Routes transcript to the s3_prd agent to generate structure."""
        try:
            from beta_swarm.agents.stage.s3_prd import S3PRDAgent
            # Check if brain is needed for initialization
            from beta_swarm.brain.kuzudb_manager import KuzuBrain
            brain = KuzuBrain()
            agent = S3PRDAgent(brain=brain)
            
            logger.info(f"Generating PRD from transcript for: {project_name}")
            result = agent.execute(task_input={
                "prompt": transcript,
                "project_name": project_name,
                "context": "Voice command input"
            })
            return {"status": "complete", "prd": result}
        except ImportError as e:
            return {"status": "error", "message": f"S3PRDAgent not found: {e}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def text_to_speech(self, text: str, voice: str = "en-US-GuyNeural", output_path: str = None) -> Dict[str, Any]:
        """Converts text back to audio (confirmation)."""
        if output_path is None:
            output_path = os.path.join(self.temp_dir, f"tts_{int(os.path.getmtime('.'))}.mp3")
            
        # Try edge-tts (Premium quality, no API key needed)
        edge_tts_bin = shutil.which("edge-tts")
        if edge_tts_bin:
            try:
                subprocess.run(
                    [edge_tts_bin, "--voice", voice, "--text", text, "--write-media", output_path],
                    capture_output=True, timeout=60
                )
                if os.path.exists(output_path):
                    return {"status": "complete", "path": output_path, "engine": "edge-tts"}
            except Exception:
                pass
                
        # Fallback: pyttsx3 (Offline, standard quality)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            return {"status": "complete", "path": output_path, "engine": "pyttsx3"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def full_pipeline(self, audio_path: str, project_name: str = "Voice-Project") -> Dict[str, Any]:
        """Runs the entire end-to-end voice-to-PRD pipeline."""
        t_res = self.transcribe(audio_path)
        if t_res["status"] != "complete":
            return t_res
            
        p_res = self.prd_from_transcript(t_res["transcript"], project_name)
        if p_res["status"] != "complete":
            return p_res
            
        # Confirmation message
        msg = f"Voice command processed. PRD for {project_name} has been generated and indexed."
        tts_res = self.text_to_speech(msg)
        
        return {
            "status": "complete",
            "transcript": t_res["transcript"],
            "prd": p_res["prd"],
            "confirmation_audio": tts_res.get("path")
        }
