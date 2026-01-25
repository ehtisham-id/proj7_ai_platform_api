from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import File
from app.services.minio_service import minio_service
from app.services.qr_service import qr_service
from app.schemas.qr import QRGenerate
from app.schemas.file import FileOut

router = APIRouter(prefix="/qrcode", tags=["QR Code Generation"])

@router.post("/generate", response_model=dict)
async def generate_qr(
    qr_data: QRGenerate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        qr_image = qr_service.generate_qr(**qr_data.dict())
        
        # Save to MinIO
        filename = f"qr_{uuid.uuid4().hex[:8]}.png"
        object_name = minio_service.upload_file(
            filename=filename,
            file_content=qr_image,
            metadata={
                "operation": "qr_generate",
                "text": qr_data.text[:100],
                "size": str(qr_data.size),
                "user_id": str(current_user.id)
            }
        )
        
        # Save metadata to DB
        db_file = File(
            filename=filename,
            user_id=current_user.id,
            object_name=object_name,
            mime_type="image/png",
            size_bytes=len(qr_image)
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        # Get presigned URL
        url = minio_service.get_presigned_url(object_name)
        
        return {
            "qrcode_file_id": db_file.id,
            "url": url,
            "filename": db_file.filename,
            "size": qr_data.size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QR generation failed: {str(e)}")
