import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
build_router = APIRouter()

class BuildConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                continue

manager = BuildConnectionManager()

@build_router.websocket("/ws/build")
async def websocket_build_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive and handle incoming commands if necessary
            data = await websocket.receive_text()
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket build error: {e}")
        manager.disconnect(websocket)

# Method to broadcast events from backend engine
async def emit_build_event(event_type: str, payload: dict):
    message = {"type": event_type}
    message.update(payload)
    await manager.broadcast(message)
