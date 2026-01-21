"""
Orchestrator Agent Executor - A2A Server implementation.

Gateway agent that:
1. Classifies queries via NLU
2. Routes to specialist agents (Knowledge, Validation)
3. Aggregates results and calls LLM to generate final answer
"""
import os
import logging
from typing import Optional
from uuid import uuid4

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    Message,
)
from a2a.utils import new_agent_text_message

from .nlu import NLUClassifier, QueryType, Intent
from .a2a_client import A2AClientHelper
from .registry import agent_registry
from .llm import LLMClient
from ai.knowledge.redis.memory import get_memory_service

logger = logging.getLogger(__name__)


class OrchestratorAgentExecutor(AgentExecutor):
    """
    Orchestrator agent that routes queries to specialists and generates final answers.
    """
    
    def __init__(self):
        self.nlu = NLUClassifier()
        self.a2a_client = A2AClientHelper()
        self.llm = LLMClient()
        self.memory = get_memory_service()
    
    async def execute(
        self, 
        context: RequestContext, 
        event_queue: EventQueue
    ) -> None:
        """Execute the orchestrator workflow."""
        try:
            query = self._extract_query(context)
            trace_id = uuid4().hex
            session_id = self._get_session_id(context)
            
            # Log query đầy đủ
            print(f"\n{'='*60}")
            print(f"📩 [ORCHESTRATOR] Received query:")
            print(f"   {query}")
            print(f"   trace_id: {trace_id}, session_id: {session_id}")
            print(f"{'='*60}\n")
            logger.info(f"[{trace_id}] Processing: {query[:100]}...")
            
            # Load conversation context from memory
            memory_context = {}
            if session_id:
                memory_context = await self.memory.get_context(session_id)
                msg_count = len(memory_context.get('messages', []))
                has_summary = bool(memory_context.get('summary'))
                print(f"📚 [MEMORY] session={session_id[:8]}... | messages={msg_count} | summary={has_summary}")
                logger.info(f"[{trace_id}] Memory: {msg_count} messages, summary={has_summary}")
                
                # Add user message to memory
                await self.memory.add_message(session_id, "user", query)
                print(f"📝 [MEMORY] Added user message to buffer")
            
            # Send working status
            await self._send_status(event_queue, context, "Đang phân loại câu hỏi...")
            
            # 1. NLU Classification
            nlu_result = await self.nlu.classify(query)
            logger.info(f"[{trace_id}] NLU: type={nlu_result.type}, intent={nlu_result.intent}")
            
            # 2. Route based on type and get answer
            if nlu_result.type == QueryType.GENERAL_CHAT:
                answer = await self._handle_chat(query, trace_id, memory_context)
            elif nlu_result.type == QueryType.NOT_RELATED:
                answer = self._handle_not_related()
            else:
                # RELATED type - call specialist agents
                answer = await self._handle_related(query, nlu_result.intent, trace_id, event_queue, context, memory_context)
            
            # Save assistant response to memory
            if session_id and answer:
                await self.memory.add_message(session_id, "assistant", answer[:2000])  # Limit size
            
            # 3. Send final answer
            await event_queue.enqueue_event(new_agent_text_message(answer))
            
        except Exception as e:
            logger.error(f"Orchestrator failed: {e}", exc_info=True)
            await event_queue.enqueue_event(
                new_agent_text_message(f"❌ Đã xảy ra lỗi: {str(e)}")
            )
    
    async def _handle_chat(self, query: str, trace_id: str, memory_context: dict = None) -> str:
        """Handle general chat queries - collect full response."""
        # Build context with conversation history
        chat_context = "Trả lời câu hỏi chung một cách thân thiện."
        if memory_context:
            history = self._format_memory_for_llm(memory_context)
            if history:
                chat_context = f"{chat_context}\n\nLịch sử hội thoại:\n{history}"
        
        tokens = []
        async for token in self.llm.generate_answer_stream(
            query=query,
            context=chat_context,
            trace_id=trace_id
        ):
            tokens.append(token)
        return "".join(tokens)
    
    def _handle_not_related(self) -> str:
        """Handle out-of-scope queries."""
        return (
            "Xin lỗi, câu hỏi này nằm ngoài phạm vi hỗ trợ của tôi.\n\n"
            "Tôi là trợ lý pháp luật chứng khoán, có thể giúp bạn:\n"
            "• Tra cứu quy định pháp luật chứng khoán\n"
            "• Kiểm tra hiệu lực văn bản\n"
            "• Tìm hiểu mức phạt vi phạm\n"
            "• Giải thích các điều khoản luật\n\n"
            "Hãy đặt câu hỏi liên quan đến pháp luật chứng khoán!"
        )
    
    async def _handle_related(
        self, 
        query: str, 
        intent: Optional[Intent],
        trace_id: str,
        event_queue: EventQueue,
        context: RequestContext,
        memory_context: dict = None
    ) -> str:
        """Handle legal-related queries by routing to specialist agents."""
        
        if intent == Intent.LAW_CURRENCY_CHANGE:
            # Only call ValidationAgent
            await self._send_status(event_queue, context, "Đang kiểm tra hiệu lực văn bản...")
            
            validation_url = agent_registry.get_url("validation")
            if not validation_url:
                return "ValidationAgent không khả dụng."
            
            result = await self.a2a_client.send_message(
                validation_url, query, trace_id, memory_context=memory_context
            )
            agent_response = result.get("content", "Không có kết quả")
            
        else:  # LEGAL_ANALYSIS
            # Call KnowledgeAgent
            await self._send_status(event_queue, context, "Đang tìm kiếm tài liệu pháp lý...")
            
            knowledge_url = agent_registry.get_url("knowledge")
            if not knowledge_url:
                return "KnowledgeAgent không khả dụng."
            
            result = await self.a2a_client.send_message(
                knowledge_url, query, trace_id, memory_context=memory_context
            )
            agent_response = result.get("content", "Không có kết quả")
        
        # Add conversation history to context
        full_context = agent_response
        if memory_context:
            history = self._format_memory_for_llm(memory_context)
            if history:
                full_context = f"Lịch sử hội thoại:\n{history}\n\n---\n\n{agent_response}"
        
        # Generate final answer using LLM - collect all tokens
        await self._send_status(event_queue, context, "Đang tổng hợp câu trả lời...")
        
        tokens = []
        async for token in self.llm.generate_answer_stream(
            query=query,
            context=full_context,
            trace_id=trace_id
        ):
            tokens.append(token)
        
        return "".join(tokens)
    
    async def _send_status(
        self, 
        event_queue: EventQueue, 
        context: RequestContext, 
        message: str
    ) -> None:
        """Send status update to client."""
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(
                    state=TaskState.working,
                    message=Message(
                        messageId=uuid4().hex,
                        role="agent",
                        parts=[{"kind": "text", "text": message}]
                    )
                ),
                final=False
            )
        )
    
    def _get_session_id(self, context: RequestContext) -> str:
        """Extract session ID from query text (embedded as [SESSION:xxx])."""
        import re
        
        # First, try to extract from message text
        text = self._extract_raw_query(context)
        match = re.match(r'^\[SESSION:([^\]]+)\]', text)
        if match:
            return match.group(1)
        
        # Fallback to context_id (for backward compatibility)
        if context.context_id:
            return context.context_id
        return None
    
    def _extract_raw_query(self, context: RequestContext) -> str:
        """Extract raw query text without processing."""
        if context.message and context.message.parts:
            for part in context.message.parts:
                if hasattr(part, 'text') and part.text:
                    return part.text
                if hasattr(part, 'root') and hasattr(part.root, 'text') and part.root.text:
                    return part.root.text
                if isinstance(part, dict) and part.get('text'):
                    return part['text']
        return ""
    
    def _format_memory_for_llm(self, memory_context: dict) -> str:
        """Format memory context for LLM prompt."""
        parts = []
        
        # Add summary if exists
        summary = memory_context.get("summary", "")
        if summary:
            parts.append(f"[Tóm tắt trước đó]: {summary}")
        
        # Add recent messages
        messages = memory_context.get("messages", [])
        for msg in messages:
            role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
            content = msg.get("content", "")[:500]  # Limit each message
            parts.append(f"{role}: {content}")
        
        return "\n".join(parts) if parts else ""
    
    def _extract_query(self, context: RequestContext) -> str:
        """Extract query text from request context, stripping session prefix."""
        import re
        
        raw_text = self._extract_raw_query(context)
        
        # Strip [SESSION:xxx] prefix if present
        cleaned = re.sub(r'^\[SESSION:[^\]]+\]\n?', '', raw_text)
        
        if not cleaned:
            print("[EXTRACT] WARNING: Could not extract query!")
        
        return cleaned.strip()
    
    async def cancel(
        self, 
        context: RequestContext, 
        event_queue: EventQueue
    ) -> None:
        """Cancel the task."""
        logger.info(f"Cancelling task {context.task_id}")
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(
                    state=TaskState.canceled,
                    message=Message(
                        messageId=uuid4().hex,
                        role="agent",
                        parts=[{"kind": "text", "text": "Task cancelled"}]
                    )
                ),
                final=True
            )
        )


def get_agent_card() -> AgentCard:
    """Return the orchestrator agent card."""
    return AgentCard(
        name="OrchestratorAgent",
        description="Gateway agent for Vietnam stock law Q&A system",
        url=os.getenv("ORCHESTRATOR_AGENT_PUBLIC_URL", "http://ai-orchestrator:9100/"),
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="legal_qa",
                name="Legal Q&A",
                description="Answer questions about Vietnam stock law",
                tags=["legal", "securities", "vietnam", "qa"],
                examples=[
                    "Mức phạt công bố thông tin trễ?",
                    "Nghị định 155 còn hiệu lực không?",
                    "Điều kiện niêm yết cổ phiếu?"
                ]
            )
        ],
        supportsAuthenticatedExtendedCard=False
    )


def build_app() -> A2AStarletteApplication:
    """Build the A2A Starlette application."""
    executor = OrchestratorAgentExecutor()
    
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore()
    )
    
    return A2AStarletteApplication(
        agent_card=get_agent_card(),
        http_handler=handler
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Orchestrator Agent A2A Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=9100, help="Port to bind")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting Orchestrator Agent on {args.host}:{args.port}")
    
    app = build_app()
    uvicorn.run(app.build(), host=args.host, port=args.port)
