import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from win10toast import ToastNotifier
    _HAS_WIN10TOAST = True
except ImportError:
    _HAS_WIN10TOAST = False

try:
    from plyer import notification
    _HAS_PLYER = True
except ImportError:
    _HAS_PLYER = False

class SwarmNotifier:
    """Desktop notification system for critical swarm events."""
    
    def __init__(self):
        self.toaster = ToastNotifier() if _HAS_WIN10TOAST else None

    def notify(self, title: str, message: str, icon_path: Optional[str] = None):
        """Send a desktop notification."""
        logger.info(f"NOTIFICATION: {title} - {message}")
        
        try:
            if os.name == 'nt' and self.toaster:
                # Windows 10 native toast
                self.toaster.show_toast(
                    title,
                    message,
                    icon_path=icon_path,
                    duration=5,
                    threaded=True
                )
            elif _HAS_PLYER:
                # Cross-platform fallback
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Beta Swarm JARVIS",
                    timeout=5
                )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def alert_error(self, agent_id: str, error: str):
        self.notify(f"⚠️ AGENT ERROR: {agent_id}", f"Reason: {error[:50]}")

    def alert_complete(self, project_name: str):
        self.notify("✅ PIPELINE COMPLETE", f"Project '{project_name}' has been successfully deployed.")
