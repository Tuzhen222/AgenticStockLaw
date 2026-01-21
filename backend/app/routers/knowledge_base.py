"""
Knowledge Base Router - Fetches Qdrant collections as knowledge bases and documents from MinIO.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from app.services.document_service import document_service

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])

# Qdrant connection - use environment variable or container name from docker-compose
import os
QDRANT_HOST = os.environ.get("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))


class Document(BaseModel):
    """Document schema."""
    id: str
    name: str
    size: int
    last_modified: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Response schema for listing documents."""
    documents: list[Document]
    total: int


class DownloadResponse(BaseModel):
    """Response schema for download URL."""
    download_url: str
    filename: str


class KnowledgeBase(BaseModel):
    """Knowledge base schema."""
    id: str
    name: str
    type: str = "Qdrant"
    files: int = 0
    chunks: int = 0
    favorite: bool = False
    expanded: bool = False


class KnowledgeBaseListResponse(BaseModel):
    """Response schema for listing knowledge bases."""
    knowledge_bases: list[KnowledgeBase]
    total: int


@router.get("", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases():
    """
    List all Qdrant collections as knowledge bases.
    """
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=5)
        collections = client.get_collections().collections
        
        knowledge_bases = []
        for collection in collections:
            # Get collection info for vector count
            try:
                info = client.get_collection(collection.name)
                chunks = info.points_count or 0
            except Exception:
                chunks = 0
            
            # Get document count from MinIO
            try:
                docs = document_service.list_documents()
                files = len(docs)
            except Exception:
                files = 0
            
            knowledge_bases.append(
                KnowledgeBase(
                    id=collection.name,
                    name=collection.name,
                    chunks=chunks,
                    files=files,
                )
            )
        
        return KnowledgeBaseListResponse(
            knowledge_bases=knowledge_bases,
            total=len(knowledge_bases),
        )
    except UnexpectedResponse as e:
        raise HTTPException(status_code=502, detail=f"Qdrant error: {e}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Qdrant: {e}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_all_documents():
    """
    List all documents from MinIO storage.
    """
    import os
    from app.db.minio_client import MINIO_HOST, MINIO_PORT, DOCUMENTS_BUCKET
    
    # Log connection info for debugging
    print(f"[DEBUG] Connecting to MinIO at {MINIO_HOST}:{MINIO_PORT}")
    print(f"[DEBUG] Looking for bucket: {DOCUMENTS_BUCKET}")
    print(f"[DEBUG] MINIO_HOST env: {os.environ.get('MINIO_HOST', 'not set')}")
    
    try:
        docs = document_service.list_documents()
        print(f"[DEBUG] Found {len(docs)} documents")
        documents = [
            Document(
                id=doc["id"],
                name=doc["name"],
                size=doc["size"],
                last_modified=doc.get("last_modified"),
            )
            for doc in docs
        ]
        return DocumentListResponse(
            documents=documents,
            total=len(documents),
        )
    except Exception as e:
        print(f"[ERROR] MinIO error: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to MinIO: {e}")


@router.get("/documents/{doc_name:path}/download")
async def download_document(doc_name: str):
    """
    Download a document directly through the backend.
    Streams the file from MinIO to the client.
    """
    from fastapi.responses import StreamingResponse
    from app.db.minio_client import get_minio_client, DOCUMENTS_BUCKET
    
    # Check if document exists
    if not document_service.document_exists(doc_name):
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_name}")
    
    try:
        client = get_minio_client()
        response = client.get_object(DOCUMENTS_BUCKET, doc_name)
        
        # Create filename for download (use the object name)
        filename = doc_name.split("/")[-1]  # Get just the filename part
        
        return StreamingResponse(
            response,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            }
        )
    except Exception as e:
        print(f"Error downloading document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download document: {e}")


@router.get("/documents/debug")
async def debug_minio():
    """
    Debug endpoint to check MinIO connection.
    """
    import os
    from app.db.minio_client import MINIO_HOST, MINIO_PORT, DOCUMENTS_BUCKET, get_minio_client
    
    result = {
        "minio_host": MINIO_HOST,
        "minio_port": MINIO_PORT,
        "bucket": DOCUMENTS_BUCKET,
        "env_host": os.environ.get("MINIO_HOST", "not set"),
        "env_port": os.environ.get("MINIO_PORT", "not set"),
    }
    
    try:
        client = get_minio_client()
        result["bucket_exists"] = client.bucket_exists(DOCUMENTS_BUCKET)
        
        # Try to list objects
        objects = list(client.list_objects(DOCUMENTS_BUCKET, recursive=True, max_keys=5))
        result["sample_objects"] = [obj.object_name for obj in objects]
        result["status"] = "connected"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result
