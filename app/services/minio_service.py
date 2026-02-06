from minio import Minio
from minio.error import S3Error
import io
import logging
from app.core.config import settings
from typing import Optional
from datetime import timedelta
from urllib.parse import urlparse, urlunparse
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
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as exc:
            logging.getLogger(__name__).warning(
                "MinIO bucket check failed: %s", exc
            )
    
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
        # MinIO expects a timedelta for expires; accept int seconds for convenience.
        exp = timedelta(seconds=expires) if isinstance(expires, int) else expires
        url = self.client.presigned_get_object(self.bucket, object_name, expires=exp)
        public = settings.MINIO_PUBLIC_ENDPOINT
        if public and public != settings.MINIO_ENDPOINT:
            # Replace host with the public endpoint for browser access
            parsed = urlparse(url)
            netloc = public
            # If public includes scheme, preserve it
            if "://" in public:
                pub_parsed = urlparse(public)
                netloc = pub_parsed.netloc or pub_parsed.path
                parsed = parsed._replace(scheme=pub_parsed.scheme or parsed.scheme)
            url = urlunparse(parsed._replace(netloc=netloc))
        return url

minio_service = MinIOService()
