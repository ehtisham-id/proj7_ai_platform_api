from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ws")

@router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket, current_user: User = Depends(get_current_user)):
    await websocket.accept()
    try:
        while True:
            # Listen for Kafka messages (simplified)
            data = await websocket.receive_json()
            await websocket.send_json({"message": f"Notification for {current_user.email}", "data": data})
    except WebSocketDisconnect:
        pass
