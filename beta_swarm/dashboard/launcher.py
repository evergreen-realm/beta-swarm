import uvicorn
import logging

def run_web():
    """Run the FastAPI web server."""
    # We import inside to avoid circular deps and allow multiprocessing pickling
    from beta_swarm.dashboard.web_server import app
    import os
    port = int(os.environ.get("PORT", 8991))
    print(f"Dashboard Web Server starting on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

def run_tui():
    """Run the Textual TUI."""
    from beta_swarm.dashboard.tui_app import SwarmDashboard
    app = SwarmDashboard()
    app.run()
