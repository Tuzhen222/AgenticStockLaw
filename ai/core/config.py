"""Configuration settings for AI module."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """AI module settings loaded from environment variables."""

    # Triton Inference Server
    triton_url: str = "http://localhost:8001"
    triton_model_name: str = "bge-m3"
    embedding_dim: int = 1024  # BGE-M3 dimension

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "legal-documents"
    minio_secure: bool = False

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "legal_law"

    # Data paths
    data_dir: str = "./data"
    ingest_file: str = "./data/ingest.jsonl"

    class Config:
        env_prefix = "AI_"
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
