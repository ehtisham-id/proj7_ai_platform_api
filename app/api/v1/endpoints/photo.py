from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import File
from app.services.minio_service import minio_service
from app.services.photo_service import photo_service
from app.schemas.photo import PhotoEdit
import uuid
from typing import Dict, Any

router = APIRouter(prefix="/photo", tags=["Photo Editing"])

@router.post("/edit", response_model=dict)
async def edit_photo(
    file: UploadFile = File(...),
    operations: PhotoEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate image
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files supported")
    
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        # Process image
        processed_image = photo_service.process_photo(content, operations.dict(exclude_unset=True))
        
        # Save to MinIO
        filename = f"edited_{uuid.uuid4().hex[:8]}_{file.filename}"
        object_name = minio_service.upload_file(
            filename=filename,
            file_content=processed_image,
            metadata={
                'operation': 'photo_edit',
                'original': file.filename,
                'filter': operations.filter,
                'rotate': str(operations.rotate),
                'user_id': str(current_user.id)
            }
        )
        
        # Save metadata
        db_file = File(
            filename=filename,
            user_id=current_user.id,
            object_name=object_name,
            mime_type="image/jpeg",
            size_bytes=len(processed_image)
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        url = minio_service.get_presigned_url(object_name)
        
        return {
            "edited_file_id": db_file.id,
            "url": url,
            "filename": filename,
            "operations": operations.dict(exclude_unset=True),
            "size_bytes": len(processed_image)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Photo processing failed: {str(e)}")
