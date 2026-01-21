"""
Qdrant Vector Database Client Module
Uses gRPC for high-performance vector operations.
"""

import uuid
from typing import Optional
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.grpc import PointStruct, VectorParams, Distance
from qdrant_client.models import (
    VectorParams as ModelsVectorParams,
    Distance as ModelsDistance,
    PointStruct as ModelsPointStruct,
)


@dataclass
class QdrantConfig:
    """Configuration for Qdrant connection."""
    host: str = "localhost"
    grpc_port: int = 6334
    http_port: int = 6333
    collection_name: str = "stock_law_chunks"
    vector_size: int = 1024  # BGE-M3 embedding dimension


class QdrantVectorDB:
    """Qdrant vector database client using gRPC."""
    
    def __init__(self, config: Optional[QdrantConfig] = None):
        """Initialize Qdrant client with gRPC.
        
        Args:
            config: Qdrant configuration. Uses defaults if not provided.
        """
        self.config = config or QdrantConfig()
        self.client = QdrantClient(
            host=self.config.host,
            grpc_port=self.config.grpc_port,
            prefer_grpc=True,
        )
    
    def create_collection_if_not_exists(self) -> bool:
        """Create collection if it doesn't exist.
        
        Returns:
            True if collection was created, False if it already existed.
        """
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.config.collection_name in collection_names:
            print(f"Collection '{self.config.collection_name}' already exists")
            return False
        
        self.client.create_collection(
            collection_name=self.config.collection_name,
            vectors_config=ModelsVectorParams(
                size=self.config.vector_size,
                distance=ModelsDistance.COSINE,
            ),
        )
        print(f"Created collection '{self.config.collection_name}'")
        return True
    
    def delete_collection(self) -> bool:
        """Delete the collection if it exists.
        
        Returns:
            True if deleted, False if it didn't exist.
        """
        try:
            self.client.delete_collection(self.config.collection_name)
            print(f"Deleted collection '{self.config.collection_name}'")
            return True
        except Exception:
            return False
    
    def upsert_batch(
        self,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> int:
        """Upsert a batch of points.
        
        Args:
            ids: List of point IDs (UUIDs as strings).
            vectors: List of embedding vectors.
            payloads: List of metadata dictionaries.
            
        Returns:
            Number of points upserted.
        """
        points = [
            ModelsPointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        
        self.client.upsert(
            collection_name=self.config.collection_name,
            points=points,
        )
        
        return len(points)
    
    def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
    ) -> list[dict]:
        """Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector.
            limit: Maximum number of results.
            score_threshold: Minimum similarity score.
            
        Returns:
            List of search results with id, score, and payload.
        """
        results = self.client.search(
            collection_name=self.config.collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )
        
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in results
        ]
    
    def get_collection_info(self) -> dict:
        """Get collection statistics.
        
        Returns:
            Dictionary with collection info.
        """
        info = self.client.get_collection(self.config.collection_name)
        return {
            "name": self.config.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.name,
        }
    
    def count_points(self) -> int:
        """Get total number of points in collection.
        
        Returns:
            Number of points.
        """
        info = self.client.get_collection(self.config.collection_name)
        return info.points_count or 0


if __name__ == "__main__":
    # Quick test
    db = QdrantVectorDB()
    db.create_collection_if_not_exists()
    print(db.get_collection_info())
