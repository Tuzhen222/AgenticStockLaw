"""
RegulatoryUpdate Agent Executor - A2A Server implementation.

Fallback agent for finding missing legal documents via web search.
Called by KnowledgeAgent when no local docs are found.
"""
import os
import logging
from typing import Optional

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


# MCP client for BrightData (lazy import)
_mcp_client = None


async def get_mcp_client():
    """Get or create MCP client for BrightData."""
    global _mcp_client
    if _mcp_client is None:
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client
        # Note: In production, connect to running MCP server
        # For now, return None and use fallback
        pass
    return _mcp_client


class RegulatoryUpdateAgentExecutor(AgentExecutor):
    """
    Agent for finding legal documents via web search.
    
    Flow:
    1. MCP BrightData search (2 best results)
    2. Scrape full content from links
    3. Return content for Orchestrator to generate answer
    """
    
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # Use key manager for rotation
        try:
            self._key_manager = get_api_key_manager()
            logger.info(f"RegulatoryUpdateAgent: Key rotation enabled with {self._key_manager.get_key_count()} keys")
        except Exception as e:
            logger.warning(f"RegulatoryUpdateAgent: Key manager failed: {e}")
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
        """Execute web search and return content for Orchestrator."""
        try:
            query = self._extract_query(context)
            logger.info(f"RegulatoryUpdateAgent: {query[:100]}...")
            
            # Step 1: Send working status
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    taskId=context.task_id,
                    contextId=context.context_id,
                    status=TaskStatus(
                        state=TaskState.working,
                        message=Message(
                            role="agent",
                            parts=[{"kind": "text", "text": "Đang tìm kiếm văn bản pháp luật trên web..."}],
                            messageId=f"status-{context.task_id}"
                        )
                    ),
                    final=False
                )
            )
            
            # Step 2: MCP BrightData search (only 2 results)
            search_result = await self._search_web(query)
            
            if not search_result.get("success"):
                await event_queue.enqueue_event(
                    new_agent_text_message(f"❌ Không tìm thấy kết quả. {search_result.get('error', '')}")
                )
                return
            
            # Step 2.5: Ingest scraped content to web_content collection
            ingest_result = await self._ingest_to_web_content(search_result)
            
            # Step 3: Return simple success message (no LLM call needed)
            # Knowledge Agent will retrieve from web_content collection
            chunks_count = ingest_result.get("chunks_count", 0) if ingest_result else 0
            results = search_result.get("results", [])
            source_title = results[0].title if results else "Unknown"
            source_url = results[0].url if results else ""
            
            response = (
                f"✅ Đã tìm và lưu **{chunks_count}** đoạn văn bản từ web.\n\n"
                f"**Nguồn:** [{source_title}]({source_url})\n\n"
                f"*Knowledge Agent sẽ retrieve từ collection web_content.*"
            )
            await event_queue.enqueue_event(new_agent_text_message(response))
            
        except Exception as e:
            logger.error(f"RegulatoryUpdateAgent failed: {e}", exc_info=True)
            await event_queue.enqueue_event(
                new_agent_text_message(f"❌ Lỗi tìm kiếm: {str(e)}")
            )
    
    async def _search_web(self, query: str) -> dict:
        """Search web via BrightData SERP then scrape first result."""
        try:
            # Step 1: SERP search
            search_query = f"{query} site:thuvienphapluat.vn"
            result = await self.brightdata.serp_search(
                query=search_query,
                country="VN",
                language="vi",
                num_results=3
            )
            
            if not result.success or not result.results:
                return {
                    "success": False, 
                    "error": result.error or "Không tìm thấy kết quả"
                }
            
            logger.info(f"SERP found {len(result.results)} results for: {query[:50]}")
            for i, r in enumerate(result.results[:3]):
                logger.info(f"  [{i+1}] {r.title[:60]}...")
            
            # Step 2: Scrape first result
            first_url = result.results[0].url
            logger.info(f"Scraping: {first_url}")
            
            scrape_result = await self.brightdata.scrape_url(first_url)
            
            if scrape_result.success and scrape_result.raw_response:
                content = scrape_result.raw_response.get("content", "")
                # Clean up content
                if isinstance(content, list):
                    content = "\n".join([str(c.get('text', '')) if isinstance(c, dict) else str(c) for c in content])
                logger.info(f"Scraped {len(content)} chars from {first_url}")
                
                return {
                    "success": True,
                    "source": "brightdata_scrape",
                    "results": result.results,
                    "scraped_content": content
                }
            else:
                # Fallback to snippets
                logger.warning(f"Scrape failed, using snippets")
                snippets = "\n\n".join([f"**{r.title}**\n{r.snippet}" for r in result.results[:3]])
                return {
                    "success": True,
                    "source": "brightdata_serp",
                    "results": result.results,
                    "scraped_content": snippets
                }
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _ingest_to_web_content(self, search_result: dict) -> dict:
        """Ingest scraped content to web_content collection for future retrieval."""
        try:
            logger.info("[Ingest] Starting ingest to web_content...")
            from ai.services.web_content_ingest import get_web_content_ingest_service
            
            scraped_content = search_result.get("scraped_content", "")
            logger.info(f"[Ingest] Scraped content length: {len(scraped_content)} chars")
            
            if not scraped_content or len(scraped_content) < 100:
                logger.warning("[Ingest] Scraped content too short, skipping ingest")
                return {"success": False, "error": "Content too short", "chunks_count": 0}
            
            results = search_result.get("results", [])
            source_url = results[0].url if results else ""
            name_file = results[0].title if results else "Unknown Web Content"
            logger.info(f"[Ingest] Source: {name_file[:50]}... URL: {source_url[:50]}...")
            
            ingest_service = get_web_content_ingest_service()
            logger.info(f"[Ingest] Got ingest service, calling ingest()...")
            
            ingest_result = await ingest_service.ingest(
                content=scraped_content,
                source_url=source_url,
                name_file=name_file
            )
            
            logger.info(f"[Ingest] Result: {ingest_result}")
            
            if ingest_result.get("success"):
                logger.info(f"[Ingest] SUCCESS: Ingested {ingest_result.get('chunks_count', 0)} chunks to web_content")
            else:
                logger.warning(f"[Ingest] FAILED: {ingest_result.get('error', 'Unknown error')}")
            
            return ingest_result
                
        except Exception as e:
            logger.error(f"[Ingest] EXCEPTION: {e}", exc_info=True)
            return {"success": False, "error": str(e), "chunks_count": 0}

    
    def _extract_query(self, context: RequestContext) -> str:
        """Extract query text from request context."""
        if context.message and context.message.parts:
            for part in context.message.parts:
                # A2A SDK pattern: part.root.text
                if hasattr(part, 'root') and hasattr(part.root, 'text') and part.root.text:
                    logger.info(f"[RegulatoryAgent] Extracted query: {part.root.text[:50]}...")
                    return part.root.text
                # Direct text attribute
                if hasattr(part, 'text') and part.text:
                    logger.info(f"[RegulatoryAgent] Extracted query: {part.text[:50]}...")
                    return part.text
                # Dict format
                if isinstance(part, dict) and part.get('text'):
                    logger.info(f"[RegulatoryAgent] Extracted query: {part['text'][:50]}...")
                    return part['text']
        logger.warning("[RegulatoryAgent] Could not extract query from context")
        return ""
    
    async def cancel(
        self, 
        context: RequestContext, 
        event_queue: EventQueue
    ) -> None:
        """Cancel the task."""
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                taskId=context.task_id,
                contextId=context.context_id,
                status=TaskStatus(
                    state=TaskState.canceled,
                    message=Message(
                        role="agent",
                        parts=[{"kind": "text", "text": "Task cancelled"}],
                        messageId=f"cancel-{context.task_id}"
                    )
                ),
                final=True
            )
        )


def get_agent_card() -> AgentCard:
    """Return the agent card."""
    return AgentCard(
        name="RegulatoryUpdateAgent",
        description="Finds new legal documents via web search when not in local database",
        url=os.getenv("REGULATORY_AGENT_PUBLIC_URL", "http://ai-regulatory:9103/"),
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="find_new_regulations",
                name="Find New Regulations",
                description="Search web for latest legal documents not in local database",
                tags=["search", "web", "regulations", "update"],
                examples=[
                    "Tìm nghị định mới về chứng khoán 2024",
                    "Thông tư mới về công bố thông tin"
                ]
            )
        ],
        supportsAuthenticatedExtendedCard=False
    )


def build_app() -> A2AStarletteApplication:
    """Build the A2A Starlette application."""
    executor = RegulatoryUpdateAgentExecutor()
    
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
    
    parser = argparse.ArgumentParser(description="RegulatoryUpdate Agent A2A Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=9103, help="Port to bind")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting RegulatoryUpdate Agent on {args.host}:{args.port}")
    
    app = build_app()
    uvicorn.run(app.build(), host=args.host, port=args.port)
