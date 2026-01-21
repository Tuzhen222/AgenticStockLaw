"""Debug router - Endpoints to test individual agents via A2A."""
import os
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from ai.schemas import (
    NLUInput, NLUOutput,
    OrchestratorInput, OrchestratorOutput,
    KnowledgeInput, KnowledgeOutput,
    ValidationInput, ValidationOutput,
    RegulatoryInput, RegulatoryOutput,
)
# Use NLU from agents folder
from ai.agents.orchestrator.nlu import NLUClassifier, QueryType, Intent
from ai.services import get_a2a_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["Debug"])

# Agent URLs from environment
KNOWLEDGE_AGENT_URL = os.getenv("KNOWLEDGE_AGENT_URL", "http://localhost:9101")
VALIDATION_AGENT_URL = os.getenv("VALIDATION_AGENT_URL", "http://localhost:9102")
REGULATORY_AGENT_URL = os.getenv("REGULATORY_AGENT_URL", "http://localhost:9103")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:9100")

# NLU Classifier from agents folder
nlu_classifier = NLUClassifier()


# ============== 1. NLU ENDPOINT ==============
@router.post("/nlu", response_model=NLUOutput, summary="Test NLU Classification")
async def debug_nlu(request: NLUInput):
    """Test NLU classification using agents/orchestrator/nlu.py"""
    try:
        result = await nlu_classifier.classify(request.query)
        return NLUOutput(
            type=result.type.value,
            intent=result.intent.value if result.intent else None,
            raw_llm_response=result.to_dict()
        )
    except Exception as e:
        logger.error(f"NLU debug failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 2. ORCHESTRATOR AGENT ENDPOINT ==============
@router.post("/orchestrator", response_model=OrchestratorOutput, summary="Test Orchestrator Agent")
async def debug_orchestrator(request: OrchestratorInput):
    """
    Test Orchestrator Agent pipeline using agents/orchestrator/nlu.py
    
    1. NLU classification (from agents folder)
    2. Route to appropriate agent via A2A
    """
    try:
        trace_id = uuid4().hex[:8]
        
        # Step 1: NLU classification using agent's NLU
        nlu_result = await nlu_classifier.classify(request.query)
        
        nlu_type = nlu_result.type.value
        nlu_intent = nlu_result.intent.value if nlu_result.intent else None
        
        nlu_dict = {
            "type": nlu_type,
            "intent": nlu_intent
        }
        
        # Step 2: Route to appropriate agent
        a2a_service = get_a2a_service()
        
        if nlu_type == "NOT_RELATED":
            routed_to = "none"
            agent_response = "Câu hỏi không liên quan đến pháp luật chứng khoán"
        elif nlu_intent == "LAW_CURRENCY_CHANGE":
            routed_to = "validation"
            result = await a2a_service.call_agent(VALIDATION_AGENT_URL, request.query)
            agent_response = result.get("parsed_content", "")
        else:
            routed_to = "knowledge"
            result = await a2a_service.call_agent(KNOWLEDGE_AGENT_URL, request.query)
            agent_response = result.get("parsed_content", "")
        
        return OrchestratorOutput(
            nlu_result=nlu_dict,
            routed_to=routed_to,
            agent_response=agent_response,
            final_answer=agent_response,
            trace_id=trace_id
        )
    except Exception as e:
        logger.error(f"Orchestrator debug failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== 3. KNOWLEDGE AGENT ENDPOINT ==============
@router.post("/knowledge", response_model=KnowledgeOutput, summary="Test Knowledge Agent Pipeline")
async def debug_knowledge(request: KnowledgeInput):
    """
    Test Knowledge Agent pipeline with intermediate results.
    
    Uses agent executor logic directly to show all steps:
    1. Enhance query
    2. Retrieve top 10
    3. Rerank to top 5  
    4. LLM filter
    5. Group by parent_id
    """
    try:
        from ai.agents.knowledge.executor import KnowledgeAgentExecutor
        from ai.agents.regulatory_update.executor import RegulatoryUpdateAgentExecutor
        from ai.services.retrieve import get_retrieve_service
        from ai.services.rerank import get_rerank_service
        
        trace_id = uuid4().hex[:8]
        executor = KnowledgeAgentExecutor()
        regulatory_result = None
        
        # Step 1: Enhance query
        enhanced_query = await executor._enhance_query(request.query)
        
        # Step 2: Retrieve top 10
        retrieve_service = get_retrieve_service()
        retrieve_result = await retrieve_service.retrieve(
            query=enhanced_query,
            collection=request.knowledge_base,
            limit=10,
            score_threshold=0.8
        )
        retrieved_docs = retrieve_result.get("documents", [])
        
        # If no docs found → Call Regulatory fallback
        if not retrieved_docs:
            reg_executor = RegulatoryUpdateAgentExecutor()
            search_result = await reg_executor._search_web(request.query)
            regulatory_result = {
                "fallback_triggered": True,
                "search_success": search_result.get("success", False),
                "content": reg_executor._format_content_for_orchestrator(request.query, search_result) if search_result.get("success") else search_result.get("error", "No results")
            }
            
            return KnowledgeOutput(
                original_query=request.query,
                enhanced_query=enhanced_query,
                retrieved_docs=[],
                retrieved_count=0,
                reranked_docs=[],
                reranked_count=0,
                filtered_docs=[],
                filtered_count=0,
                grouped_docs=[],
                grouped_count=0,
                regulatory_result=regulatory_result,
                trace_id=trace_id
            )
        
        # Step 3: Rerank to top 5
        rerank_service = get_rerank_service()
        rerank_result = await rerank_service.rerank(
            query=enhanced_query,
            documents=retrieved_docs,
            top_n=5
        )
        reranked_docs = rerank_result.get("results", retrieved_docs[:5])
        
        # Step 4: LLM filter
        if reranked_docs:
            filtered_docs = await executor._llm_filter_docs(request.query, reranked_docs)
        else:
            filtered_docs = []
        
        # If no docs after filter → Call Regulatory fallback
        if not filtered_docs:
            reg_executor = RegulatoryUpdateAgentExecutor()
            search_result = await reg_executor._search_web(request.query)
            regulatory_result = {
                "fallback_triggered": True,
                "reason": "No docs after LLM filter",
                "search_success": search_result.get("success", False),
                "content": reg_executor._format_content_for_orchestrator(request.query, search_result) if search_result.get("success") else search_result.get("error", "No results")
            }
        
        # Step 5: Group by parent_id
        if filtered_docs:
            grouped_docs = executor._group_by_parent(filtered_docs)
        else:
            grouped_docs = []
        
        return KnowledgeOutput(
            original_query=request.query,
            enhanced_query=enhanced_query,
            retrieved_docs=retrieved_docs,
            retrieved_count=len(retrieved_docs),
            reranked_docs=reranked_docs,
            reranked_count=len(reranked_docs),
            filtered_docs=filtered_docs,
            filtered_count=len(filtered_docs),
            grouped_docs=grouped_docs,
            grouped_count=len(grouped_docs),
            regulatory_result=regulatory_result,
            trace_id=trace_id
        )
    except Exception as e:
        logger.error(f"Knowledge debug failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============== 4. VALIDATION AGENT ENDPOINT ==============
@router.post("/validation", response_model=ValidationOutput, summary="Test Validation Agent")
async def debug_validation(request: ValidationInput):
    """
    Test Validation Agent (Mode 1: Direct query).
    
    Uses agent executor to:
    1. Extract document names
    2. MCP BrightData search
    3. LLM validate
    """
    try:
        from ai.agents.validate.executor import ValidateAgentExecutor
        
        executor = ValidateAgentExecutor()
        
        # Call the direct validation method
        result = await executor._validate_direct_query(request.query)
        
        return ValidationOutput(
            document_name=None,
            is_valid=None,
            effective_date=None,
            amendments=[],
            replaced_by=None,
            raw_response=result
        )
    except Exception as e:
        logger.error(f"Validation debug failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============== 5. REGULATORY UPDATE AGENT ENDPOINT ==============
@router.post("/regulatory", response_model=RegulatoryOutput, summary="Test Regulatory Agent")
async def debug_regulatory(request: RegulatoryInput):
    """
    Test Regulatory Agent pipeline.
    
    Uses executor directly:
    1. MCP BrightData search (2 links)
    2. Scrape content
    3. Return formatted content
    """
    try:
        from ai.agents.regulatory_update.executor import RegulatoryUpdateAgentExecutor
        
        executor = RegulatoryUpdateAgentExecutor()
        
        # Call the search method directly
        search_result = await executor._search_web(request.query)
        
        if search_result.get("success"):
            content = executor._format_content_for_orchestrator(request.query, search_result)
            found_docs = [
                {"title": r.title, "url": r.url, "snippet": r.snippet}
                for r in search_result.get("results", [])[:2]
            ]
        else:
            content = search_result.get("error", "Search failed")
            found_docs = []
        
        return RegulatoryOutput(
            query_analysis={"original_query": request.query},
            answer=content,
            found_documents=found_docs,
            source="regulatory_executor_direct",
            result_summary=content[:500] if content else ""
        )
    except Exception as e:
        logger.error(f"Regulatory debug failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============== QDRANT STATUS ENDPOINT ==============
@router.get("/qdrant/status", summary="Check Qdrant Status")
async def debug_qdrant_status():
    """Check Qdrant connection and list available collections."""
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6334"))
    triton_url = os.getenv("TRITON_URL", "localhost:8001")
    
    result = {
        "config": {
            "qdrant_host": qdrant_host,
            "qdrant_port": qdrant_port,
            "triton_url": triton_url
        },
        "status": "unknown",
        "collections": [],
        "error": None
    }
    
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=qdrant_host, port=qdrant_port, prefer_grpc=True)
        
        collections = client.get_collections()
        result["status"] = "connected"
        result["collections"] = []
        
        for c in collections.collections:
            collection_info = client.get_collection(c.name)
            result["collections"].append({
                "name": c.name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": str(collection_info.status)
            })
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


# ============== DEBUG OVERVIEW ==============
@router.get("/", summary="Debug Endpoints Overview")
async def debug_overview():
    """List all available debug endpoints."""
    return {
        "message": "Debug endpoints - All call actual agents",
        "agent_urls": {
            "orchestrator": ORCHESTRATOR_URL,
            "knowledge": KNOWLEDGE_AGENT_URL,
            "validation": VALIDATION_AGENT_URL,
            "regulatory": REGULATORY_AGENT_URL
        },
        "endpoints": {
            "POST /debug/nlu": "Test NLU classification",
            "POST /debug/orchestrator": "Test Orchestrator pipeline",
            "POST /debug/knowledge": "Test Knowledge pipeline",
            "POST /debug/validation": "Test Validation Agent",
            "POST /debug/regulatory": "Test Regulatory Agent",
            "GET /debug/qdrant/status": "Check Qdrant connection",
            "GET /debug/mcp/test": "Test MCP BrightData connection"
        }
    }


# ============== MCP BRIGHTDATA TEST ==============
@router.get("/mcp/test", summary="Test MCP BrightData Connection")
async def debug_mcp_test():
    """Test MCP BrightData connection and search."""
    import os
    
    token = os.getenv("BRIGHTDATA_MCP_TOKEN", "")
    result = {
        "token_set": bool(token),
        "token_preview": token[:20] + "..." if len(token) > 20 else token,
        "connection": "unknown",
        "tools": [],
        "search_test": None,
        "error": None
    }
    
    try:
        from ai.mcp.brightdata import BrightDataMCPClient
        
        client = BrightDataMCPClient()
        
        # Test getting tools
        tools = await client._get_tools()
        result["connection"] = "connected"
        result["tools"] = [t.name for t in tools]
        
        # Test search
        search_result = await client.serp_search(
            query="chứng khoán việt nam site:thuvienphapluat.vn",
            num_results=2
        )
        
        result["search_test"] = {
            "success": search_result.success,
            "count": len(search_result.results) if search_result.results else 0,
            "error": search_result.error
        }
        
        if search_result.results:
            result["search_test"]["first_result"] = {
                "title": search_result.results[0].title,
                "url": search_result.results[0].url
            }
            
    except Exception as e:
        result["connection"] = "error"
        result["error"] = str(e)
    
    return result
