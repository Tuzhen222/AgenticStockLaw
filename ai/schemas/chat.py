"""Request and response schemas for Chat endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    """Chat request from backend."""
    query: str = Field(
        ..., 
        description="User query/question", 
        examples=["Quy định về công bố thông tin cổ phiếu là gì?"]
    )
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")
    knowledge_base: Optional[str] = Field(
        None, 
        description="Qdrant collection name to search (e.g. 'stock_law', 'securities'). If null, uses default.",
        examples=["stock_law"]
    )
    
    @property
    def message(self) -> str:
        """Alias for backward compatibility."""
        return self.query


class SourceDocument(BaseModel):
    """Source document reference."""
    title: str
    content: str
    score: Optional[float] = None
    metadata: Optional[dict] = None


class ChatResponse(BaseModel):
    """Chat response to backend."""
    answer: str = Field(..., description="Generated answer")
    sources: List[SourceDocument] = Field(default_factory=list, description="Source documents")
    session_id: Optional[str] = Field(None, description="Session ID")
    metadata: Optional[dict] = Field(default_factory=dict, description="Response metadata")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    services: dict = Field(default_factory=dict)
