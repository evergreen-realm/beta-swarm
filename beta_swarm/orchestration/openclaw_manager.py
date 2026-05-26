"""
OpenClaw Manager — Real integration with the OpenClaw AI agent platform.

OpenClaw is used in Beta Swarm for:
1. LM Studio recovery: restart/reconnect when the REST API is unresponsive
2. Browser automation: interact with LM Studio GUI as fallback for model management
3. Process management: kill/restart stuck model server processes

Requires: npm install -g openclaw@latest (Node.js based)
Fallback: Uses subprocess-based process management if OpenClaw CLI is not available.
"""

import os
import subprocess
import logging
import time
import httpx

logger = logging.getLogger(__name__)


class OpenClawManager:
    """
    Manages OpenClaw CLI interactions for LM Studio recovery and automation.

    OpenClaw capabilities used:
    - Process management (restart LM Studio server)
    - Health monitoring (check if model servers are responsive)
    - Fallback automation when REST APIs fail
    """

    def __init__(self):
        self.lm_studio_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        self._host_base = self.lm_studio_url.replace("/v1", "")
        self._openclaw_available = self._check_openclaw_installed()
        self._client = httpx.Client(timeout=10.0)

    def _check_openclaw_installed(self) -> bool:
        """Check if OpenClaw CLI is available in PATH."""
        try:
            result = subprocess.run(
                ["npx", "openclaw", "--version"],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"[OpenClaw] CLI available: v{version}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        logger.info("[OpenClaw] CLI not found — using subprocess fallback mode")
        return False

    # ─── LM Studio Recovery ─────────────────────────────────────────

    def force_unload_all_via_api(self) -> bool:
        """
        Force unload all models via LM Studio's native REST API.
        This is the first recovery step before resorting to process restart.
        """
        logger.info("[OpenClaw] Force-unloading all models via REST API...")
        try:
            # Get all loaded instances
            resp = self._client.get(f"{self._host_base}/api/v1/models")
            resp.raise_for_status()
            models = resp.json().get("models", [])

            unloaded = 0
            for model in models:
                for inst in model.get("loaded_instances", []):
                    iid = inst.get("instance_id")
                    if iid:
                        try:
                            self._client.post(
                                f"{self._host_base}/api/v1/models/unload",
                                json={"instance_id": iid}
                            )
                            logger.info(f"[OpenClaw] Unloaded: {model.get('key')} ({iid})")
                            unloaded += 1
                        except Exception as e:
                            logger.warning(f"[OpenClaw] Failed to unload {iid}: {e}")

            logger.info(f"[OpenClaw] Force-unloaded {unloaded} model(s)")
            return True
        except Exception as e:
            logger.error(f"[OpenClaw] REST API force-unload failed: {e}")
            return False

    def fallback_recover_lm_studio(self) -> bool:
        """
        Recovery sequence for LM Studio when REST API is completely unresponsive.

        Recovery order:
        1. Try REST API force-unload (least disruptive)
        2. Kill and restart LM Studio process (nuclear option)
        3. Wait for LM Studio to come back online
        """
        logger.warning("[OpenClaw] ⚠ Initiating LM Studio recovery sequence...")

        # Step 1: Try REST API unload first
        if self._is_lm_studio_responsive():
            logger.info("[OpenClaw] LM Studio API is responsive — trying API unload")
            if self.force_unload_all_via_api():
                return True

        # Step 2: Kill and restart the LM Studio process
        logger.warning("[OpenClaw] REST API unresponsive — restarting LM Studio process")
        return self._restart_lm_studio_process()

    def _is_lm_studio_responsive(self) -> bool:
        """Check if LM Studio API responds at all."""
        try:
            resp = self._client.get(f"{self._host_base}/v1/models")
            return resp.status_code == 200
        except Exception:
            return False

    def _restart_lm_studio_process(self) -> bool:
        """
        Kill all LM Studio processes and wait for user to restart,
        or attempt to relaunch if the executable path is known.
        """
        if os.name == 'nt':
            # Windows: taskkill
            try:
                logger.info("[OpenClaw] Killing LM Studio processes (Windows)...")
                subprocess.run(
                    ["taskkill", "/IM", "LM Studio.exe", "/F"],
                    capture_output=True, text=True, timeout=10
                )
                time.sleep(3)

                # Try to find and relaunch LM Studio
                lm_paths = [
                    os.path.expandvars(r"%LOCALAPPDATA%\LM Studio\LM Studio.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\LM Studio\LM Studio.exe"),
                ]
                for path in lm_paths:
                    if os.path.exists(path):
                        logger.info(f"[OpenClaw] Relaunching LM Studio from: {path}")
                        subprocess.Popen([path], creationflags=subprocess.CREATE_NO_WINDOW)
                        # Wait for it to start
                        return self._wait_for_lm_studio(timeout=60)

                logger.warning("[OpenClaw] LM Studio executable not found — please restart manually")
                return False

            except Exception as e:
                logger.error(f"[OpenClaw] Process restart failed: {e}")
                return False
        else:
            # Linux/WSL: systemctl or pkill
            try:
                subprocess.run(["pkill", "-f", "lm-studio"], capture_output=True, timeout=5)
                time.sleep(2)
                logger.warning("[OpenClaw] LM Studio killed — please restart manually")
                return False
            except Exception as e:
                logger.error(f"[OpenClaw] Linux kill failed: {e}")
                return False

    def _wait_for_lm_studio(self, timeout: int = 60) -> bool:
        """Wait for LM Studio to become responsive after restart."""
        logger.info(f"[OpenClaw] Waiting up to {timeout}s for LM Studio to start...")
        start = time.time()
        while time.time() - start < timeout:
            if self._is_lm_studio_responsive():
                logger.info("[OpenClaw] ✓ LM Studio is back online!")
                return True
            time.sleep(2)
        logger.error(f"[OpenClaw] ✗ LM Studio did not respond within {timeout}s")
        return False

    # ─── Ollama Recovery ────────────────────────────────────────────

    def fallback_recover_ollama(self) -> bool:
        """
        Uses system commands to restart Ollama service.
        """
        logger.warning("[OpenClaw] Initiating Ollama recovery...")
        try:
            if os.name == 'nt':
                # Windows: restart Ollama service
                subprocess.run(
                    ["net", "stop", "ollama"],
                    capture_output=True, timeout=10
                )
                time.sleep(2)
                subprocess.run(
                    ["net", "start", "ollama"],
                    capture_output=True, timeout=10
                )
            else:
                subprocess.run(
                    ["systemctl", "restart", "ollama"],
                    capture_output=True, timeout=10
                )
            time.sleep(3)
            logger.info("[OpenClaw] ✓ Ollama restart command issued")
            return True
        except Exception as e:
            logger.error(f"[OpenClaw] Ollama recovery failed: {e}")
            return False

    # ─── Status Reporting ───────────────────────────────────────────

    def get_system_status(self) -> dict:
        """Get current status of all managed services."""
        return {
            "openclaw_available": self._openclaw_available,
            "lm_studio_responsive": self._is_lm_studio_responsive(),
            "lm_studio_url": self._host_base,
        }
