from fastapi import APIRouter

from .auth import router as auth_router
from .files import router as files_router
from .pdf import router as pdf_router
from .qr import router as qr_router
from .ar import router as ar_router
from .photo import router as photo_router
from .convert import router as convert_router
from .analysis import router as analysis_router
from .summarize import router as summarize_router
from .websocket import router as websocket_router

router = APIRouter()

routers = [
    auth_router,
    files_router,
    pdf_router,
    qr_router,
    ar_router,
    photo_router,
    convert_router,
    analysis_router,
    summarize_router,
    websocket_router,
]

for r in routers:
    router.include_router(r)
