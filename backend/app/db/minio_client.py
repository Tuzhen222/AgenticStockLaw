"""
MinIO client configuration for object storage.
"""
import os
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

# MinIO connection settings - use env vars for flexibility
MINIO_HOST = os.environ.get("MINIO_HOST", "minio")
MINIO_PORT = int(os.environ.get("MINIO_PORT", "9000"))
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"

# Default bucket for documents
DOCUMENTS_BUCKET = "documents"


def get_minio_client() -> Minio:
    """Create and return a MinIO client instance."""
    endpoint = f"{MINIO_HOST}:{MINIO_PORT}"
    print(f"[MinIO] Creating client for endpoint: {endpoint}")
    
    return Minio(
        endpoint,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def ensure_bucket_exists(client: Minio, bucket_name: str = DOCUMENTS_BUCKET) -> None:
    """Create bucket if it doesn't exist."""
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Created bucket: {bucket_name}")
    except S3Error as e:
        print(f"Error checking/creating bucket: {e}")
        raise
