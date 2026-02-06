from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.security import _get_user_from_token

router = APIRouter(prefix="/ws")

@router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        async with AsyncSessionLocal() as db:
            current_user = await _get_user_from_token(token, db)
    except Exception:
        await websocket.close(code=1008)
        return
    try:
        while True:
            # Listen for Kafka messages (simplified)
            data = await websocket.receive_json()
            await websocket.send_json({"message": f"Notification for {current_user.email}", "data": data})
    except WebSocketDisconnect:
        pass
