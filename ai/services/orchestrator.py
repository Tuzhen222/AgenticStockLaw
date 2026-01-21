"""Orchestrator Service - Main query routing and orchestration."""
import os
import logging
from typing import Optional
from uuid import uuid4

from .nlu import get_nlu_service, NLUResult
from .knowledge import get_knowledge_service
from .validation import get_validation_service
from .llm import get_llm_service
from .a2a import get_a2a_service

logger = logging.getLogger(__name__)


# Agent URLs
KNOWLEDGE_AGENT_URL = os.getenv("KNOWLEDGE_AGENT_URL", "http://localhost:9101")
VALIDATION_AGENT_URL = os.getenv("VALIDATION_AGENT_URL", "http://localhost:9102")


NOT_RELATED_RESPONSE = """Xin lỗi, câu hỏi này nằm ngoài phạm vi hỗ trợ của tôi.

Tôi là trợ lý pháp luật chứng khoán, có thể giúp bạn:
• Tra cứu quy định pháp luật chứng khoán
• Kiểm tra hiệu lực văn bản
• Tìm hiểu mức phạt vi phạm
• Giải thích các điều khoản luật

Hãy đặt câu hỏi liên quan đến pháp luật chứng khoán!"""


class OrchestratorService:
    """Service for orchestrating the full query pipeline."""
    
    def __init__(self):
        self.nlu_service = get_nlu_service()
        self.knowledge_service = get_knowledge_service()
        self.validation_service = get_validation_service()
        self.llm_service = get_llm_service()
        self.a2a_service = get_a2a_service()
    
    async def process(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        knowledge_base: Optional[str] = None
    ) -> dict:
        """
        Execute full orchestrator pipeline.
        
        Input: query, optional user_id, optional knowledge_base
        Output: dict with nlu_result, routed_to, agent_response, final_answer, trace_id
        
        Pipeline:
        1. NLU Classification
        2. Route to appropriate agent/service
        3. Get agent response
        4. Generate final answer with LLM
        """
        trace_id = uuid4().hex[:8]
        logger.info(f"[{trace_id}] Orchestrator: {query[:100]}...")
        
        # Step 1: NLU Classification
        nlu_result = await self.nlu_service.classify(query)
        logger.info(f"[{trace_id}] NLU: type={nlu_result.type}, intent={nlu_result.intent}")
        
        # Step 2: Route based on type
        routed_to = ""
        agent_response = ""
        
        if nlu_result.type == "GENERAL_CHAT":
            routed_to = "llm_chat"
            agent_response = await self.llm_service.chat(query)
            final_answer = agent_response
            
        elif nlu_result.type == "NOT_RELATED":
            routed_to = "not_related"
            agent_response = NOT_RELATED_RESPONSE
            final_answer = NOT_RELATED_RESPONSE
            
        else:  # RELATED
            if nlu_result.intent == "LAW_CURRENCY_CHANGE":
                # Route to Validation
                routed_to = "validation"
                validation_result = await self.validation_service.validate(query)
                agent_response = validation_result.get("raw_response", "")
                
                # Generate final answer
                final_answer = await self.llm_service.generate(
                    query=query,
                    context=agent_response
                )
                final_answer = final_answer["answer"]
                
            else:  # LEGAL_ANALYSIS
                # Route to Knowledge
                routed_to = "knowledge"
                knowledge_result = await self.knowledge_service.process(
                    query=query,
                    collection=knowledge_base or "stock_law"
                )
                agent_response = knowledge_result.get("generated_answer", "")
                final_answer = agent_response
        
        return {
            "nlu_result": nlu_result.to_dict(),
            "routed_to": routed_to,
            "agent_response": agent_response,
            "final_answer": final_answer,
            "trace_id": trace_id
        }


# Singleton instance
_orchestrator_service: Optional[OrchestratorService] = None


def get_orchestrator_service() -> OrchestratorService:
    """Get or create Orchestrator service instance."""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service
