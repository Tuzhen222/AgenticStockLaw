"""Schemas module for AI Gateway."""
from .chat import ChatRequest, ChatResponse, SourceDocument, HealthResponse
from .debug import (
    NLUInput, NLUOutput,
    OrchestratorInput, OrchestratorOutput,
    KnowledgeInput, KnowledgeOutput,
    RetrieveInput, RetrieveOutput,
    RerankInput, RerankOutput,
    ValidationInput, ValidationOutput,
    RegulatoryInput, RegulatoryOutput,
    LLMGenerateInput, LLMGenerateOutput,
    A2ACallInput, A2ACallOutput,
)

__all__ = [
    # Chat schemas
    "ChatRequest",
    "ChatResponse", 
    "SourceDocument",
    "HealthResponse",
    # Debug schemas
    "NLUInput", "NLUOutput",
    "OrchestratorInput", "OrchestratorOutput",
    "KnowledgeInput", "KnowledgeOutput",
    "RetrieveInput", "RetrieveOutput",
    "RerankInput", "RerankOutput",
    "ValidationInput", "ValidationOutput",
    "RegulatoryInput", "RegulatoryOutput",
    "LLMGenerateInput", "LLMGenerateOutput",
    "A2ACallInput", "A2ACallOutput",
]
