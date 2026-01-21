"""
Document Service - Handles document operations with MinIO storage.
"""
from datetime import timedelta
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.db.minio_client import DOCUMENTS_BUCKET, ensure_bucket_exists, get_minio_client


class DocumentService:
    """Service for managing documents in MinIO."""

    def __init__(self):
        self._client: Optional[Minio] = None
        self.bucket = DOCUMENTS_BUCKET

    @property
    def client(self) -> Minio:
        """Lazy initialization of MinIO client."""
        if self._client is None:
            self._client = get_minio_client()
        return self._client

    def ensure_bucket(self) -> None:
        """Ensure the documents bucket exists."""
        ensure_bucket_exists(self.client, self.bucket)

    def list_documents(self, prefix: str = "") -> list[dict]:
        """
        List all documents in the bucket.
        
        Args:
            prefix: Optional prefix to filter documents.
            
        Returns:
            List of document metadata dictionaries.
        """
        try:
            # First ensure bucket exists
            self.ensure_bucket()
            
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            documents = []
            for obj in objects:
                documents.append({
                    "id": obj.object_name,
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag,
                })
            return documents
        except S3Error as e:
            print(f"Error listing documents: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error listing documents: {e}")
            return []

    def get_download_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for downloading a document.
        
        Args:
            object_name: Name of the object in MinIO.
            expires: URL expiration time in seconds (default: 1 hour).
            
        Returns:
            Presigned URL string or None if error.
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires),
            )
            # Replace internal hostname with localhost for browser access
            # This handles the case where MinIO returns internal Docker hostname
            url = url.replace("agentic-minio:9000", "localhost:9000")
            url = url.replace("agentic_minio:9000", "localhost:9000")  # fallback
            return url
        except S3Error as e:
            print(f"Error generating download URL: {e}")
            return None

    def upload_document(
        self,
        file_path: str,
        object_name: str,
        content_type: str = "text/plain",
    ) -> bool:
        """
        Upload a document to MinIO.
        
        Args:
            file_path: Path to the local file.
            object_name: Name to store the object as in MinIO.
            content_type: MIME type of the file.
            
        Returns:
            True if upload successful, False otherwise.
        """
        try:
            self.ensure_bucket()
            self.client.fput_object(
                self.bucket,
                object_name,
                file_path,
                content_type=content_type,
            )
            return True
        except S3Error as e:
            print(f"Error uploading document: {e}")
            return False

    def document_exists(self, object_name: str) -> bool:
        """Check if a document exists in the bucket."""
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False


# Singleton instance (lazy initialized)
document_service = DocumentService()
