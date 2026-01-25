from fastapi import APIRouter
from .auth import router as auth_router

router = APIRouter()
router.include_router(auth_router)


# In app/api/v1/endpoints/__init__.py
from .files import router as files_router
router.include_router(files_router)

from .pdf import router as pdf_router
router.include_router(pdf_router)

from .qr import router as qr_router
router.include_router(qr_router)

from .ar import router as ar_router
router.include_router(ar_router)

from .photo import router as photo_router
router.include_router(photo_router)


from .convert import router as convert_router
router.include_router(convert_router)

from .analysis import router as analysis_router
router.include_router(analysis_router)

# Include new routers
from .summarize import router as summarize_router
from .websocket import router as ws_router
router.include_router(summarize_router)
router.include_router(ws_router)

# Add to main.py
app.mount("/ws", app=websocket_app)  # Simplified WS mounting
