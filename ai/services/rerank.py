"""Rerank Service - Document reranking using Cohere."""
import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class RerankService:
    """Service for reranking documents using Cohere."""
    
    def __init__(self):
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        self.cohere_model = os.getenv("COHERE_RERANK_MODEL", "rerank-multilingual-v3.0")
        self._client = None
    
    def _get_client(self):
        """Get or create Cohere client."""
        if self._client is None:
            if not self.cohere_api_key:
                logger.warning("COHERE_API_KEY not set, reranking will return original order")
                return None
            import cohere
            self._client = cohere.Client(self.cohere_api_key)
            logger.info("Cohere client initialized")
        return self._client
    
    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_n: int = 3
    ) -> dict:
        """
        Rerank documents by relevance to query.
        
        Input: query, documents, top_n
        Output: dict with results, original_count, reranked_count
        """
        original_count = len(documents)
        
        if not documents:
            return {
                "results": [],
                "original_count": 0,
                "reranked_count": 0
            }
        
        client = self._get_client()
        
        if client is None:
            # No Cohere API key - return original order with simulated scores
            results = []
            for i, doc in enumerate(documents[:top_n]):
                doc_copy = doc.copy()
                doc_copy["relevance_score"] = 1.0 - (i * 0.1)  # Simulated score
                doc_copy["original_index"] = i
                results.append(doc_copy)
            
            return {
                "results": results,
                "original_count": original_count,
                "reranked_count": len(results)
            }
        
        try:
            # Extract text content from documents
            doc_texts = []
            for doc in documents:
                text = doc.get("content", doc.get("text", ""))
                doc_texts.append(text)
            
            # Call Cohere rerank
            response = client.rerank(
                model=self.cohere_model,
                query=query,
                documents=doc_texts,
                top_n=min(top_n, len(documents))
            )
            
            # Build results with original document data
            results = []
            for item in response.results:
                doc = documents[item.index].copy()
                doc["relevance_score"] = item.relevance_score
                doc["original_index"] = item.index
                results.append(doc)
            
            logger.info(f"Reranked {original_count} docs → top {len(results)}")
            
            return {
                "results": results,
                "original_count": original_count,
                "reranked_count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Rerank failed: {e}", exc_info=True)
            # Fallback to original order
            results = []
            for i, doc in enumerate(documents[:top_n]):
                doc_copy = doc.copy()
                doc_copy["relevance_score"] = doc.get("score", 0.5)
                doc_copy["original_index"] = i
                results.append(doc_copy)
            
            return {
                "results": results,
                "original_count": original_count,
                "reranked_count": len(results),
                "error": str(e)
            }


# Singleton instance
_rerank_service: Optional[RerankService] = None


def get_rerank_service() -> RerankService:
    """Get or create Rerank service instance."""
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service
