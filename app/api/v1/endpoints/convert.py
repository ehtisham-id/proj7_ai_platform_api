from fastapi import APIRouter, Depends, UploadFile, File as FileParam, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import File as FileModel
from app.services.minio_service import minio_service
from app.services.conversion_service import conversion_service
from app.schemas.conversion import ConversionRequest
import mimetypes
import uuid
from typing import Dict, Any
import os

router = APIRouter(prefix="/convert", tags=["File Conversions"])

@router.post("/", response_model=dict)
async def convert_file(
    conversion: str = Form(...),
    file: UploadFile = FileParam(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=400, detail="File too large")
    
    # Detect source format
    source_mime, _ = mimetypes.guess_type(file.filename)
    source_format = file.content_type.split('/')[-1] if file.content_type else file.filename.split('.')[-1]
    
    try:
        # parse conversion JSON from form field
        conversion_obj = ConversionRequest.parse_raw(conversion)

        converted_content = conversion_service.convert_file(
            file_content=content,
            source_format=source_format,
            target_format=conversion_obj.target_format
        )
        
        # Generate filename
        name, ext = os.path.splitext(file.filename)
        target_ext = f".{conversion_obj.target_format}"
        new_filename = f"{name}_converted{target_ext}"
        
        # Save to MinIO
        object_name = minio_service.upload_file(
            filename=new_filename,
            file_content=converted_content,
            metadata={
                'operation': 'file_conversion',
                'source': file.filename,
                'target_format': conversion_obj.target_format,
                'user_id': str(current_user.id)
            }
        )
        
        # Save metadata
        db_file = FileModel(
            filename=new_filename,
            user_id=current_user.id,
            object_name=object_name,
            mime_type=f"application/{conversion_obj.target_format}" if conversion_obj.target_format != 'pdf' else 'application/pdf',
            size_bytes=len(converted_content)
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        url = minio_service.get_presigned_url(object_name)
        
        return {
            "converted_file_id": db_file.id,
            "url": url,
            "filename": new_filename,
            "source_format": source_format,
            "target_format": conversion_obj.target_format,
            "size_bytes": len(converted_content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
