# web_server.py - Legacy redirect to new unified dashboard_ws_server.py
from beta_swarm.dashboard.dashboard_ws_server import app

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8999))
    uvicorn.run(app, host="127.0.0.1", port=port)
