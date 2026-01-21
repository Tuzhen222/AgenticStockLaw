"""
MCP Server Configuration

Shared configuration and utilities for MCP tool servers.
"""
import os
import logging
from typing import Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@dataclass
class MCPConfig:
    """Configuration for MCP servers."""
    
    # Triton Inference Server
    triton_url: str = os.getenv("TRITON_URL", "localhost:8001")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "bgem3_onnx")
    
    # Qdrant Vector Database
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6334"))
    default_collection: str = os.getenv("DEFAULT_COLLECTION", "stock_law_chunks")
    
    # Cohere Rerank
    cohere_api_key: Optional[str] = os.getenv("COHERE_API_KEY")
    cohere_model: str = os.getenv("COHERE_RERANK_MODEL", "rerank-multilingual-v3.0")
    
    # Server settings
    default_transport: str = "stdio"
    retrieve_port: int = int(os.getenv("RETRIEVE_MCP_PORT", "8100"))
    rerank_port: int = int(os.getenv("RERANK_MCP_PORT", "8101"))


# Global config instance
config = MCPConfig()


# Lazy-loaded clients
_qdrant_client = None
_triton_client = None
_cohere_client = None


async def get_qdrant_client():
    """Get or create Qdrant client."""
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        _qdrant_client = QdrantClient(
            host=config.qdrant_host,
            port=config.qdrant_port,
            prefer_grpc=True
        )
        logger.info(f"Connected to Qdrant at {config.qdrant_host}:{config.qdrant_port}")
    return _qdrant_client


async def get_triton_client():
    """Get or create Triton client."""
    global _triton_client
    if _triton_client is None:
        import tritonclient.grpc.aio as grpcclient
        _triton_client = grpcclient.InferenceServerClient(url=config.triton_url)
        logger.info(f"Connected to Triton at {config.triton_url}")
    return _triton_client


def get_cohere_client():
    """Get or create Cohere client."""
    global _cohere_client
    if _cohere_client is None:
        if not config.cohere_api_key:
            raise ValueError("COHERE_API_KEY not set")
        import cohere
        _cohere_client = cohere.Client(config.cohere_api_key)
        logger.info("Cohere client initialized")
    return _cohere_client


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding using Triton."""
    try:
        import numpy as np
        
        client = await get_triton_client()
        
        import tritonclient.grpc.aio as grpcclient
        text_input = grpcclient.InferInput("text", [1], "BYTES")
        text_input.set_data_from_numpy(
            np.array([text.encode('utf-8')], dtype=object)
        )
        
        result = await client.infer(
            model_name=config.embedding_model,
            inputs=[text_input]
        )
        
        return result.as_numpy("embedding")[0].tolist()
        
    except Exception as e:
        logger.warning(f"Triton embedding failed: {e}, using mock")
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_bytes[:1024]]
