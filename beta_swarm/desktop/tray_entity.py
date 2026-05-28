import os
import sys

# Ensure the project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import time
import threading
import webbrowser
import subprocess
from PIL import Image
import pystray
from pystray import MenuItem as item

from beta_swarm.desktop.wake_sequence import WakeSequence
from beta_swarm.desktop.health_orchestrator import HealthOrchestrator
from beta_swarm.desktop.obsidian_logger import ObsidianLogger

class SwarmEntity:
    """The Living Icon - Optimized System Tray Entity for Beta Swarm."""
    
    def __init__(self):
        self.assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        self._ensure_assets()
        
        self.health = HealthOrchestrator()
        self.logger = ObsidianLogger()
        self.state = "idle" # idle, waking, active
        self.frame_idx = 0
        self.icon = None
        self.running = True
        
        # Preload frames into RAM to eliminate Disk I/O bottlenecks
        self._frames = {"idle": [], "wake": [], "active": []}
        self._preload_frames()

    def _ensure_assets(self):
        """Auto-generate frames on first run if missing."""
        if not os.path.exists(os.path.join(self.assets_dir, "orb_idle_0.png")):
            print("First run: generating orb assets...")
            script_path = os.path.join(os.path.dirname(__file__), "generate_orb_assets.py")
            subprocess.run([sys.executable, script_path], check=True)

    def _preload_frames(self):
        """Load all PNGs into memory once at startup."""
        print("Preloading entity assets...")
        for state in self._frames:
            for i in range(30):
                path = os.path.join(self.assets_dir, f"orb_{state}_{i}.png")
                if os.path.exists(path):
                    self._frames[state].append(Image.open(path).convert("RGBA"))
                else:
                    self._frames[state].append(Image.new("RGBA", (64, 64), (0, 0, 0, 0)))
        print("Assets ready.")

    def _animate(self):
        """Animation loop for the tray icon (Optimized to 15 FPS)."""
        while self.running:
            if self.icon:
                current_state = "idle" if self.state != "active" else "active"
                # If waking, use wake frames but we handle overlay separately
                state_to_draw = "wake" if self.state == "waking" else current_state
                
                # Zero-Disk-IO Icon Update
                self.icon.icon = self._frames[state_to_draw][self.frame_idx % 30]
                self.frame_idx = (self.frame_idx + 1) % 30
            
            # Reduce CPU usage by sleeping 66ms (15 FPS)
            time.sleep(0.066)

    def wake_swarm(self):
        """Trigger the wake sequence (Non-blocking)."""
        if self.state == "active": return
        
        self.logger.log_action("Wake Swarm", status="WAKING")
        self.state = "waking"
        self.frame_idx = 0
        
        # Play non-blocking overlay animation
        seq = WakeSequence(self.assets_dir)
        seq.play()
        
        # Immediate state transition to active after trigger
        self.state = "active"
        
        try:
            from beta_swarm.desktop.native_window import launch_native_window
            port = int(os.environ.get("PORT", 8999))
            launch_native_window(port)
        except ImportError:
            port = int(os.environ.get("PORT", 8999))
            webbrowser.open(f"http://127.0.0.1:{port}")
            
        self.logger.log_action("Swarm Awakened", status="ACTIVE")

    def open_galaxy(self):
        """Open the 3D Galaxy View (Default action)"""
        self.logger.log_action("Open Galaxy")
        subprocess.Popen([sys.executable, "-m", "beta_swarm.desktop.galaxy_window"], cwd=r"C:\Users\Admin\Documents\Beta Swarnv2")
        
    def open_dashboard(self):
        """Open Native Dashboard"""
        self.logger.log_action("Open Dashboard")
        subprocess.Popen([sys.executable, "-m", "beta_swarm.desktop.native_window"], cwd=r"C:\Users\Admin\Documents\Beta Swarnv2")
        self.state = "active"

    def toggle_voice(self, icon, item):
        self.voice_enabled = not getattr(self, "voice_enabled", False)
        if self.voice_enabled:
            self.logger.log_action("Voice Engine Started")
            self.voice_process = subprocess.Popen([sys.executable, "-m", "beta_swarm.desktop.voice_engine"], cwd=r"C:\Users\Admin\Documents\Beta Swarnv2")
        else:
            self.logger.log_action("Voice Engine Stopped")
            if hasattr(self, "voice_process"):
                self.voice_process.terminate()

    def get_voice_state(self, item):
        return getattr(self, "voice_enabled", False)

    def show_status(self):
        results = self.health.run_all_checks()
        status_msg = " | ".join([f"{k}: {'OK' if v else '!!'}" for k, v in results.items()])
        self.logger.log_action(f"Audit: {status_msg}")

    def on_quit(self, icon, item):
        self.running = False
        if getattr(self, "voice_enabled", False) and hasattr(self, "voice_process"):
            self.voice_process.terminate()
        self.logger.generate_summary()
        icon.stop()

    def run(self):
        self.voice_enabled = False
        menu = pystray.Menu(
            item("Open Galaxy", self.open_galaxy, default=True),
            item("Open Dashboard", self.open_dashboard),
            item("System Status", self.show_status),
            item("View Log", lambda: os.startfile(self.logger.daily_notes_dir)),
            item("Voice Commands", self.toggle_voice, checked=self.get_voice_state),
            pystray.Menu.SEPARATOR,
            item("Sleep", lambda: setattr(self, 'state', 'idle')),
            item("Quit", self.on_quit)
        )
        
        self.icon = pystray.Icon("BetaSwarm", self._frames["idle"][0], "BETA SWARM V3.2", menu)
        threading.Thread(target=self._animate, daemon=True).start()
        self.icon.run()

if __name__ == "__main__":
    entity = SwarmEntity()
    entity.run()
