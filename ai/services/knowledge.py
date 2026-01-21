"""Knowledge Service - Full knowledge retrieval pipeline with detailed output."""
import os
import logging
from typing import Optional, List, Dict
from uuid import uuid4
from collections import defaultdict

from openai import AsyncOpenAI

from .retrieve import get_retrieve_service
from .rerank import get_rerank_service
from .llm import get_llm_service

logger = logging.getLogger(__name__)


class KnowledgeService:
    """
    Service for full knowledge retrieval pipeline.
    
    Pipeline:
    1. Enhance query (LLM)
    2. Retrieve top 10
    3. Rerank to top 5
    4. LLM filter relevant docs
    5. Group by parent_id
    6. Generate answer
    """
    
    def __init__(self):
        self.retrieve_service = get_retrieve_service()
        self.rerank_service = get_rerank_service()
        self.llm_service = get_llm_service()
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
    
    async def process(self, query: str, collection: str = "stock_law_chunks") -> dict:
        """
        Execute full knowledge retrieval pipeline with all intermediate results.
        
        Returns all steps: enhanced_query, retrieved, reranked, filtered, grouped docs
        """
        trace_id = uuid4().hex[:8]
        logger.info(f"[{trace_id}] Knowledge pipeline: {query[:100]}...")
        
        result = {
            "original_query": query,
            "enhanced_query": query,
            "retrieved_docs": [],
            "retrieved_count": 0,
            "reranked_docs": [],
            "reranked_count": 0,
            "filtered_docs": [],
            "filtered_count": 0,
            "grouped_docs": [],
            "grouped_count": 0,
            "validation_result": None,
            "regulatory_result": None,
            "generated_answer": "",
            "trace_id": trace_id
        }
        
        # Step 1: Enhance query
        enhanced_query = await self._enhance_query(query)
        result["enhanced_query"] = enhanced_query
        
        # Step 2: Retrieve top 10
        retrieve_result = await self.retrieve_service.retrieve(
            query=enhanced_query,
            collection=collection,
            limit=10,
            score_threshold=0.8  # Lower threshold for more candidates
        )
        retrieved_docs = retrieve_result.get("documents", [])
        result["retrieved_docs"] = retrieved_docs
        result["retrieved_count"] = len(retrieved_docs)
        
        if not retrieved_docs:
            # No docs found → call Regulatory Agent
            result["regulatory_result"] = await self._call_regulatory_fallback(query)
            result["generated_answer"] = result["regulatory_result"].get("answer", "Không tìm thấy tài liệu.")
            return result
        
        # Step 3: Rerank to top 5
        rerank_result = await self.rerank_service.rerank(
            query=enhanced_query,
            documents=retrieved_docs,
            top_n=5
        )
        reranked_docs = rerank_result.get("results", retrieved_docs[:5])
        result["reranked_docs"] = reranked_docs
        result["reranked_count"] = len(reranked_docs)
        
        # Step 4: LLM filter for relevance
        filtered_docs = await self._llm_filter_docs(query, reranked_docs)
        result["filtered_docs"] = filtered_docs
        result["filtered_count"] = len(filtered_docs)
        
        if not filtered_docs:
            # No relevant docs after filter → Regulatory fallback
            result["regulatory_result"] = await self._call_regulatory_fallback(query)
            result["generated_answer"] = result["regulatory_result"].get("answer", "Không tìm thấy tài liệu liên quan.")
            return result
        
        # Step 5: Group by parent_id
        grouped_docs = self._group_by_parent(filtered_docs)
        result["grouped_docs"] = grouped_docs
        result["grouped_count"] = len(grouped_docs)
        
        # NOTE: generated_answer is NOT created here
        # This service is for debugging pipeline steps only
        # Answer generation happens in Orchestrator
        
        return result
    
    async def _enhance_query(self, query: str) -> str:
        """Use LLM to enhance query for better retrieval."""
        if not self.llm:
            return query
        
        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Bạn là chuyên gia pháp luật chứng khoán Việt Nam.
Tối ưu hóa câu hỏi để tìm kiếm vector tốt hơn.
Giữ nguyên ý nghĩa, thêm từ khóa pháp lý liên quan.
Chỉ trả về query đã tối ưu."""
                    },
                    {"role": "user", "content": query}
                ],
                temperature=0.2,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Query enhancement failed: {e}")
            return query
    
    async def _llm_filter_docs(self, query: str, docs: List[Dict]) -> List[Dict]:
        """Use LLM to filter truly relevant documents."""
        if not self.llm or not docs:
            return docs
        
        try:
            docs_text = ""
            for i, doc in enumerate(docs):
                content = doc.get("content", "")[:500]
                docs_text += f"[{i}] {content}\n\n"
            
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Bạn là chuyên gia đánh giá độ liên quan tài liệu.
Xác định tài liệu nào thực sự liên quan đến câu hỏi.
Trả về JSON: {"relevant_indices": [0, 2, 4]}
Chỉ bao gồm index của tài liệu CÓ THỂ trả lời câu hỏi."""
                    },
                    {
                        "role": "user",
                        "content": f"Câu hỏi: {query}\n\nTài liệu:\n{docs_text}"
                    }
                ],
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            indices = result.get("relevant_indices", list(range(len(docs))))
            
            return [docs[i] for i in indices if i < len(docs)]
            
        except Exception as e:
            logger.warning(f"LLM filter failed: {e}")
            return docs
    
    def _group_by_parent(self, docs: List[Dict]) -> List[Dict]:
        """Group documents by parent_id."""
        groups = defaultdict(list)
        
        for doc in docs:
            metadata = doc.get("metadata", {})
            parent_id = metadata.get("parent_id", doc.get("id", "unknown"))
            groups[parent_id].append(doc)
        
        grouped = []
        for parent_id, chunks in groups.items():
            best_chunk = max(chunks, key=lambda x: x.get("score", 0))
            metadata = best_chunk.get("metadata", {})
            
            grouped.append({
                "parent_id": parent_id,
                "file_id": metadata.get("file_id", ""),
                "name_file": metadata.get("name_file", "Unknown"),
                "parent_text": metadata.get("parent_text", best_chunk.get("content", "")),
                "score": best_chunk.get("score", 0),
                "chunks": [
                    {
                        "child_id": c.get("id", ""),
                        "child_text": c.get("content", ""),
                        "score": c.get("score", 0)
                    }
                    for c in chunks
                ]
            })
        
        grouped.sort(key=lambda x: x["score"], reverse=True)
        return grouped
    
    def _format_grouped_context(self, grouped_docs: List[Dict]) -> str:
        """Format grouped documents into context string."""
        context_parts = []
        for i, doc in enumerate(grouped_docs[:3], 1):
            context_parts.append(
                f"📄 [{i}] {doc['name_file']}\n"
                f"Score: {doc['score']:.4f}\n\n"
                f"{doc['parent_text'][:2000]}"
            )
        return "\n\n---\n\n".join(context_parts)
    
    async def _call_regulatory_fallback(self, query: str) -> dict:
        """Call Regulatory Service as fallback."""
        try:
            from .regulatory import get_regulatory_service
            regulatory_service = get_regulatory_service()
            return await regulatory_service.search(query)
        except Exception as e:
            logger.error(f"Regulatory fallback failed: {e}")
            return {"answer": f"Lỗi tìm kiếm: {str(e)}"}


# Singleton instance
_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """Get or create Knowledge service instance."""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
