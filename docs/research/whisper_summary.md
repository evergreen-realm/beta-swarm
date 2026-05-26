# Research Summary: whisper / whisper.cpp
**Repo:** [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp)

## Key Patterns
- **Integer Quantization**: Running Whisper models in 4-bit/5-bit to save memory and increase speed on CPU.
- **C/C++ Implementation**: Zero-dependency inference engine for Whisper.
- **Streaming STT**: Patterns for processing audio in chunks for real-time transcription.

## What to Steal
- The **CLI integration pattern** for whisper.cpp: Much faster than the python `openai-whisper` package for single-command transcriptions on Windows.
- **Base model usage**: Finding the "sweet spot" (usually `base` or `small` models) for T490 hardware.

## Integration Plan
- Update `dashboard/voice_module.py` to prefer `whisper-cli` if found in the system path.
- Implement a fall-through to the `openai-whisper` python library if the C++ binary is missing.
