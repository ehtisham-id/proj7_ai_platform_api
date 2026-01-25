from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.job import Job
from app.tasks import process_summarization
from uuid import uuid4
import json

router = APIRouter(prefix="/summarize", tags=["Summarization"])

@router.post("/", response_model=dict)
async def summarize_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    text = content.decode('utf-8', errors='ignore')
    
    if len(text) > 100000:  # 100k char limit
        raise HTTPException(status_code=400, detail="Text too long")
    
    job_id = str(uuid4())
    
    # Create job record
    job = Job(
        id=job_id,
        user_id=current_user.id,
        task_type="summarization"
    )
    db.add(job)
    await db.commit()
    
    # Queue background task
    process_summarization.delay(job_id, text, current_user.id)
    
    return {"job_id": job_id, "status": "queued"}

@router.get("/jobs/{job_id}", response_model=dict)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "status": job.status,
        "result_url": job.result_url,
        "error": job.error_message
    }
