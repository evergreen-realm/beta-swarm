import os
import subprocess
import logging
from typing import Dict, Any
from beta_swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class WhisperWrapperAgent(BaseAgent):
    """
    Whisper Transcription Agent
    Voice Pipeline
    Wraps whisper.cpp or falls back to system processes to transcribe audio files.
    """
    def __init__(self, brain=None):
        super().__init__("whisper", "Whisper Transcription", "Voice: Speech-to-Text", brain)
        # IMPROVEMENT: expanduser to handle paths like ~/models
        self.model_path = os.path.expanduser(os.getenv("WHISPER_MODEL", "~/models/ggml-base.bin"))
        self.cli_path = os.getenv("WHISPER_CLI", "whisper-cli")

    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        audio_path = task.get("audio_path", "")
        language = task.get("language", "en")

        if not audio_path or not os.path.exists(audio_path):
            return {"status": "error", "message": f"Audio file not found: {audio_path}"}

        logger.info(f"Transcribing {audio_path} using Whisper...")
        
        try:
            # IMPROVEMENT: Add robustness for stdout capturing and error checking
            result = subprocess.run(
                [self.cli_path, "-f", audio_path, "-m", self.model_path, "-l", language, "--no-timestamps"],
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"Whisper CLI failed: {result.stderr}")
                return {"status": "error", "message": "Transcription failed", "details": result.stderr}
                
            transcript = result.stdout.strip()
            
            if not transcript:
                return {"status": "warning", "message": "Transcription yielded empty text. Audio may be blank."}
                
            if self.brain:
                self.brain.store_fact(self.agent_id, f"Transcribed {len(transcript.split())} words", "voice")
                
            return {
                "status": "complete", 
                "transcript": transcript, 
                "word_count": len(transcript.split())
            }
            
        except FileNotFoundError:
            # IMPROVEMENT: Graceful error if whisper-cli is simply not installed
            return {
                "status": "error", 
                "message": f"whisper-cli not found at {self.cli_path}. Please install whisper.cpp."
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Transcription timed out after 300 seconds."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
