import sounddevice as sd
import wavio
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

class AudioRecorder:
    """
    Handles audio recording using sounddevice and wavio.
    """
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def record(self, duration_seconds: float, output_file: str):
        """Record audio for a fixed duration and save to a file."""
        logger.info(f"Recording for {duration_seconds} seconds...")
        try:
            # Record audio as a numpy array
            recording = sd.rec(
                int(duration_seconds * self.sample_rate), 
                samplerate=self.sample_rate, 
                channels=1, 
                dtype='int16'
            )
            sd.wait() # Wait for recording to finish
            
            # Save using wavio
            wavio.write(output_file, recording, self.sample_rate, sampwidth=2)
            logger.info(f"Audio saved to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return False

    def listen_and_record(self, output_file: str, silence_threshold: float = 0.01, max_duration: int = 30):
        """
        Optional: Record until silence or max duration. 
        Simplified implementation for now.
        """
        # For now, just call record with a default duration or use simple logic
        return self.record(5.0, output_file) # Mocking auto-stop for now
