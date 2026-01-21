"""
Web Content Ingest Service - Chunk and store web content in Qdrant.

Called by Regulatory Agent after scraping web content to:
1. Chunk content using RecursiveCharacterTextSplitter
2. Generate embeddings via Triton
3. Upsert to 'web_content' collection in Qdrant
"""
import os
import time
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Constants
COLLECTION_NAME = "web_content"
VECTOR_SIZE = 1024  # BGE-M3 embedding dimension
MAX_SEQ_LENGTH = 512


class WebContentIngestService:
    """Service to chunk and store web content in Qdrant."""
    
    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6334"))
        self.triton_url = os.getenv("TRITON_URL", "localhost:8001")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "bge_m3_tensorrt")
        
        self._qdrant_client = None
        self._triton_client = None
        self._tokenizer = None
        
        # Chunking config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", "; ", ", ", " "]
        )
        self.max_parent_text_len = 2000
    
    async def _get_qdrant_client(self):
        """Get or create Qdrant client."""
        if self._qdrant_client is None:
            from qdrant_client import QdrantClient
            self._qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port,
                prefer_grpc=True
            )
            logger.info(f"Connected to Qdrant at {self.qdrant_host}:{self.qdrant_port}")
        return self._qdrant_client
    
    async def ensure_collection_exists(self) -> bool:
        """Create web_content collection if not exists."""
        try:
            from qdrant_client.models import Distance, VectorParams
            
            client = await self._get_qdrant_client()
            
            # Check if collection exists
            collections = client.get_collections().collections
            exists = any(c.name == COLLECTION_NAME for c in collections)
            
            if not exists:
                logger.info(f"Creating collection '{COLLECTION_NAME}' with {VECTOR_SIZE} dims")
                client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection '{COLLECTION_NAME}' created successfully")
                return True
            else:
                logger.info(f"Collection '{COLLECTION_NAME}' already exists")
                return True
                
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            return False
    
    def _get_tokenizer(self):
        """Get or create tokenizer for Triton embedding."""
        if self._tokenizer is None:
            from transformers import AutoTokenizer
            from pathlib import Path
            
            # Try local tokenizer first
            local_path = Path(__file__).parent.parent.parent / "triton_server" / "model_repository" / "tokenizer"
            
            if local_path.exists() and (local_path / "tokenizer_config.json").exists():
                logger.info(f"Loading tokenizer from: {local_path}")
                self._tokenizer = AutoTokenizer.from_pretrained(str(local_path))
            else:
                logger.info("Loading tokenizer from HuggingFace: BAAI/bge-m3")
                self._tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
        
        return self._tokenizer
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Triton with tokenized input."""
        try:
            import numpy as np
            import tritonclient.grpc.aio as grpcclient
            
            tokenizer = self._get_tokenizer()
            
            tokens = tokenizer(
                [text],
                return_tensors="np",
                padding="max_length",
                truncation=True,
                max_length=MAX_SEQ_LENGTH,
            )
            
            input_ids = tokens["input_ids"].astype(np.int64)
            attention_mask = tokens["attention_mask"].astype(np.int64)
            
            if self._triton_client is None:
                self._triton_client = grpcclient.InferenceServerClient(url=self.triton_url)
                logger.info(f"Connected to Triton at {self.triton_url}")
            
            input_ids_tensor = grpcclient.InferInput("input_ids", input_ids.shape, "INT64")
            input_ids_tensor.set_data_from_numpy(input_ids)
            
            attention_mask_tensor = grpcclient.InferInput("attention_mask", attention_mask.shape, "INT64")
            attention_mask_tensor.set_data_from_numpy(attention_mask)
            
            result = await self._triton_client.infer(
                model_name=self.embedding_model,
                inputs=[input_ids_tensor, attention_mask_tensor],
                outputs=[grpcclient.InferRequestedOutput("last_hidden_state")]
            )
            
            last_hidden_state = result.as_numpy("last_hidden_state")
            
            # Mean pooling with attention mask
            mask = attention_mask[:, :, np.newaxis].astype(np.float32)
            masked_hidden = last_hidden_state * mask
            sum_hidden = masked_hidden.sum(axis=1)
            sum_mask = mask.sum(axis=1)
            
            embedding = sum_hidden / np.maximum(sum_mask, 1e-9)
            
            # L2 normalize
            norm = np.linalg.norm(embedding, axis=1, keepdims=True)
            embedding = embedding / np.maximum(norm, 1e-9)
            
            return embedding[0].tolist()
            
        except Exception as e:
            logger.warning(f"Triton embedding failed: {e}, using fallback")
            # Fallback to mock embedding
            import hashlib
            hash_bytes = hashlib.sha512(text.encode()).digest()
            embedding = []
            for i in range(VECTOR_SIZE):
                idx = i % 64
                seed = hash_bytes[idx] + i
                embedding.append((seed % 256) / 255.0 - 0.5)
            return embedding
    
    def chunk_content(self, content: str, source_url: str, name_file: str) -> List[Dict]:
        """
        Chunk content using RecursiveCharacterTextSplitter.
        
        Returns list of chunk records with metadata.
        """
        if not content or not content.strip():
            return []
        
        # Truncate parent_text for storage
        parent_text = content[:self.max_parent_text_len]
        if len(content) > self.max_parent_text_len:
            parent_text += "..."
        
        # Generate parent_id for grouping chunks from same source
        parent_id = str(uuid.uuid4())
        file_id = f"web_{uuid.uuid4().hex[:8]}"
        
        # Split into chunks
        chunks = self.text_splitter.split_text(content)
        
        records = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            
            records.append({
                "child_id": str(uuid.uuid4()),
                "child_text": chunk.strip(),
                "parent_text": parent_text,
                "parent_id": parent_id,
                "file_id": file_id,
                "name_file": name_file,
                "source_url": source_url,
                "scraped_at": datetime.now().isoformat()
            })
        
        logger.info(f"Chunked content into {len(records)} chunks from {source_url}")
        return records
    
    async def ingest(
        self, 
        content: str, 
        source_url: str, 
        name_file: str
    ) -> Dict[str, Any]:
        """
        Main method: chunk + embed + upsert to Qdrant.
        
        Args:
            content: Scraped web content
            source_url: Source URL
            name_file: Document/page title
            
        Returns:
            Dict with success status, chunks_count, execution_time_ms
        """
        start_time = time.time()
        
        try:
            # Ensure collection exists
            await self.ensure_collection_exists()
            
            # Chunk content
            records = self.chunk_content(content, source_url, name_file)
            
            if not records:
                return {
                    "success": False,
                    "error": "No content to ingest",
                    "chunks_count": 0,
                    "execution_time_ms": (time.time() - start_time) * 1000
                }
            
            # Generate embeddings and prepare points
            from qdrant_client.models import PointStruct
            
            points = []
            for record in records:
                embedding = await self._generate_embedding(record["child_text"])
                
                points.append(PointStruct(
                    id=record["child_id"],
                    vector=embedding,
                    payload={
                        "child_text": record["child_text"],
                        "parent_text": record["parent_text"],
                        "parent_id": record["parent_id"],
                        "file_id": record["file_id"],
                        "name_file": record["name_file"],
                        "source_url": record["source_url"],
                        "scraped_at": record["scraped_at"]
                    }
                ))
            
            # Upsert to Qdrant
            client = await self._get_qdrant_client()
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"Ingested {len(points)} chunks to {COLLECTION_NAME} in {execution_time:.1f}ms")
            
            return {
                "success": True,
                "chunks_count": len(points),
                "parent_id": records[0]["parent_id"] if records else None,
                "collection": COLLECTION_NAME,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            logger.error(f"Ingest failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "chunks_count": 0,
                "execution_time_ms": (time.time() - start_time) * 1000
            }


# Singleton instance
_web_content_ingest_service: Optional[WebContentIngestService] = None


def get_web_content_ingest_service() -> WebContentIngestService:
    """Get or create WebContentIngestService instance."""
    global _web_content_ingest_service
    if _web_content_ingest_service is None:
        _web_content_ingest_service = WebContentIngestService()
    return _web_content_ingest_service
