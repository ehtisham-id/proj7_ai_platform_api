from celery_app import app
from app.services.summarization_service import summarization_service
from app.services.minio_service import minio_service
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine
from app.models.job import Job
from sqlalchemy import select

@app.task(bind=True)
def process_summarization(self, job_id: str, text: str, user_id: int):
    """Background summarization task."""
    try:
        # Update job status
        summary = summarization_service.extractive_summary(text)
        
        # Save summary to MinIO
        filename = f"summary_{job_id}.txt"
        summary_bytes = summary.encode('utf-8')
        object_name = minio_service.upload_file(
            filename=filename,
            file_content=summary_bytes,
            metadata={'type': 'summarization_result'}
        )
        result_url = minio_service.get_presigned_url(object_name)
        
        # Update job in DB
        async def update_job():
            async with AsyncSession(engine) as db:
                job = await db.get(Job, job_id)
                if job:
                    job.status = JobStatus.COMPLETED
                    job.result_url = result_url
                    await db.commit()
        
        import asyncio
        asyncio.run(update_job())
        
        # Send Kafka notification
        from kafka import KafkaProducer
        producer = KafkaProducer(bootstrap_servers=['localhost:9092'])
        producer.send('job.completed', {
            'job_id': job_id,
            'user_id': user_id,
            'status': 'completed'
        })
        
        return result_url
        
    except Exception as exc:
        # Update job as failed
        async def mark_failed():
            async with AsyncSession(engine) as db:
                job = await db.get(Job, job_id)
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(exc)
                    await db.commit()
        
        import asyncio
        asyncio.run(mark_failed())
        raise self.retry(exc=exc)
