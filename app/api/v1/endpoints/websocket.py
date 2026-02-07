from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.security import _get_user_from_token
import asyncio
import json

router = APIRouter(prefix="/ws")

# Simple in-memory connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, user_email: str, websocket: WebSocket):
        self.active_connections[user_email] = websocket
    
    def disconnect(self, user_email: str):
        self.active_connections.pop(user_email, None)
    
    async def send_to_user(self, user_email: str, message: dict):
        if user_email in self.active_connections:
            await self.active_connections[user_email].send_json(message)
    
    async def broadcast(self, message: dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)

manager = ConnectionManager()

@router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
    
    try:
        async with AsyncSessionLocal() as db:
            current_user = await _get_user_from_token(token, db)
    except Exception as e:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    user_email = current_user.email
    await manager.connect(user_email, websocket)
    
    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "message": f"Welcome {user_email}!",
        "data": {"user": user_email, "status": "connected"}
    })
    
    try:
        while True:
            try:
                # Use asyncio.wait_for to add timeout and keep connection alive
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0  # 30 second timeout for heartbeat
                )
                # Echo back with confirmation
                await websocket.send_json({
                    "type": "message",
                    "message": f"Received from {user_email}",
                    "data": data
                })
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({
                    "type": "ping",
                    "message": "keepalive",
                    "data": {"timestamp": asyncio.get_event_loop().time()}
                })
    except WebSocketDisconnect:
        manager.disconnect(user_email)
    except Exception:
        manager.disconnect(user_email)
