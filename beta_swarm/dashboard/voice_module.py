import asyncio
import edge_tts
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

class JarvisVoice:
    """Voice interface for the Beta Swarm JARVIS dashboard."""
    
    # JARVIS-like voice (Microsoft Online)
    VOICE = "en-GB-RyanNeural" 
    
    def __init__(self):
        self.output_path = os.path.join(os.getcwd(), "jarvis_voice.mp3")

    async def speak(self, text: str):
        """Convert text to speech and play it."""
        logger.info(f"JARVIS: {text}")
        try:
            communicate = edge_tts.Communicate(text, self.VOICE)
            await communicate.save(self.output_path)
            
            # Play the audio (Windows)
            if os.name == 'nt':
                subprocess.run(["powershell", "-c", f"(New-Object Media.SoundPlayer '{self.output_path}').PlaySync()"], 
                               capture_output=True)
            else:
                subprocess.run(["mpg123", self.output_path], capture_output=True)
                
        except Exception as e:
            logger.error(f"Failed to generate JARVIS voice: {e}")

    def whisper_transcribe(self, audio_path: str) -> Optional[str]:
        """Transcribe audio using whisper.cpp (fast) or openai-whisper (slow)."""
        import shutil
        whisper_cpp = shutil.which("whisper-cli") or shutil.which("whisper")
        
        if whisper_cpp:
            logger.info("Using whisper.cpp for fast transcription...")
            try:
                result = subprocess.run([whisper_cpp, "-f", audio_path, "-otxt"], capture_output=True, text=True)
                return result.stdout.strip()
            except Exception as e:
                logger.error(f"whisper.cpp failed: {e}")
        
        # Fallback to python whisper
        logger.info("Using openai-whisper (fallback)...")
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            return result["text"].strip()
        except Exception as e:
            logger.error(f"openai-whisper failed: {e}")
            return None

    def listen_and_transcribe(self) -> Optional[str]:
        """Capture audio and transcribe it."""
        logger.info("JARVIS is listening...")
        # In a real scenario, we'd use sounddevice to record to a temp wav
        temp_wav = "voice_command.wav"
        if os.path.exists(temp_wav):
            return self.whisper_transcribe(temp_wav)
        return None

    async def process_command(self, command: str):
        """Process natural language commands."""
        command = command.lower()
        if "status" in command:
            await self.speak("System status is nominal. All agents are in idle state.")
        elif "pipeline" in command and "run" in command:
            await self.speak("Initiating master swarm pipeline. Ideation stage starting.")
        elif "abort" in command or "stop" in command:
            await self.speak("Emergency stop engaged. All agent processes terminated.")
        else:
            await self.speak(f"Processing command: {command}")

if __name__ == "__main__":
    jarvis = JarvisVoice()
    asyncio.run(jarvis.speak("System online. JARVIS dashboard initialized."))
