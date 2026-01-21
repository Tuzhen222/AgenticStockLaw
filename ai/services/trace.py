"""
Chat Trace Collector - Collects trace data during agent execution.

This module provides a simple dict-based tracer for AI agents.
The trace data will be passed back to backend for logging.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class AgentTracer:
    """
    Collects trace data during agent execution.
    
    Usage in executor.py:
        tracer = AgentTracer(trace_id)
        tracer.set_query(query)
        tracer.add_retrieve_step(docs, time_ms)
        tracer.add_rerank_step(docs, time_ms)
        ...
        trace_data = tracer.to_dict()
    """
    
    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self.start_time = time.time()
        
        self._data: Dict[str, Any] = {
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": "",
            "enhanced_query": "",
            "steps": [],
            "retrieve": {},
            "rerank": {},
            "filter": {},
            "grouped": {},
            "validation": {"called": False},
            "regulatory": {"called": False},
            "answer": "",
            "error": None
        }
    
    def set_query(self, query: str, enhanced: str = None) -> None:
        """Set original and enhanced query."""
        self._data["query"] = query
        self._data["enhanced_query"] = enhanced or query
    
    def add_step(self, name: str, details: str = "", time_ms: float = 0) -> None:
        """Add a pipeline step for logging."""
        self._data["steps"].append({
            "name": name,
            "details": details,
            "time_ms": time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def set_retrieve(
        self, 
        docs: List[Dict], 
        time_ms: float,
        score_threshold: float = 0.8
    ) -> None:
        """Set retrieve step results."""
        # Summarize docs for logging (avoid huge payloads)
        doc_summaries = []
        for doc in docs[:10]:  # Limit to first 10
            metadata = doc.get("metadata", {})
            doc_summaries.append({
                "id": doc.get("id", ""),
                "score": round(doc.get("score", 0), 4),
                "file_id": metadata.get("file_id", ""),
                "name_file": metadata.get("name_file", "")[:100],
                "content_preview": doc.get("content", "")[:100]
            })
        
        self._data["retrieve"] = {
            "time_ms": round(time_ms, 2),
            "count": len(docs),
            "score_threshold": score_threshold,
            "docs": doc_summaries
        }
    
    def set_rerank(self, docs: List[Dict], time_ms: float) -> None:
        """Set rerank step results."""
        doc_summaries = []
        for doc in docs[:5]:
            doc_summaries.append({
                "id": doc.get("id", ""),
                "score": round(doc.get("score", 0), 4),
                "name_file": doc.get("metadata", {}).get("name_file", "")[:100]
            })
        
        self._data["rerank"] = {
            "time_ms": round(time_ms, 2),
            "count": len(docs),
            "docs": doc_summaries
        }
    
    def set_filter(
        self, 
        docs: List[Dict], 
        time_ms: float,
        relevant_indices: List[int] = None
    ) -> None:
        """Set LLM filter step results."""
        doc_summaries = []
        for doc in docs:
            metadata = doc.get("metadata", {})
            doc_summaries.append({
                "id": doc.get("id", ""),
                "parent_id": metadata.get("parent_id", ""),
                "name_file": metadata.get("name_file", "")[:100]
            })
        
        self._data["filter"] = {
            "time_ms": round(time_ms, 2),
            "count": len(docs),
            "relevant_indices": relevant_indices or [],
            "docs": doc_summaries
        }
    
    def set_grouped(self, docs: List[Dict]) -> None:
        """Set grouped documents."""
        doc_summaries = []
        for doc in docs:
            doc_summaries.append({
                "parent_id": doc.get("parent_id", ""),
                "name_file": doc.get("name_file", "")[:100],
                "score": round(doc.get("score", 0), 4),
                "parent_text_length": len(doc.get("parent_text", ""))
            })
        
        self._data["grouped"] = {
            "count": len(docs),
            "docs": doc_summaries
        }
    
    def set_validation(
        self,
        called: bool = True,
        time_ms: float = 0,
        valid_count: int = 0,
        docs: List[Dict] = None
    ) -> None:
        """Set validation agent results."""
        doc_summaries = []
        if docs:
            for doc in docs:
                validation = doc.get("validation", {})
                doc_summaries.append({
                    "name_file": doc.get("name_file", "")[:100],
                    "status": validation.get("status", "unknown"),
                    "is_valid": validation.get("is_valid")
                })
        
        self._data["validation"] = {
            "called": called,
            "time_ms": round(time_ms, 2),
            "valid_count": valid_count,
            "docs": doc_summaries
        }
    
    def set_regulatory(
        self,
        called: bool = True,
        time_ms: float = 0,
        reason: str = "",
        sources: List[Dict] = None
    ) -> None:
        """Set regulatory agent results."""
        source_summaries = []
        if sources:
            for src in sources[:3]:
                source_summaries.append({
                    "title": src.get("title", "")[:100],
                    "url": src.get("url", "")
                })
        
        self._data["regulatory"] = {
            "called": called,
            "time_ms": round(time_ms, 2),
            "reason": reason,
            "sources": source_summaries
        }
    
    def set_answer(self, answer: str, answer_length: int = None) -> None:
        """Set final answer (truncated for logging)."""
        self._data["answer"] = answer[:500] if len(answer) > 500 else answer
        self._data["answer_length"] = answer_length or len(answer)
    
    def set_error(self, error: str) -> None:
        """Set error if pipeline failed."""
        self._data["error"] = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Get complete trace data as dict."""
        self._data["total_time_ms"] = round(
            (time.time() - self.start_time) * 1000, 2
        )
        return self._data


def create_tracer(trace_id: str) -> AgentTracer:
    """Create a new tracer instance."""
    return AgentTracer(trace_id)
