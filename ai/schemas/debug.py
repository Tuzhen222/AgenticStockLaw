"""Request and response schemas for Debug endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List, Any


# ============== NLU ==============
class NLUInput(BaseModel):
    """Input for NLU classification."""
    query: str = Field(..., example="Mức phạt công bố thông tin trễ?")


class NLUOutput(BaseModel):
    """Output from NLU classification."""
    type: str = Field(..., description="GENERAL_CHAT, NOT_RELATED, or RELATED")
    intent: Optional[str] = Field(None, description="LAW_CURRENCY_CHANGE or LEGAL_ANALYSIS")
    raw_llm_response: Optional[Any] = None


# ============== ORCHESTRATOR ==============
class OrchestratorInput(BaseModel):
    """Input for Orchestrator agent."""
    query: str = Field(..., example="Mức phạt công bố thông tin trễ?")
    user_id: Optional[str] = None
    knowledge_base: Optional[str] = None


class OrchestratorOutput(BaseModel):
    """Output from Orchestrator agent with full trace."""
    nlu_result: Optional[dict] = Field(None, description="NLU classification result")
    routed_to: str = Field("", description="Agent that was called")
    agent_response: str = Field("", description="Raw response from sub-agent")
    final_answer: str = Field("", description="Final generated answer")
    trace_id: str = ""


# ============== KNOWLEDGE AGENT ==============
class KnowledgeInput(BaseModel):
    """Input for Knowledge agent."""
    query: str = Field(..., example="Điều 8 Nghị định 155/2020")
    knowledge_base: str = Field(
        "stock_law_chunks", 
        description="Qdrant collection name to search",
        example="stock_law_chunks"
    )


class GroupedDoc(BaseModel):
    """A grouped document with parent text and child chunks."""
    parent_id: str
    file_id: str
    name_file: str
    parent_text: str
    score: float
    chunks: List[dict] = Field(default_factory=list)


class KnowledgeOutput(BaseModel):
    """Output from Knowledge agent with full pipeline results."""
    # Step 1: Query enhancement
    original_query: str
    enhanced_query: str
    
    # Step 2: Retrieved docs (top 10)
    retrieved_docs: List[dict] = Field(default_factory=list)
    retrieved_count: int = 0
    
    # Step 3: Reranked docs (top 5)
    reranked_docs: List[dict] = Field(default_factory=list)
    reranked_count: int = 0
    
    # Step 4: LLM filtered docs
    filtered_docs: List[dict] = Field(default_factory=list)
    filtered_count: int = 0
    
    # Step 5: Grouped by parent_id
    grouped_docs: List[GroupedDoc] = Field(default_factory=list)
    grouped_count: int = 0
    
    # Fallback results (if retrieve fails)
    regulatory_result: Optional[dict] = None
    
    # Trace
    trace_id: str = ""


# ============== RETRIEVE TOOL ==============
class RetrieveInput(BaseModel):
    """Input for Retrieve tool."""
    query: str = Field(..., example="công bố thông tin")
    collection: str = Field("stock_law", description="Qdrant collection name")
    limit: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.8, ge=0.0, le=1.0)


class RetrieveOutput(BaseModel):
    """Output from Retrieve tool."""
    documents: List[dict] = Field(default_factory=list)
    count: int
    query: str
    execution_time_ms: float


# ============== RERANK TOOL ==============
class RerankInput(BaseModel):
    """Input for Rerank tool."""
    query: str = Field(..., example="công bố thông tin")
    documents: List[dict] = Field(..., description="Documents to rerank")
    top_n: int = Field(3, ge=1, le=20)


class RerankOutput(BaseModel):
    """Output from Rerank tool."""
    results: List[dict] = Field(default_factory=list)
    original_count: int
    reranked_count: int


# ============== VALIDATION AGENT ==============
class ValidationInput(BaseModel):
    """Input for Validation agent."""
    query: str = Field(..., example="Nghị định 155/2020 còn hiệu lực không?")


class ValidationOutput(BaseModel):
    """Output from Validation agent."""
    document_name: Optional[str] = None
    is_valid: Optional[bool] = None
    effective_date: Optional[str] = None
    amendments: List[dict] = Field(default_factory=list)
    replaced_by: Optional[str] = None
    raw_response: Optional[str] = None


# ============== REGULATORY UPDATE AGENT ==============
class RegulatoryInput(BaseModel):
    """Input for Regulatory Update agent."""
    query: str = Field(..., example="văn bản mới về chứng khoán 2024")


class RegulatoryOutput(BaseModel):
    """Output from Regulatory Update agent with direct answer."""
    query_analysis: Optional[dict] = Field(None, description="Query info")
    answer: str = Field("", description="LLM generated answer")
    found_documents: List[dict] = Field(default_factory=list)
    source: str = "unknown"
    result_summary: str = ""


# ============== LLM GENERATE TOOL ==============
class LLMGenerateInput(BaseModel):
    """Input for LLM Generate tool."""
    query: str = Field(..., example="Mức phạt công bố thông tin trễ?")
    context: str = Field(..., example="Theo Điều 8 Nghị định 155/2020...")
    system_prompt: Optional[str] = Field(
        None, 
        description="Custom system prompt, uses default if not provided"
    )


class LLMGenerateOutput(BaseModel):
    """Output from LLM Generate tool."""
    answer: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


# ============== A2A CALL ==============
class A2ACallInput(BaseModel):
    """Input for raw A2A agent call."""
    agent_url: str = Field(..., example="http://localhost:9101")
    query: str = Field(..., example="test query")


class A2ACallOutput(BaseModel):
    """Output from raw A2A agent call."""
    success: bool
    agent_name: Optional[str] = None
    raw_response: Optional[dict] = None
    parsed_content: str = ""
    error: Optional[str] = None
