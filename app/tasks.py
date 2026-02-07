from celery_app import app
from app.services.summarization_service import summarization_service
from app.services.minio_service import minio_service
from app.models.job import Job, JobStatus
from app.core.config import settings
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Sync engine for Celery tasks (asyncpg doesn't work in sync context)
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
sync_engine = create_engine(sync_db_url)

@app.task(bind=True, max_retries=3)
def process_summarization(self, job_id: str, text: str, user_id: int):
    """Background summarization task."""
    try:
        # Generate summary
        summary = summarization_service.extractive_summary(text)
        
        # Save summary to MinIO
        filename = f"summary_{job_id}.txt"
        summary_bytes = summary.encode('utf-8')
        object_name = minio_service.upload_file(
            filename=filename,
            file_content=summary_bytes,
            metadata={'type': 'summarization_result', 'job_id': job_id}
        )
        result_url = minio_service.get_presigned_url(object_name)
        
        # Update job in DB using sync session
        with Session(sync_engine) as db:
            job = db.get(Job, job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.result_url = result_url
                db.commit()
        
        return {"job_id": job_id, "result_url": result_url, "status": "completed"}
        
    except Exception as exc:
        # Update job as failed
        with Session(sync_engine) as db:
            job = db.get(Job, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                db.commit()
        
        raise self.retry(exc=exc, countdown=5)
