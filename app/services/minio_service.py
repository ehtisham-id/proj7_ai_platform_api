from minio import Minio
from minio.error import S3Error
import io
from app.core.config import settings
from typing import Optional
import uuid
import os

class MinIOService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False  # Set True in production with HTTPS
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
    
    def upload_file(self, filename: str, file_content: bytes, metadata: dict = None) -> str:
        object_name = f"{uuid.uuid4()}/{filename}"
        self.client.put_object(
            self.bucket, object_name, io.BytesIO(file_content),
            length=len(file_content),
            metadata=metadata
        )
        return object_name
    
    def download_file(self, object_name: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(self.bucket, object_name)
            return response.read()
        except S3Error:
            return None
    
    def delete_file(self, object_name: str):
        self.client.remove_object(self.bucket, object_name)
    
    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        return self.client.presigned_get_object(self.bucket, object_name, expires=expires)

minio_service = MinIOService()
