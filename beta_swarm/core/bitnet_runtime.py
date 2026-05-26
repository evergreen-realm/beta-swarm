"""
BitNet Runtime — loads 1-bit quantised models via Microsoft BitNet or HuggingFace
transformers.  Falls back to the local Exo/Ollama HTTP APIs, then to cloud LLMs.
"""

import logging
import os
import json
import time
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# ── Optional heavy deps ────────────────────────────────────────────────────────
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers/torch not available – BitNetRuntime will use HTTP fallbacks.")

try:
    import bitnet  # microsoft/BitNet python wrapper (if installed)
    BITNET_PKG_AVAILABLE = True
except ImportError:
    BITNET_PKG_AVAILABLE = False


class BitNetRuntime:
    """
    Priority chain:
      1. BitNet local model (transformers + bitnet pkg)
      2. Ollama HTTP API  (OLLAMA_BASE_URL)
      3. LM Studio HTTP API (LMSTUDIO_BASE_URL)
      4. Groq cloud API
      5. Gemini cloud API
    """

    def __init__(
        self,
        model_path: str = "microsoft/bitnet-b1.58-2B-4T",
        device: str = "auto",
    ):
        self.model_path = model_path
        self.device = device
        self.tokenizer: Optional[Any] = None
        self.model: Optional[Any] = None
        self.initialized = False

        # Resolved env values
        self._ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self._lmstudio_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        self._groq_key = os.getenv("GROQ_API_KEY", "")
        self._gemini_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY") or os.getenv("GOOGLE_API_KEY", "")

        self._try_load_local_model()

    # ── Model loading ──────────────────────────────────────────────────────────

    def _try_load_local_model(self):
        if not TRANSFORMERS_AVAILABLE:
            logger.info("Skipping local model load – transformers not installed.")
            return

        try:
            logger.info(f"Loading BitNet model: {self.model_path}")
            load_kwargs: Dict[str, Any] = {
                "trust_remote_code": True,
                "low_cpu_mem_usage": True,
            }

            # Use the bitnet package to patch the model if available
            if BITNET_PKG_AVAILABLE:
                try:
                    bitnet.replace_hf_model_weights_with_bitnet_weights(self.model_path)
                    logger.info("BitNet weight replacement applied.")
                except Exception as patch_err:
                    logger.warning(f"BitNet patch failed (non-fatal): {patch_err}")

            import torch  # re-import inside guarded block
            if self.device == "auto":
                load_kwargs["device_map"] = "auto"
                if torch.cuda.is_available():
                    load_kwargs["torch_dtype"] = torch.float16
            else:
                load_kwargs["device_map"] = self.device

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path, **load_kwargs
            )
            self.initialized = True
            logger.info(f"BitNet model loaded successfully from '{self.model_path}'.")
        except Exception as e:
            logger.warning(f"Local BitNet model load failed: {e}. Will use HTTP/cloud fallbacks.")

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Returns: {"text": str, "via": str, "tokens": int, "latency_ms": float}
        """
        t0 = time.time()

        # 1. Local model
        if self.initialized and self.model and self.tokenizer:
            result = self._generate_local(prompt, max_tokens, temperature)
            if result:
                result["latency_ms"] = round((time.time() - t0) * 1000, 1)
                return result

        # 2. Ollama
        result = self._generate_http(
            self._ollama_url,
            prompt,
            max_tokens,
            temperature,
            provider="ollama",
        )
        if result:
            result["latency_ms"] = round((time.time() - t0) * 1000, 1)
            return result

        # 3. LM Studio
        result = self._generate_http(
            self._lmstudio_url,
            prompt,
            max_tokens,
            temperature,
            provider="lmstudio",
        )
        if result:
            result["latency_ms"] = round((time.time() - t0) * 1000, 1)
            return result

        # 4. Groq
        if self._groq_key:
            result = self._generate_groq(prompt, max_tokens, temperature)
            if result:
                result["latency_ms"] = round((time.time() - t0) * 1000, 1)
                return result

        # 5. Gemini
        if self._gemini_key:
            result = self._generate_gemini(prompt, max_tokens)
            if result:
                result["latency_ms"] = round((time.time() - t0) * 1000, 1)
                return result

        latency = round((time.time() - t0) * 1000, 1)
        logger.error("All BitNet generation backends exhausted.")
        return {
            "text": f"[ERROR] No generation backend available for prompt: {prompt[:80]}...",
            "via": "none",
            "tokens": 0,
            "latency_ms": latency,
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns runtime health info."""
        backends_up = []
        if self.initialized:
            backends_up.append("local_bitnet")
        if self._ping_http(self._ollama_url):
            backends_up.append("ollama")
        if self._ping_http(self._lmstudio_url):
            backends_up.append("lmstudio")
        if self._groq_key:
            backends_up.append("groq")
        if self._gemini_key:
            backends_up.append("gemini")
        return {
            "model_path": self.model_path,
            "local_initialized": self.initialized,
            "available_backends": backends_up,
            "transformers_available": TRANSFORMERS_AVAILABLE,
            "bitnet_pkg_available": BITNET_PKG_AVAILABLE,
        }

    # ── Internal generation methods ────────────────────────────────────────────

    def _generate_local(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> Optional[Dict[str, Any]]:
        try:
            import torch
            inputs = self.tokenizer(prompt, return_tensors="pt")
            device = next(self.model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            gen_cfg: Dict[str, Any] = {
                "max_new_tokens": max_tokens,
                "do_sample": temperature > 0,
            }
            if temperature > 0:
                gen_cfg["temperature"] = temperature

            with torch.no_grad():
                output_ids = self.model.generate(**inputs, **gen_cfg)

            # Decode only newly generated tokens
            prompt_len = inputs["input_ids"].shape[-1]
            new_ids = output_ids[0][prompt_len:]
            text = self.tokenizer.decode(new_ids, skip_special_tokens=True)
            return {"text": text.strip(), "via": "local_bitnet", "tokens": len(new_ids)}
        except Exception as e:
            logger.error(f"Local BitNet generation error: {e}")
            return None

    def _generate_http(
        self,
        base_url: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        provider: str,
    ) -> Optional[Dict[str, Any]]:
        """OpenAI-compatible /chat/completions endpoint (Ollama & LM Studio)."""
        if not self._ping_http(base_url):
            return None
        try:
            resp = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json={
                    "model": "llama3",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("completion_tokens", len(text.split()))
            return {"text": text, "via": provider, "tokens": tokens}
        except Exception as e:
            logger.warning(f"{provider} HTTP generation failed: {e}")
            return None

    def _generate_groq(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("completion_tokens", len(text.split()))
            return {"text": text, "via": "groq", "tokens": tokens}
        except Exception as e:
            logger.warning(f"Groq generation failed: {e}")
            return None

    def _generate_gemini(self, prompt: str, max_tokens: int) -> Optional[Dict[str, Any]]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._gemini_key)
            model = genai.GenerativeModel(
                "gemini-1.5-flash",
                generation_config={"max_output_tokens": max_tokens},
            )
            response = model.generate_content(prompt)
            text = response.text
            return {"text": text, "via": "gemini", "tokens": len(text.split())}
        except Exception as e:
            logger.warning(f"Gemini generation failed: {e}")
            return None

    def _ping_http(self, base_url: str, timeout: float = 2.0) -> bool:
        try:
            resp = requests.get(f"{base_url.rstrip('/')}/models", timeout=timeout)
            return resp.status_code < 500
        except Exception:
            return False
