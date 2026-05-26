import webview
import threading
import uvicorn
import time
import sys
import os
import socket

# Add project to path
sys.path.insert(0, r"C:\Users\Admin\Documents\Beta Swarnv2")

from beta_swarm.dashboard.web_server import app

import subprocess

PORT = int(os.environ.get("PORT", 8999))

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

if not is_port_in_use(PORT):
    print(f"Starting background web server as subprocess on port {PORT}...")
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    subprocess.Popen([sys.executable, "-m", "beta_swarm.dashboard.web_server"], env=env, cwd=r"C:\Users\Admin\Documents\Beta Swarnv2")
    time.sleep(5)
else:
    print(f"Server already running on port {PORT}. Connecting to existing instance...")

# Loading screen with subtle orb
loading_html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  background: #0d1117;
  display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  height: 100vh; font-family: -apple-system, sans-serif;
}}
.orb {{
  width: 48px; height: 48px; border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #2f81f7, #1f6feb);
  box-shadow: 0 0 40px rgba(47,129,247,0.3);
  animation: breathe 2.5s ease-in-out infinite;
}}
@keyframes breathe {{
  0%, 100% {{ transform: scale(1); opacity: 0.7; }}
  50% {{ transform: scale(1.15); opacity: 1; }}
}}
.label {{
  margin-top: 24px; color: #8b949e;
  font-size: 13px; letter-spacing: 0.05em;
}}
</style>
</head>
<body>
<div class="orb"></div>
<div class="label">BETA SWARM V3.2</div>
<script>
setTimeout(() => {{ window.location = 'http://127.0.0.1:{PORT}'; }}, 3000);
</script>
</body>
</html>
"""

def launch_native_window(port=None):
    if port is None:
        port = PORT
    window = webview.create_window(
        "Beta Swarm",
        url=f"http://127.0.0.1:{port}",  # Navigate directly to URL instead of using loading_html since server is fully loaded after 5s!
        width=1440,
        height=900,
        min_size=(900, 600),
        resizable=True,
        text_select=False,
        confirm_close=True
    )
    webview.start(debug=False)

if __name__ == "__main__":
    launch_native_window()
