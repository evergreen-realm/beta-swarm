"""Bugsink error monitoring client — silent-fail on monitoring errors."""

import os
import traceback
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BugsinkClient:
    def __init__(self):
        # Default to localhost:8001 (container port) or provided env
        self.dsn = os.getenv("BUGSINK_DSN", "http://localhost:8001/api/error/")
        # Enable if DSN is set or if we are in production mode
        self.enabled = bool(os.getenv("BUGSINK_DSN")) or os.getenv("ENVIRONMENT") == "production"

    def capture_exception(self, exc: Exception, context: Dict[str, Any] = None):
        if not self.enabled:
            logger.debug(f"Bugsink disabled. Skipping exception: {exc}")
            return
        try:
            payload = {
                "message": str(exc),
                "stacktrace": traceback.format_exc(),
                "context": context or {},
                "level": "error"
            }
            # Fire and forget / Silent fail
            requests.post(self.dsn, json=payload, timeout=2)
            logger.debug("Exception captured by Bugsink.")
        except Exception as e:
            logger.debug(f"Bugsink capture failed (silent): {e}")

    def capture_message(self, message: str, level: str = "info", context: Dict[str, Any] = None):
        if not self.enabled:
            return
        try:
            payload = {
                "message": message,
                "level": level,
                "context": context or {}
            }
            requests.post(self.dsn, json=payload, timeout=2)
        except Exception:
            pass

# Singleton instance
bugsink = BugsinkClient()
