from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FileParam, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import File as FileModel
from app.models.file_version import FileVersion
from app.services.minio_service import minio_service
from app.schemas.file import FileOut, FileVersionOut, FileRename
import uuid
from typing import List

router = APIRouter(prefix="/files", tags=["File Management"])

@router.post("/", response_model=FileOut, status_code=201)
async def upload_file(
    file: UploadFile = FileParam(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate file
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Invalid file")
    
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100MB limit
        raise HTTPException(status_code=400, detail="File too large")
    
    # Upload to MinIO
    object_name = minio_service.upload_file(
        filename=file.filename,
        file_content=content,
        metadata={"user_id": str(current_user.id)}
    )
    
    # Save metadata to DB
    db_file = FileModel(
        filename=file.filename,
        user_id=current_user.id,
        object_name=object_name,
        mime_type=file.content_type,
        size_bytes=len(content)
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    return db_file

@router.get("/{file_id}", response_class=Response)
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileModel).where(FileModel.id == file_id, FileModel.user_id == current_user.id)
    )
    db_file = result.scalar_one_or_none()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_content = minio_service.download_file(db_file.object_name)
    if not file_content:
        raise HTTPException(status_code=404, detail="File not found in storage")
    
    return Response(
        content=file_content,
        media_type=db_file.mime_type,
        headers={"Content-Disposition": f"attachment; filename={db_file.filename}"}
    )

@router.delete("/{file_id}", status_code=200)
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileModel).where(FileModel.id == file_id, FileModel.user_id == current_user.id)
    )
    db_file = result.scalar_one_or_none()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    minio_service.delete_file(db_file.object_name)
    await db.delete(db_file)
    await db.commit()
    return {"status": "success"}

@router.put("/{file_id}/rename", response_model=FileOut)
async def rename_file(
    file_id: int,
    rename_data: FileRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileModel).where(FileModel.id == file_id, FileModel.user_id == current_user.id)
    )
    db_file = result.scalar_one_or_none()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    db_file.filename = rename_data.new_name
    await db.commit()
    await db.refresh(db_file)
    return db_file

@router.get("/{file_id}/versions", response_model=List[FileVersionOut])
async def get_versions(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FileVersion).where(FileVersion.file_id == file_id)
    )
    versions = result.scalars().all()
    return versions
