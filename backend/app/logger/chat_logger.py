"""
Chat Logger - Detailed trace logging for chat interactions.

Logs all agent interactions, NLU results, retrieved documents, and routing decisions.
Output: backend/logs/chat_trace.log (JSON Lines format)
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler


class ChatLogger:
    """
    Logger for detailed chat traces.
    
    Writes JSON Lines to chat_trace.log with complete pipeline info:
    - NLU classification
    - Routing decisions
    - Knowledge pipeline (retrieve, rerank, filter, group)
    - Validation/Regulatory agent calls
    - LLM generation
    - Final answer
    """
    
    _instance: Optional["ChatLogger"] = None
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path(__file__).parent.parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.log_dir / "chat_trace.log"
        self._logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger with rotating file handler."""
        logger = logging.getLogger("chat_trace")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        # Raw format - just the message (JSON line)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        
        return logger
    
    def log_trace(self, trace: Dict[str, Any]) -> None:
        """
        Write a complete trace to the log file.
        
        Args:
            trace: Dict containing complete chat trace data
        """
        # Add timestamp if not present
        if "timestamp" not in trace:
            trace["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Write as single JSON line
        self._logger.info(json.dumps(trace, ensure_ascii=False, default=str))
    
    @classmethod
    def get_instance(cls) -> "ChatLogger":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = ChatLogger()
        return cls._instance


class ChatTracer:
    """
    Context manager for building a chat trace.
    
    Usage:
        async with ChatTracer("abc123") as tracer:
            tracer.set_query("What is the penalty?")
            tracer.set_nlu(nlu_result)
            tracer.set_routing("knowledge", "LEGAL_ANALYSIS")
            tracer.add_knowledge_step("retrieve", {...})
            tracer.set_validation({...})
            tracer.set_answer("The penalty is...")
    """
    
    def __init__(self, trace_id: str, session_id: Optional[str] = None):
        self.trace_id = trace_id
        self.session_id = session_id
        self.start_time = datetime.now(timezone.utc)
        
        self.trace: Dict[str, Any] = {
            "trace_id": trace_id,
            "session_id": session_id,
            "timestamp": self.start_time.isoformat(),
            "query": "",
            "total_time_ms": 0,
            "nlu": {},
            "routing": {},
            "knowledge": {},
            "validation": {"called": False},
            "regulatory_update": {"called": False},
            "llm": {},
            "answer": ""
        }
    
    def set_query(self, query: str) -> None:
        """Set the original user query."""
        self.trace["query"] = query
    
    def set_nlu(
        self, 
        type_: str, 
        intent: Optional[str] = None,
        confidence: float = 0.0,
        raw_response: Optional[Dict] = None
    ) -> None:
        """Set NLU classification result."""
        self.trace["nlu"] = {
            "type": type_,
            "intent": intent,
            "confidence": confidence,
            "raw_response": raw_response or {}
        }
    
    def set_routing(self, routed_to: str, reason: str) -> None:
        """Set routing decision."""
        self.trace["routing"] = {
            "routed_to": routed_to,
            "reason": reason
        }
    
    def set_knowledge(
        self,
        enhanced_query: str = "",
        retrieve: Optional[Dict] = None,
        rerank: Optional[Dict] = None,
        filter_: Optional[Dict] = None,
        grouped: Optional[Dict] = None,
        fallback_used: bool = False
    ) -> None:
        """Set knowledge pipeline results."""
        self.trace["knowledge"] = {
            "enhanced_query": enhanced_query,
            "retrieve": retrieve or {},
            "rerank": rerank or {},
            "filter": filter_ or {},
            "grouped": grouped or {},
            "fallback_used": fallback_used
        }
    
    def add_knowledge_step(self, step_name: str, data: Dict) -> None:
        """Add a single knowledge pipeline step."""
        if "knowledge" not in self.trace:
            self.trace["knowledge"] = {}
        self.trace["knowledge"][step_name] = data
    
    def set_validation(
        self,
        called: bool = True,
        time_ms: float = 0,
        document_name: Optional[str] = None,
        is_valid: Optional[bool] = None,
        effective_date: Optional[str] = None,
        raw_response: Optional[str] = None
    ) -> None:
        """Set validation agent result."""
        self.trace["validation"] = {
            "called": called,
            "time_ms": time_ms,
            "document_name": document_name,
            "is_valid": is_valid,
            "effective_date": effective_date,
            "raw_response": raw_response
        }
    
    def set_regulatory(
        self,
        called: bool = True,
        time_ms: float = 0,
        search_count: int = 0,
        sources: Optional[list] = None,
        reason: str = ""
    ) -> None:
        """Set regulatory update agent result."""
        self.trace["regulatory_update"] = {
            "called": called,
            "time_ms": time_ms,
            "search_count": search_count,
            "sources": sources or [],
            "reason": reason
        }
    
    def set_llm(
        self,
        model: str = "gpt-4o-mini",
        time_ms: float = 0,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ) -> None:
        """Set LLM generation info."""
        self.trace["llm"] = {
            "model": model,
            "time_ms": time_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    
    def set_answer(self, answer: str) -> None:
        """Set final answer."""
        self.trace["answer"] = answer[:500] if len(answer) > 500 else answer
    
    def set_error(self, error: str) -> None:
        """Set error if pipeline failed."""
        self.trace["error"] = error
    
    def finalize(self) -> Dict[str, Any]:
        """Calculate total time and return the trace."""
        end_time = datetime.now(timezone.utc)
        self.trace["total_time_ms"] = int(
            (end_time - self.start_time).total_seconds() * 1000
        )
        return self.trace
    
    def save(self) -> None:
        """Save trace to log file."""
        trace = self.finalize()
        ChatLogger.get_instance().log_trace(trace)
    
    async def __aenter__(self) -> "ChatTracer":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            self.set_error(str(exc_val))
        self.save()


def get_chat_logger() -> ChatLogger:
    """Get chat logger instance."""
    return ChatLogger.get_instance()
