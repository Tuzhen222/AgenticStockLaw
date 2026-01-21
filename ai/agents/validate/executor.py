"""
Validation Agent Executor - A2A Server implementation.

Two Modes:
1. DIRECT: User asks about law validity → search directly with user query
2. FROM KNOWLEDGE: Receives name_file metadata → search "name_file còn hiệu lực không"
   → Filter docs that are still valid
"""
import os
import re
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

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

from openai import AsyncOpenAI
from ai.utils.api_key_manager import get_api_key_manager

logger = logging.getLogger(__name__)


class ValidateAgentExecutor(AgentExecutor):
    """
    Validation Agent with two modes:
    
    Mode 1 (DIRECT): LAW_CURRENCY_CHANGE query
      - User asks about validity directly
      - Use MCP BrightData to search
      - LLM determines validity
    
    Mode 2 (FROM KNOWLEDGE): Receives docs with name_file
      - Extract name_file from each doc
      - Search "name_file còn hiệu lực không"
      - Filter and return only valid docs
    """
    
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # Use key manager for rotation
        try:
            self._key_manager = get_api_key_manager()
            logger.info(f"ValidateAgent: Key rotation enabled with {self._key_manager.get_key_count()} keys")
        except Exception as e:
            logger.warning(f"ValidateAgent: Key manager failed: {e}")
            self._key_manager = None
        
        # BrightData MCP client
        from ai.mcp.brightdata import BrightDataMCPClient
        self.brightdata = BrightDataMCPClient()
    
    def _get_llm(self) -> AsyncOpenAI:
        """Get OpenAI client with rotated API key"""
        if self._key_manager:
            api_key = self._key_manager.get_next_key()
        else:
            api_key = os.getenv("OPENAI_API_KEY")
        return AsyncOpenAI(api_key=api_key)
    
    async def execute(
        self, 
        context: RequestContext, 
        event_queue: EventQueue
    ) -> None:
        """Execute validation workflow."""
        try:
            query = self._extract_query(context)
            logger.info(f"ValidateAgent: {query[:100]}...")
            
            await self._send_status(event_queue, context, "Đang phân tích yêu cầu...")
            
            # Check if this is a direct query or docs from Knowledge Agent
            if self._is_docs_validation(query):
                # Mode 2: Validate docs from Knowledge Agent
                result = await self._validate_docs_from_knowledge(query)
            else:
                # Mode 1: Direct validity query
                result = await self._validate_direct_query(query)
            
            await event_queue.enqueue_event(new_agent_text_message(result))
            
        except Exception as e:
            logger.error(f"ValidateAgent failed: {e}", exc_info=True)
            await event_queue.enqueue_event(
                new_agent_text_message(f"❌ Lỗi xác minh: {str(e)}")
            )
    
    def _is_docs_validation(self, query: str) -> bool:
        """Check if query contains docs from Knowledge Agent (JSON format)."""
        return query.strip().startswith("{") or query.strip().startswith("[")
    
    async def _validate_direct_query(self, query: str) -> str:
        """
        Mode 1: Direct validation query from user.
        Search web for validity info, LLM validates.
        """
        await self._log("Mode 1: Direct query validation")
        
        # Extract document name if present
        doc_names = self._extract_document_names(query)
        
        if not doc_names:
            # Search with original query
            search_query = f"{query} hiệu lực site:thuvienphapluat.vn"
        else:
            # Search with extracted document name
            search_query = f"{doc_names[0]} còn hiệu lực không site:thuvienphapluat.vn"
        
        # MCP BrightData search
        search_result = await self.brightdata.serp_search(
            query=search_query,
            country="VN",
            language="vi",
            num_results=3
        )
        
        if not search_result.success:
            return f"❌ Không thể tìm kiếm: {search_result.error}"
        
        # Format search snippets
        snippets = []
        for r in search_result.results[:3]:
            snippets.append(f"- {r.title}: {r.snippet}")
        snippets_text = "\n".join(snippets)
        
        # LLM validates
        validation = await self._llm_validate_single(query, snippets_text)
        
        return self._format_direct_result(validation, search_result.results[:2])
    
    async def _validate_docs_from_knowledge(self, query: str) -> str:
        """
        Mode 2: Validate docs from Knowledge Agent.
        Receives docs with name_file, validates each, filters valid ones.
        """
        await self._log("Mode 2: Docs validation from Knowledge Agent")
        
        try:
            docs = json.loads(query)
            if not isinstance(docs, list):
                docs = [docs]
            logger.info(f"[Validation] Received {len(docs)} docs to validate")
        except json.JSONDecodeError:
            logger.error(f"[Validation] Invalid JSON received")
            return "❌ Invalid docs format from Knowledge Agent"
        
        # Validate all docs in PARALLEL for speed
        import asyncio
        
        async def validate_single_doc(doc):
            """Validate a single doc - called in parallel."""
            name_file = doc.get("name_file", "")
            if not name_file:
                logger.info(f"[Validation] Skipping doc without name_file")
                return None
            
            logger.info(f"[Validation] Checking: {name_file[:50]}")
            
            try:
                # Search for validity
                search_query = f"{name_file} còn hiệu lực không site:thuvienphapluat.vn"
                search_result = await self.brightdata.serp_search(
                    query=search_query,
                    country="VN",
                    language="vi",
                    num_results=2
                )
                
                if search_result.success and search_result.results:
                    snippets = "\n".join([r.snippet for r in search_result.results[:2]])
                    validation = await self._llm_check_validity(name_file, snippets)
                    doc["validation"] = validation
                    logger.info(f"[Validation] {name_file[:30]}: is_valid={validation.get('is_valid')}")
                else:
                    doc["validation"] = {"is_valid": None, "status": "unknown"}
                
                return doc
            except Exception as e:
                logger.error(f"[Validation] Error validating {name_file[:30]}: {e}")
                doc["validation"] = {"is_valid": None, "status": "error", "error": str(e)}
                return doc
        
        # Run all validations in parallel
        tasks = [validate_single_doc(doc) for doc in docs[:5]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter valid docs (not None and still valid or unknown)
        validated_docs = []
        for result in results:
            if result is None or isinstance(result, Exception):
                continue
            if result.get("validation", {}).get("is_valid", True) != False:
                validated_docs.append(result)
        
        logger.info(f"[Validation] Result: {len(validated_docs)}/{len(docs)} docs passed")
        
        return json.dumps({
            "validated_docs": validated_docs,
            "validated_count": len(validated_docs),
            "original_count": len(docs)
        }, ensure_ascii=False, indent=2)
    
    async def _llm_validate_single(self, query: str, snippets: str) -> dict:
        """LLM validates a single document query."""
        try:
            llm = self._get_llm()
            response = await llm.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Bạn là chuyên gia pháp luật Việt Nam.
Dựa vào thông tin tìm kiếm, xác định văn bản còn hiệu lực không.

Trả về JSON:
{
    "is_valid": true/false/null,
    "status": "còn hiệu lực" / "hết hiệu lực" / "đã sửa đổi" / "không rõ",
    "effective_date": "ngày có hiệu lực",
    "amendments": "văn bản sửa đổi nếu có",
    "reason": "giải thích ngắn gọn"
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Câu hỏi: {query}\n\nThông tin tìm được:\n{snippets}"
                    }
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return {"status": "error", "reason": str(e)}
    
    async def _llm_check_validity(self, name_file: str, snippets: str) -> dict:
        """Quick LLM check if document is still valid."""
        try:
            llm = self._get_llm()
            response = await llm.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Xác định văn bản còn hiệu lực không.
Trả về JSON: {"is_valid": true/false/null, "status": "...", "reason": "..."}"""
                    },
                    {
                        "role": "user",
                        "content": f"Văn bản: {name_file}\n\nThông tin:\n{snippets}"
                    }
                ],
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"is_valid": None, "status": "error", "reason": str(e)}
    
    def _extract_document_names(self, query: str) -> List[str]:
        """Extract document names from query."""
        patterns = [
            r"(Nghị định \d+/\d+/NĐ-CP)",
            r"(Thông tư \d+/\d+/TT-\w+)",
            r"(Luật [\w\s]+\d{4})",
            r"(Quyết định \d+/\d+/QĐ-\w+)",
        ]
        
        names = []
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            names.extend(matches)
        
        return names
    
    def _format_direct_result(self, validation: dict, results: list) -> str:
        """Format direct validation result."""
        status = validation.get("status", "không rõ")
        is_valid = validation.get("is_valid")
        
        emoji = "✅" if is_valid else ("❌" if is_valid is False else "❓")
        
        lines = [
            f"## {emoji} Kết quả xác minh hiệu lực\n",
            f"**Tình trạng:** {status}",
        ]
        
        if validation.get("effective_date"):
            lines.append(f"**Ngày hiệu lực:** {validation['effective_date']}")
        if validation.get("amendments"):
            lines.append(f"**Sửa đổi:** {validation['amendments']}")
        if validation.get("reason"):
            lines.append(f"**Chi tiết:** {validation['reason']}")
        
        if results:
            lines.append(f"\n---\n📚 **Nguồn:** [{results[0].title}]({results[0].url})")
        
        lines.append(f"\n*Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        
        return "\n".join(lines)
    
    async def _log(self, msg: str):
        logger.info(f"ValidateAgent: {msg}")
    
    async def _send_status(self, event_queue: EventQueue, context: RequestContext, message: str):
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(
                    state=TaskState.working,
                    message=Message(
                        role="agent", 
                        parts=[{"kind": "text", "text": message}],
                        messageId=f"status-{context.task_id}"
                    )
                ),
                final=False
            )
        )
    
    def _extract_query(self, context: RequestContext) -> str:
        if context.message and context.message.parts:
            for part in context.message.parts:
                if hasattr(part, 'text'):
                    return part.text
        return ""
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(
                    state=TaskState.canceled,
                    message=Message(
                        role="agent", 
                        parts=[{"kind": "text", "text": "Cancelled"}],
                        messageId=f"cancel-{context.task_id}"
                    )
                ),
                final=True
            )
        )


def get_agent_card() -> AgentCard:
    return AgentCard(
        name="ValidationAgent",
        description="Validates legal document effectiveness with two modes: direct query and docs validation",
        url=os.getenv("VALIDATION_AGENT_PUBLIC_URL", "http://ai-validation:9102/"),
        version="2.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="validate_direct",
                name="Validate Direct Query",
                description="Check document validity from user query",
                tags=["validate", "direct"],
                examples=["Nghị định 155/2020 còn hiệu lực không?"]
            ),
            AgentSkill(
                id="validate_docs",
                name="Validate Docs from Knowledge",
                description="Validate docs received from Knowledge Agent",
                tags=["validate", "docs"],
                examples=["[{\"name_file\": \"...\", \"parent_text\": \"...\"}]"]
            )
        ],
        supportsAuthenticatedExtendedCard=False
    )


def build_app() -> A2AStarletteApplication:
    executor = ValidateAgentExecutor()
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore()
    )
    return A2AStarletteApplication(
        agent_card=get_agent_card(),
        http_handler=handler
    )


def create_validate_executor(**kwargs) -> ValidateAgentExecutor:
    return ValidateAgentExecutor(**kwargs)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validation Agent A2A Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9102)
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting Validation Agent on {args.host}:{args.port}")
    
    app = build_app()
    uvicorn.run(app.build(), host=args.host, port=args.port)
