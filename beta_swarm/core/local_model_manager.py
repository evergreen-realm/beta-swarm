import os
import httpx
import logging
import time

logger = logging.getLogger(__name__)


class LocalModelManager:
    """
    Manages LM Studio model lifecycle via both OpenAI-compatible (/v1)
    and native REST API (/api/v1) endpoints.

    Key capability: load ONE model at a time, run inference, unload it,
    then load the next — critical for RAM-constrained machines.
    """

    def __init__(self, lm_studio_url: str = None, ollama_url: str = None):
        self.lm_studio_base = lm_studio_url or os.getenv(
            "LMSTUDIO_BASE_URL", "http://localhost:1234/v1"
        )
        self.ollama_url = ollama_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434/v1"
        )

        # Derive the native API base from the OpenAI-compatible URL
        # http://localhost:1234/v1 -> http://localhost:1234
        self._host_base = self.lm_studio_base.replace("/v1", "")

        # Short timeouts for health checks
        self.health_client = httpx.Client(timeout=5.0)
        # Longer timeouts for model loading (7B models can take 30-60s)
        self.load_client = httpx.Client(timeout=120.0)

        # Track currently loaded instance for clean unload
        self._current_instance_id: str = None
        self._current_model_key: str = None

    # ─── Health Checks ──────────────────────────────────────────────

    def is_lmstudio_healthy(self) -> bool:
        """Quick health check: can we reach LM Studio at all?"""
        try:
            url = f"{self._host_base}/v1/models"
            resp = self.health_client.get(url)
            return resp.status_code == 200
        except Exception:
            return False

    def is_ollama_healthy(self) -> bool:
        """Quick health check: can we reach Ollama at all?"""
        try:
            base = self.ollama_url.replace("/v1", "")
            url = f"{base}/api/tags"
            resp = self.health_client.get(url)
            return resp.status_code == 200
        except Exception:
            return False

    # ─── LM Studio Native API: Model Discovery ─────────────────────

    def list_available_models(self) -> list:
        """List all models available in LM Studio (downloaded, not necessarily loaded)."""
        try:
            url = f"{self._host_base}/api/v1/models"
            resp = self.health_client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list available models: {e}")
            return []

    def list_loaded_instances(self) -> list:
        """
        List models currently loaded in memory by checking loaded_instances
        on each model from the native API.
        Returns list of dicts: [{model_key, instance_id, type}, ...]
        """
        loaded = []
        try:
            models = self.list_available_models()
            for model in models:
                instances = model.get("loaded_instances", [])
                for inst in instances:
                    loaded.append({
                        "model_key": model.get("key"),
                        "instance_id": inst.get("instance_id"),
                        "type": model.get("type"),
                        "display_name": model.get("display_name", model.get("key")),
                    })
            return loaded
        except Exception as e:
            logger.error(f"Failed to list loaded instances: {e}")
            return []

    # ─── LM Studio Native API: Load / Unload ───────────────────────

    def load_lm_studio_model(self, model_key: str, context_length: int = 4096) -> bool:
        """
        Load a model into LM Studio memory using the native API.
        First unloads all other models to free RAM.

        Args:
            model_key: The model identifier (e.g. 'qwen2-7b-instruct')
            context_length: Context window size (smaller = less RAM)

        Returns:
            True if model was loaded successfully
        """
        logger.info(f"[ModelLifecycle] Loading model: {model_key}")

        # Step 1: Unload everything first to free RAM
        self.unload_all_models()
        time.sleep(1)  # Brief pause for memory to be freed

        # Step 2: Load the target model
        url = f"{self._host_base}/api/v1/models/load"
        payload = {
            "model": model_key,
            "context_length": context_length,
        }

        try:
            logger.info(f"[ModelLifecycle] POST {url} with model={model_key}, ctx={context_length}")
            response = self.load_client.post(url, json=payload)

            if response.status_code == 200:
                result = response.json()
                # Extract instance_id for later unloading
                instance_id = result.get("instance_id")
                if instance_id:
                    self._current_instance_id = instance_id
                    self._current_model_key = model_key
                    logger.info(f"[ModelLifecycle] ✓ Loaded {model_key} (instance: {instance_id})")
                else:
                    # Try to discover instance_id from loaded list
                    self._current_model_key = model_key
                    loaded = self.list_loaded_instances()
                    for inst in loaded:
                        if inst["model_key"] == model_key:
                            self._current_instance_id = inst["instance_id"]
                            break
                    logger.info(f"[ModelLifecycle] ✓ Loaded {model_key} (discovered instance: {self._current_instance_id})")
                return True
            else:
                logger.warning(f"[ModelLifecycle] ✗ Load returned {response.status_code}: {response.text[:200]}")
                return False

        except httpx.TimeoutException:
            logger.warning(f"[ModelLifecycle] ✗ Load timed out for {model_key} (120s limit)")
            return False
        except httpx.RequestError as e:
            logger.error(f"[ModelLifecycle] ✗ Connection error during load: {e}")
            return False

    def unload_model(self, instance_id: str = None) -> bool:
        """
        Unload a specific model instance from LM Studio memory.

        Args:
            instance_id: The instance ID to unload. If None, unloads current tracked model.
        """
        target_id = instance_id or self._current_instance_id
        if not target_id:
            logger.debug("[ModelLifecycle] No model instance to unload")
            return True

        url = f"{self._host_base}/api/v1/models/unload"
        payload = {"instance_id": target_id}

        try:
            logger.info(f"[ModelLifecycle] Unloading instance: {target_id}")
            response = self.load_client.post(url, json=payload)

            if response.status_code == 200:
                logger.info(f"[ModelLifecycle] ✓ Unloaded instance {target_id}")
                if target_id == self._current_instance_id:
                    self._current_instance_id = None
                    self._current_model_key = None
                return True
            else:
                logger.warning(f"[ModelLifecycle] ✗ Unload returned {response.status_code}: {response.text[:200]}")
                return False

        except Exception as e:
            logger.error(f"[ModelLifecycle] ✗ Failed to unload: {e}")
            return False

    def unload_all_models(self) -> bool:
        """Unload ALL currently loaded model instances to free all RAM."""
        loaded = self.list_loaded_instances()
        if not loaded:
            logger.debug("[ModelLifecycle] No models currently loaded — RAM is free")
            return True

        logger.info(f"[ModelLifecycle] Unloading {len(loaded)} model(s) to free RAM...")
        all_success = True
        for inst in loaded:
            iid = inst.get("instance_id")
            name = inst.get("display_name", inst.get("model_key"))
            if iid:
                success = self.unload_model(iid)
                if success:
                    logger.info(f"[ModelLifecycle] ✓ Freed RAM from: {name}")
                else:
                    logger.warning(f"[ModelLifecycle] ✗ Failed to unload: {name}")
                    all_success = False

        self._current_instance_id = None
        self._current_model_key = None
        return all_success

    # ─── Ollama Model Management ────────────────────────────────────

    def ensure_ollama_model(self, model_name: str) -> bool:
        """Ensures an Ollama model is available. Uses a 15s timeout to prevent pipeline stalls."""
        import subprocess
        logger.info(f"Ensuring Ollama model {model_name} is active...")
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                check=False,
                capture_output=True,
                timeout=15
            )
            if result.returncode == 0:
                return True
            else:
                logger.warning(f"Ollama pull returned code {result.returncode}: {result.stderr.decode()}")
                return False
        except subprocess.TimeoutExpired:
            logger.warning(f"Ollama pull timed out for {model_name} (15s limit)")
            return False
        except FileNotFoundError:
            logger.warning("Ollama CLI not found in PATH")
            return False
        except Exception as e:
            logger.error(f"Failed to pull/run Ollama model via CLI: {e}")
            return False

    # ─── Context Manager for Clean Lifecycle ────────────────────────

    def model_context(self, model_key: str, context_length: int = 4096):
        """
        Context manager that loads a model on enter and unloads on exit.
        Usage:
            with local_manager.model_context("qwen2-7b-instruct"):
                # model is loaded, run inference
                result = router.generate(...)
            # model is automatically unloaded
        """
        return _ModelContext(self, model_key, context_length)


class _ModelContext:
    """Context manager for automatic model load/unload lifecycle."""

    def __init__(self, manager: LocalModelManager, model_key: str, context_length: int):
        self.manager = manager
        self.model_key = model_key
        self.context_length = context_length
        self.loaded = False

    def __enter__(self):
        self.loaded = self.manager.load_lm_studio_model(self.model_key, self.context_length)
        if not self.loaded:
            logger.warning(f"[ModelContext] Failed to load {self.model_key} — inference may use cloud fallback")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.loaded:
            self.manager.unload_model()
            logger.info(f"[ModelContext] Unloaded {self.model_key} — RAM freed")
        return False  # Don't suppress exceptions
