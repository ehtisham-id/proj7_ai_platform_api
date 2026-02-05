from fastapi import APIRouter, Depends, UploadFile, File as FileParam, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file import File as FileModel
from app.services.minio_service import minio_service
from app.services.pdf_service import pdf_service
from sqlalchemy import select
from typing import List

router = APIRouter(prefix="/pdf", tags=["PDF Manipulation"])

@router.post("/merge", response_model=dict)
async def merge_pdfs(
    files: List[UploadFile] = FileParam(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 PDFs to merge")
    
    pdf_contents = []
    for file in files:
        if not file.content_type == "application/pdf":
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF")
        
        content = await file.read()
        pdf_contents.append(content)
    
    merged_pdf = pdf_service.merge_pdfs(pdf_contents)
    
    # Save merged PDF to MinIO
    object_name = minio_service.upload_file(
        filename="merged.pdf",
        file_content=merged_pdf,
        metadata={"operation": "pdf_merge", "user_id": str(current_user.id)}
    )
    
    # Save metadata
    db_file = FileModel(
        filename="merged.pdf",
        user_id=current_user.id,
        object_name=object_name,
        mime_type="application/pdf",
        size_bytes=len(merged_pdf)
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    
    return {"merged_file_id": db_file.id}

@router.post("/convert", response_model=dict)
async def convert_to_pdf(
    file: UploadFile = FileParam(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        pdf_content = pdf_service.file_to_pdf(content, file.content_type or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Save to MinIO
    object_name = minio_service.upload_file(
        filename=f"{file.filename.rsplit('.', 1)[0]}.pdf",
        file_content=pdf_content,
        metadata={"operation": "pdf_convert", "source": file.filename}
    )
    
    db_file = FileModel(
        filename=f"{file.filename.rsplit('.', 1)[0]}.pdf",
        user_id=current_user.id,
        object_name=object_name,
        mime_type="application/pdf",
        size_bytes=len(pdf_content)
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    
    return {"pdf_file_id": db_file.id}
