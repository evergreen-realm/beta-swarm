# Research Summary: llama.cpp
**Repo:** [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)

## Key Patterns
- **GGUF Format**: Highly efficient binary format for storing LLMs, optimized for CPU inference and fast loading.
- **Quantization (K-Quants)**: Reducing model size (e.g., to 4-bit or 1.58-bit) with minimal perplexity loss.
- **Unified Memory**: Efficiently sharing RAM between CPU and GPU (where applicable).

## What to Steal
- **Local CPU Inference**: Optimal patterns for running 7B+ models on commodity hardware like the T490.
- **BitNet implementation**: Patterns for handling 1.58-bit weights.

## Integration Plan
- Update `tools/bitnet/verify.py` to support loading GGUF-quantized BitNet models.
- Implement a fallback to `llama-cpp-python` for local CPU-bound verification tasks.
