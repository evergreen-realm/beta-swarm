"""
SummonEngine — Wake-word triggered voice-to-pipeline launcher.

Listens for "Hey Beta" wake phrase, transcribes the following speech
via Whisper, extracts the idea/concept, and returns a structured dict
that can be fed directly into the WorkflowEngine as S1 input.
"""

import re
import logging
import threading
import time
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy imports so the engine can still be instantiated even if audio
# hardware or whisper is unavailable (e.g. in CI / test environments).
_recorder = None
_whisper_pipeline = None


def _get_recorder():
    global _recorder
    if _recorder is None:
        try:
            from beta_swarm.voice.recorder import AudioRecorder
            _recorder = AudioRecorder(sample_rate=16000)
        except Exception as e:
            logger.warning(f"AudioRecorder unavailable: {e}")
    return _recorder


def _get_whisper():
    global _whisper_pipeline
    if _whisper_pipeline is None:
        try:
            from beta_swarm.voice.whisper_pipeline import WhisperPipeline
            _whisper_pipeline = WhisperPipeline(model_size="base")
        except Exception as e:
            logger.warning(f"WhisperPipeline unavailable: {e}")
    return _whisper_pipeline


# ─────────────────────────────────────────────────────────────────────────────
# Wake-word patterns
# ─────────────────────────────────────────────────────────────────────────────
WAKE_PATTERNS = [
    re.compile(r"hey\s+beta[,.]?\s*(.*)", re.IGNORECASE),
    re.compile(r"ok\s+beta[,.]?\s*(.*)", re.IGNORECASE),
    re.compile(r"yo\s+beta[,.]?\s*(.*)", re.IGNORECASE),
    re.compile(r"beta[,.]?\s+build\s+(.*)", re.IGNORECASE),
    re.compile(r"beta[,.]?\s+create\s+(.*)", re.IGNORECASE),
]

# Verb prefixes to strip when extracting the core idea title
STRIP_PREFIXES = re.compile(
    r"^(build|create|make|generate|design|write|develop|launch|start|set up|setup)\s+",
    re.IGNORECASE,
)


class SummonEngine:
    """
    Voice-activated pipeline launcher for Beta Swarm.

    Usage:
        engine = SummonEngine()
        engine.start_listening(callback=lambda idea: print(idea))
        # … or call engine._extract_idea(text) directly in tests
    """

    def __init__(
        self,
        wake_word: str = "hey beta",
        record_duration: float = 8.0,
        audio_tmp: str = "/tmp/summon_audio.wav",
    ):
        self.wake_word = wake_word.lower()
        self.record_duration = record_duration
        self.audio_tmp = audio_tmp
        self._listening = False
        self._thread: Optional[threading.Thread] = None
        logger.info("SummonEngine initialised (wake_word=%r)", self.wake_word)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def start_listening(self, callback=None, blocking: bool = False):
        """
        Start the background listening loop.

        Args:
            callback: callable(idea_dict) invoked whenever a valid summon
                      is detected.  idea_dict matches S1 input schema.
            blocking: if True, run in the current thread (useful for CLI).
        """
        self._listening = True
        self._callback = callback
        if blocking:
            self._listen_loop()
        else:
            self._thread = threading.Thread(
                target=self._listen_loop, daemon=True, name="summon-engine"
            )
            self._thread.start()
            logger.info("SummonEngine listening in background thread.")

    def stop_listening(self):
        """Signal the listening loop to stop."""
        self._listening = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("SummonEngine stopped.")

    # ──────────────────────────────────────────────────────────────────────
    # Core logic
    # ──────────────────────────────────────────────────────────────────────

    def _listen_loop(self):
        """Main loop: record → transcribe → detect wake → extract → callback."""
        recorder = _get_recorder()
        whisper = _get_whisper()

        if recorder is None or whisper is None:
            logger.error(
                "SummonEngine cannot start: AudioRecorder or WhisperPipeline unavailable."
            )
            return

        while self._listening:
            try:
                logger.debug("Recording %.1fs chunk…", self.record_duration)
                ok = recorder.record(self.record_duration, self.audio_tmp)
                if not ok:
                    time.sleep(1)
                    continue

                text = whisper.transcribe(self.audio_tmp)
                logger.debug("Transcribed: %r", text)

                if not text:
                    continue

                if self._contains_wake_word(text):
                    idea = self._extract_idea(text)
                    logger.info("Summon detected! idea=%r", idea)
                    if self._callback:
                        self._callback(idea)
                else:
                    logger.debug("No wake word detected.")

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("SummonEngine loop error: %s", e)
                time.sleep(2)

        # Cleanup temp file
        if os.path.exists(self.audio_tmp):
            try:
                os.remove(self.audio_tmp)
            except OSError:
                pass

    def _contains_wake_word(self, text: str) -> bool:
        """Return True if any wake pattern matches."""
        for pattern in WAKE_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def _extract_idea(self, text: str) -> dict:
        """
        Parse raw transcription into a structured idea dict compatible
        with S1IdeationAgent's `execute()` input schema.

        Returns:
            {
                "title": str,           # short idea label
                "raw": str,             # full extracted command
                "source": "voice",
                "input": str,           # same as raw, for S1 compatibility
            }
        """
        raw_command = text.strip()

        # Try each wake pattern to extract the post-wake content
        for pattern in WAKE_PATTERNS:
            m = pattern.search(text)
            if m:
                raw_command = m.group(1).strip()
                break

        # Derive a clean title by stripping leading verb
        title = STRIP_PREFIXES.sub("", raw_command).strip()

        # Capitalise first letter
        if title:
            title = title[0].upper() + title[1:]

        return {
            "title": title or "Untitled Idea",
            "raw": raw_command,
            "source": "voice",
            "input": raw_command,   # S1 expects key "input"
        }

    # ──────────────────────────────────────────────────────────────────────
    # Convenience: one-shot text-based summon (no mic, useful for tests)
    # ──────────────────────────────────────────────────────────────────────

    def text_summon(self, text: str) -> Optional[dict]:
        """
        Process a text string as if it were transcribed speech.
        Returns the idea dict if a wake word is found, else None.
        """
        if self._contains_wake_word(text):
            return self._extract_idea(text)
        return None
