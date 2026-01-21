"""Retrieve Service - Document retrieval from Qdrant vector DB."""
import os
import time
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Triton model configuration
MAX_SEQ_LENGTH = 512
BGE_M3_MODEL_ID = "BAAI/bge-m3"


class RetrieveService:
    """Service for retrieving documents from Qdrant."""
    
    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6334"))
        self.triton_url = os.getenv("TRITON_URL", "localhost:8001")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "bge_m3_tensorrt")
        self._qdrant_client = None
        self._triton_client = None
        self._tokenizer = None
    
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
    
    def _get_tokenizer(self):
        """Get or create tokenizer."""
        if self._tokenizer is None:
            from transformers import AutoTokenizer
            
            # Try local tokenizer first
            local_path = Path(__file__).parent.parent.parent.parent / "triton_server" / "model_repository" / "tokenizer"
            
            if local_path.exists() and (local_path / "tokenizer_config.json").exists():
                logger.info(f"Loading tokenizer from: {local_path}")
                self._tokenizer = AutoTokenizer.from_pretrained(str(local_path))
            else:
                logger.info(f"Loading tokenizer from HuggingFace: {BGE_M3_MODEL_ID}")
                self._tokenizer = AutoTokenizer.from_pretrained(BGE_M3_MODEL_ID)
        
        return self._tokenizer
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Triton with tokenized input."""
        try:
            import numpy as np
            import tritonclient.grpc.aio as grpcclient
            
            # Get tokenizer
            tokenizer = self._get_tokenizer()
            
            # Tokenize input
            tokens = tokenizer(
                [text],
                return_tensors="np",
                padding="max_length",
                truncation=True,
                max_length=MAX_SEQ_LENGTH,
            )
            
            input_ids = tokens["input_ids"].astype(np.int64)
            attention_mask = tokens["attention_mask"].astype(np.int64)
            
            # Connect to Triton
            if self._triton_client is None:
                self._triton_client = grpcclient.InferenceServerClient(url=self.triton_url)
                logger.info(f"Connected to Triton at {self.triton_url}")
            
            # Prepare inputs
            input_ids_tensor = grpcclient.InferInput("input_ids", input_ids.shape, "INT64")
            input_ids_tensor.set_data_from_numpy(input_ids)
            
            attention_mask_tensor = grpcclient.InferInput("attention_mask", attention_mask.shape, "INT64")
            attention_mask_tensor.set_data_from_numpy(attention_mask)
            
            # Inference
            result = await self._triton_client.infer(
                model_name=self.embedding_model,
                inputs=[input_ids_tensor, attention_mask_tensor],
                outputs=[grpcclient.InferRequestedOutput("last_hidden_state")]
            )
            
            # Get last_hidden_state [1, seq_len, 1024]
            last_hidden_state = result.as_numpy("last_hidden_state")
            
            # Mean pooling with attention mask
            mask = attention_mask[:, :, np.newaxis].astype(np.float32)
            masked_hidden = last_hidden_state * mask
            sum_hidden = masked_hidden.sum(axis=1)  # [1, 1024]
            sum_mask = mask.sum(axis=1)  # [1, 1]
            
            embedding = sum_hidden / np.maximum(sum_mask, 1e-9)
            
            # L2 normalize
            norm = np.linalg.norm(embedding, axis=1, keepdims=True)
            embedding = embedding / np.maximum(norm, 1e-9)
            
            return embedding[0].tolist()
            
        except Exception as e:
            logger.warning(f"Triton embedding failed: {e}")
            # Return mock embedding with 1024 dimensions
            import hashlib
            
            hash_bytes = hashlib.sha512(text.encode()).digest()
            embedding = []
            for i in range(1024):
                idx = i % 64
                seed = hash_bytes[idx] + i
                embedding.append((seed % 256) / 255.0 - 0.5)
            
            return embedding
    
    async def retrieve(
        self,
        query: str,
        collection: str = "stock_law_chunks",
        limit: int = 5,
        score_threshold: float = 0.8
    ) -> dict:
        """
        Retrieve documents from Qdrant vector database.
        
        Input: query, collection, limit, score_threshold
        Output: dict with documents, count, execution_time_ms
        """
        start_time = time.time()
        
        try:
            # Generate embedding for query
            embedding = await self._generate_embedding(query)
            
            # Search Qdrant
            client = await self._get_qdrant_client()
            
            results = client.query_points(
                collection_name=collection,
                query=embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format documents
            documents = []
            for r in results.points:
                documents.append({
                    "id": str(r.id),
                    "content": r.payload.get("child_text", r.payload.get("text", "")),
                    "title": r.payload.get("title", r.payload.get("parent_id", "Untitled")),
                    "score": r.score,
                    "metadata": {k: v for k, v in r.payload.items() if k not in ["child_text", "text"]}
                })
            
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"Retrieved {len(documents)} docs from {collection} in {execution_time:.1f}ms")
            
            return {
                "documents": documents,
                "count": len(documents),
                "query": query,
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            logger.error(f"Retrieve failed: {e}", exc_info=True)
            return {
                "documents": [],
                "count": 0,
                "query": query,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }


# Singleton instance
_retrieve_service: Optional[RetrieveService] = None


def get_retrieve_service() -> RetrieveService:
    """Get or create Retrieve service instance."""
    global _retrieve_service
    if _retrieve_service is None:
        _retrieve_service = RetrieveService()
    return _retrieve_service
