import json
import os
import logging
from typing import Optional, List, Dict, Any
from collections import defaultdict

import httpx
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
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import SendMessageRequest, MessageSendParams

from openai import AsyncOpenAI
from uuid import uuid4
from ai.utils.api_key_manager import get_api_key_manager

from ai.services.trace import AgentTracer

logger = logging.getLogger(__name__)


class KnowledgeAgentExecutor(AgentExecutor):
    """
    Knowledge agent that retrieves, filters, and validates legal documents.
    
    Flow:
    1. Enhance query → Retrieve 10 → Rerank 5 → LLM filter
    2. Group by parent_id
    3. No docs → Regulatory Agent (fallback)
    4. Has docs → Validation Agent → Return
    """
    
    def __init__(self):
        self.regulatory_url ="http://ai-regulatory:9103"
        self.validation_url = "http://ai-validation:9102"
        self.model = "gpt-4o-mini"
        # Use key manager for rotation
        try:
            self._key_manager = get_api_key_manager()
            logger.info(f"KnowledgeAgent: Key rotation enabled with {self._key_manager.get_key_count()} keys")
        except Exception as e:
            logger.warning(f"KnowledgeAgent: Key manager failed: {e}")
            self._key_manager = None
    
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
        """Execute knowledge retrieval workflow."""
        import time
        try:
            total_start = time.time()
            query = self._extract_query(context)
            trace_id = uuid4().hex[:8]
            
            # Initialize tracer for this request
            tracer = AgentTracer(trace_id)
            tracer.set_query(query)
            
            logger.info(f"[{trace_id}] KnowledgeAgent: {query[:100]}...")
            
            # Skip query enhancement to reduce OpenAI calls
            enhanced_query = query
            
            # Step 1: Retrieve top 10
            step1_start = time.time()
            logger.info(f"[{trace_id}] Step 1: Retrieving documents...")
            await self._send_status(event_queue, context, "Đang tìm kiếm tài liệu...")
            docs = await self._retrieve_documents(enhanced_query, limit=10)
            step1_time = (time.time() - step1_start) * 1000
            logger.info(f"[{trace_id}] Step 1: Retrieved {len(docs)} documents in {step1_time:.0f}ms")
            
            # Log to tracer
            tracer.set_retrieve(docs, step1_time)
            tracer.add_step("retrieve", f"Retrieved {len(docs)} docs", step1_time)
            
            for i, doc in enumerate(docs[:5]):
                logger.info(f"  [Step1 Doc {i+1}] {doc.get('metadata', {}).get('name_file', 'N/A')[:50]} | score={doc.get('score', 0):.3f}")
            
            if not docs:
                # No docs → Regulatory Agent fallback + retrieve from web_content
                logger.info(f"[{trace_id}] Step 2.1: No docs found, calling Regulatory Agent...")
                await self._send_status(event_queue, context, "Đang tìm kiếm trên web...")
                reg_start = time.time()
                reg_result = await self._call_regulatory_agent(query)
                reg_time = (time.time() - reg_start) * 1000
                logger.info(f"[{trace_id}] Step 2.1: Regulatory result = {len(reg_result)} chars")
                
                tracer.set_regulatory(called=True, time_ms=reg_time, reason="no_docs_retrieved")
                
                # Step 2.2: Retrieve from web_content collection (just ingested by regulatory agent)
                logger.info(f"[{trace_id}] Step 2.2: Retrieving from web_content collection...")
                await self._send_status(event_queue, context, "Đang tìm kiếm từ kết quả web...")
                web_docs = await self._retrieve_from_web_content(query, limit=10)
                logger.info(f"[{trace_id}] Step 2.2: Retrieved {len(web_docs)} docs from web_content")
                
                if web_docs:
                    # Step 2.3: Rerank web_content docs
                    logger.info(f"[{trace_id}] Step 2.3: Reranking web_content docs...")
                    reranked_web_docs = await self._rerank_documents(query, web_docs, top_n=5)
                    
                    # Step 2.4: Validate with SERP (Option B - use snippets, faster)
                    logger.info(f"[{trace_id}] Step 2.4: Validating web_content docs...")
                    await self._send_status(event_queue, context, "Đang xác minh hiệu lực...")
                    validated_docs = await self._call_validation_agent(self._group_web_docs(reranked_web_docs))
                    
                    if validated_docs:
                        # Format and return validated web docs
                        final_docs = self._format_web_docs_for_orchestrator(validated_docs)
                        tracer.set_answer(final_docs, len(final_docs))
                        trace_json = json.dumps(tracer.to_dict(), ensure_ascii=False)
                        final_response = f"{final_docs}\n\n<!-- TRACE:{trace_json} -->"
                        await event_queue.enqueue_event(new_agent_text_message(final_response))
                        return
                
                # If no web_content docs, return regulatory result as-is
                logger.info(f"[{trace_id}] Step 2.5: No web_content docs, returning regulatory result")
                tracer.set_answer(reg_result, len(reg_result))
                trace_json = json.dumps(tracer.to_dict(), ensure_ascii=False)
                final_response = f"{reg_result}\n\n<!-- TRACE:{trace_json} -->"
                await event_queue.enqueue_event(new_agent_text_message(final_response))
                return
            
            # Step 3: Rerank to top 5
            step3_start = time.time()
            logger.info(f"[{trace_id}] Step 3: Reranking documents...")
            await self._send_status(event_queue, context, "Đang xếp hạng kết quả...")
            reranked_docs = await self._rerank_documents(enhanced_query, docs, top_n=5)
            step3_time = (time.time() - step3_start) * 1000
            logger.info(f"[{trace_id}] Step 3: Reranked to {len(reranked_docs)} documents in {step3_time:.0f}ms")
            
            tracer.set_rerank(reranked_docs, step3_time)
            tracer.add_step("rerank", f"Reranked to {len(reranked_docs)} docs", step3_time)
            
            for i, doc in enumerate(reranked_docs):
                logger.info(f"  [Step3 Reranked {i+1}] {doc.get('metadata', {}).get('name_file', 'N/A')[:50]} | score={doc.get('score', 0):.3f}")
            
            # Skip LLM filter - use reranked_docs directly
            filtered_docs = reranked_docs
            
            if not filtered_docs:
                # No relevant docs after filter → Regulatory Agent fallback + retrieve from web_content
                logger.info(f"[{trace_id}] Step 4.1: No relevant docs, calling Regulatory Agent...")
                await self._send_status(event_queue, context, "Đang tìm kiếm trên web...")
                reg_start = time.time()
                reg_result = await self._call_regulatory_agent(query)
                reg_time = (time.time() - reg_start) * 1000
                logger.info(f"[{trace_id}] Step 4.1: Regulatory result = {len(reg_result)} chars")
                
                tracer.set_regulatory(called=True, time_ms=reg_time, reason="no_relevant_after_filter")
                
                # Step 4.2: Retrieve from web_content collection
                logger.info(f"[{trace_id}] Step 4.2: Retrieving from web_content collection...")
                await self._send_status(event_queue, context, "Đang tìm kiếm từ kết quả web...")
                web_docs = await self._retrieve_from_web_content(query, limit=10)
                logger.info(f"[{trace_id}] Step 4.2: Retrieved {len(web_docs)} docs from web_content")
                
                if web_docs:
                    # Step 4.3: Rerank web_content docs
                    logger.info(f"[{trace_id}] Step 4.3: Reranking web_content docs...")
                    reranked_web_docs = await self._rerank_documents(query, web_docs, top_n=5)
                    
                    # Step 4.4: Validate with SERP (Option B)
                    logger.info(f"[{trace_id}] Step 4.4: Validating web_content docs...")
                    await self._send_status(event_queue, context, "Đang xác minh hiệu lực...")
                    validated_docs = await self._call_validation_agent(self._group_web_docs(reranked_web_docs))
                    
                    if validated_docs:
                        # Format and return validated web docs
                        final_docs = self._format_web_docs_for_orchestrator(validated_docs)
                        tracer.set_answer(final_docs, len(final_docs))
                        trace_json = json.dumps(tracer.to_dict(), ensure_ascii=False)
                        final_response = f"{final_docs}\n\n<!-- TRACE:{trace_json} -->"
                        await event_queue.enqueue_event(new_agent_text_message(final_response))
                        return
                
                # If no web_content docs, return regulatory result as-is
                logger.info(f"[{trace_id}] Step 4.5: No web_content docs, returning regulatory result")
                tracer.set_answer(reg_result, len(reg_result))
                trace_json = json.dumps(tracer.to_dict(), ensure_ascii=False)
                final_response = f"{reg_result}\n\n<!-- TRACE:{trace_json} -->"
                await event_queue.enqueue_event(new_agent_text_message(final_response))
                return
            
            # Step 5: Group by parent_id
            grouped_docs = self._group_by_parent(filtered_docs)
            logger.info(f"[{trace_id}] Step 5: Grouped into {len(grouped_docs)} parent docs")
            
            tracer.set_grouped(grouped_docs)
            tracer.add_step("group", f"Grouped into {len(grouped_docs)} parent docs")
            
            for doc in grouped_docs:
                logger.info(f"  [Step5 Grouped] {doc.get('name_file', 'N/A')[:50]} | parent_text: {len(doc.get('parent_text', ''))} chars")
            
            # Step 6: Call Validation Agent to filter valid docs
            logger.info(f"[{trace_id}] Step 6: Calling Validation Agent to filter valid docs...")
            await self._send_status(event_queue, context, "Đang xác minh hiệu lực...")
            
            val_start = time.time()
            valid_docs = await self._call_validation_agent(grouped_docs)
            val_time = (time.time() - val_start) * 1000
            logger.info(f"[{trace_id}] Step 6: Got {len(valid_docs)} valid docs after validation in {val_time:.0f}ms")
            
            tracer.set_validation(called=True, time_ms=val_time, valid_count=len(valid_docs), docs=valid_docs)
            tracer.add_step("validation", f"Validated {len(valid_docs)} docs", val_time)
            
            # If no valid docs after validation, use all original docs
            if not valid_docs:
                logger.info(f"[{trace_id}] No valid docs returned, using original docs")
                valid_docs = grouped_docs
            
            # Step 7: Format valid docs' parent_text for Orchestrator
            formatted_docs = []
            for i, doc in enumerate(valid_docs):
                name_file = doc.get("name_file", "Không rõ nguồn")
                parent_text = doc.get("parent_text", "")[:3000]  # Limit each doc
                
                # Add validation status if available
                validation = doc.get("validation", {})
                status = validation.get("status", "")
                if status:
                    formatted_docs.append(f"**Nguồn: {name_file}** ({status})\n{parent_text}")
                else:
                    formatted_docs.append(f"**Nguồn: {name_file}**\n{parent_text}")
                
                # Log each doc
                logger.info(f"  [Step7 Doc {i+1}] {name_file[:60]} | {len(parent_text)} chars | status={status or 'N/A'}")
            
            final_docs = "\n\n---\n\n".join(formatted_docs)
            logger.info(f"[{trace_id}] Step 7: Formatted {len(valid_docs)} docs = {len(final_docs)} chars for Orchestrator")
            logger.info(f"[{trace_id}] Final docs preview:\n{final_docs[:500]}...")
            
            # Return docs for Orchestrator to generate answer
            total_time = time.time() - total_start
            logger.info(f"[{trace_id}] Knowledge Agent COMPLETE in {total_time:.2f}s")
            
            tracer.set_answer(final_docs, len(final_docs))
            
            # Include trace in response for logging
            trace_json = json.dumps(tracer.to_dict(), ensure_ascii=False)
            final_response = f"{final_docs}\n\n<!-- TRACE:{trace_json} -->"
            await event_queue.enqueue_event(new_agent_text_message(final_response))
            
        except Exception as e:
            logger.error(f"KnowledgeAgent failed: {e}", exc_info=True)
            await event_queue.enqueue_event(
                new_agent_text_message(f"❌ Lỗi: {str(e)}")
            )
    
    
    async def _retrieve_documents(self, query: str, limit: int = 10) -> List[Dict]:
        """Retrieve documents from Qdrant."""
        try:
            from ai.services.retrieve import get_retrieve_service
            
            service = get_retrieve_service()
            result = await service.retrieve(
                query=query,
                limit=limit,
                score_threshold=0.8  # Lower threshold to get more candidates
            )
            return result.get("documents", [])
        except Exception as e:
            logger.error(f"Retrieve failed: {e}")
            return []
    
    async def _rerank_documents(self, query: str, docs: List[Dict], top_n: int = 5) -> List[Dict]:
        """Rerank documents using Cohere."""
        try:
            from ai.services.rerank import get_rerank_service
            
            service = get_rerank_service()
            result = await service.rerank(
                query=query,
                documents=docs,
                top_n=top_n
            )
            return result.get("results", docs[:top_n])
        except Exception as e:
            logger.warning(f"Rerank failed: {e}")
            return docs[:top_n]
    
    def _group_by_parent(self, docs: List[Dict]) -> List[Dict]:
        """Group documents by parent_id and use parent_text."""
        groups = defaultdict(list)
        
        for doc in docs:
            metadata = doc.get("metadata", {})
            parent_id = metadata.get("parent_id", doc.get("id", "unknown"))
            groups[parent_id].append(doc)
        
        # Build grouped documents with parent_text
        grouped = []
        for parent_id, chunks in groups.items():
            # Get the best chunk (highest score)
            best_chunk = max(chunks, key=lambda x: x.get("score", 0))
            metadata = best_chunk.get("metadata", {})
            
            grouped.append({
                "parent_id": parent_id,
                "file_id": metadata.get("file_id", ""),
                "name_file": metadata.get("name_file", "Unknown"),
                "parent_text": metadata.get("parent_text", best_chunk.get("content", "")),
                "chunks": chunks,
                "score": best_chunk.get("score", 0)
            })
        
        # Sort by score
        grouped.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Grouped into {len(grouped)} parent documents")
        return grouped
    
    async def _retrieve_from_web_content(self, query: str, limit: int = 10) -> List[Dict]:
        """Retrieve documents from web_content collection after regulatory agent scrape."""
        try:
            from ai.services.retrieve import get_retrieve_service
            
            service = get_retrieve_service()
            result = await service.retrieve(
                query=query,
                collection="web_content",  # Different collection for scraped content
                limit=limit,
                score_threshold=0.6  # Lower threshold for web content
            )
            
            docs = result.get("documents", [])
            logger.info(f"Retrieved {len(docs)} docs from web_content collection")
            return docs
            
        except Exception as e:
            logger.error(f"Failed to retrieve from web_content: {e}")
            return []
    
    def _group_web_docs(self, docs: List[Dict]) -> List[Dict]:
        """Group web_content documents by parent_id for validation."""
        groups = defaultdict(list)
        
        for doc in docs:
            metadata = doc.get("metadata", {})
            parent_id = metadata.get("parent_id", doc.get("id", "unknown"))
            groups[parent_id].append(doc)
        
        grouped = []
        for parent_id, chunks in groups.items():
            best_chunk = max(chunks, key=lambda x: x.get("score", 0))
            metadata = best_chunk.get("metadata", {})
            
            grouped.append({
                "parent_id": parent_id,
                "file_id": metadata.get("file_id", ""),
                "name_file": metadata.get("name_file", "Unknown Web Content"),
                "parent_text": metadata.get("parent_text", best_chunk.get("content", "")),
                "source_url": metadata.get("source_url", ""),
                "scraped_at": metadata.get("scraped_at", ""),
                "chunks": chunks,
                "score": best_chunk.get("score", 0)
            })
        
        grouped.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Grouped web docs into {len(grouped)} parent documents")
        return grouped
    
    def _format_web_docs_for_orchestrator(self, docs: List[Dict]) -> str:
        """Format validated web_content docs for Orchestrator to generate answer."""
        formatted_parts = []
        
        for i, doc in enumerate(docs[:5]):  # Limit to 5 docs
            name_file = doc.get("name_file", "Không rõ nguồn")
            parent_text = doc.get("parent_text", "")[:3000]
            source_url = doc.get("source_url", "")
            
            validation = doc.get("validation", {})
            status = validation.get("status", "")
            
            header = f"**Nguồn: {name_file}**"
            if status:
                header += f" ({status})"
            if source_url:
                header += f"\n🔗 [{source_url[:60]}...]({source_url})"
            
            formatted_parts.append(f"{header}\n{parent_text}")
            logger.info(f"[FormatWebDocs {i+1}] {name_file[:50]} | {len(parent_text)} chars")
        
        final_content = "\n\n---\n\n".join(formatted_parts)
        logger.info(f"Formatted {len(docs)} web docs = {len(final_content)} chars for Orchestrator")
        return final_content
    
    async def _call_validation_agent(self, docs: List[Dict]) -> List[Dict]:
        """Call Validation Agent to filter valid documents."""
        try:
            import json
            
            # Prepare docs for validation (send as JSON)
            docs_for_validation = [
                {
                    "name_file": doc.get("name_file", ""),
                    "parent_text": doc.get("parent_text", "")[:500],
                    "file_id": doc.get("file_id", ""),
                    "score": doc.get("score", 0)
                }
                for doc in docs[:5]
            ]
            
            # Send docs as JSON to Validation Agent
            validation_query = json.dumps(docs_for_validation, ensure_ascii=False)
            
            async with httpx.AsyncClient(timeout=180.0) as http_client:
                resolver = A2ACardResolver(httpx_client=http_client, base_url=self.validation_url)
                agent_card = await resolver.get_agent_card()
                
                client = A2AClient(httpx_client=http_client, agent_card=agent_card)
                
                request = SendMessageRequest(
                    id=str(uuid4()),
                    params=MessageSendParams(
                        message={
                            "role": "user",
                            "parts": [{"kind": "text", "text": validation_query}],
                            "messageId": uuid4().hex,
                        }
                    )
                )
                
                response = await client.send_message(request)
                validation_result = self._extract_response(response)
                
                # Parse validation result
                try:
                    validated = json.loads(validation_result.get("content", "{}"))
                    return validated.get("validated_docs", docs)
                except json.JSONDecodeError:
                    # If not JSON, add validation info as-is
                    for doc in docs:
                        doc["validation"] = {"raw": validation_result.get("content", "")}
                    return docs
                
        except Exception as e:
            logger.error(f"Validation agent call failed: {e}")
            # Return docs without validation
            for doc in docs:
                doc["validation"] = {"status": "unknown", "error": str(e)}
            return docs
    
    async def _call_regulatory_agent(self, query: str) -> str:
        """Call Regulatory Agent as fallback."""
        try:
            async with httpx.AsyncClient(timeout=180.0) as http_client:
                resolver = A2ACardResolver(httpx_client=http_client, base_url=self.regulatory_url)
                agent_card = await resolver.get_agent_card()
                
                client = A2AClient(httpx_client=http_client, agent_card=agent_card)
                
                request = SendMessageRequest(
                    id=str(uuid4()),
                    params=MessageSendParams(
                        message={
                            "role": "user",
                            "parts": [{"kind": "text", "text": query}],
                            "messageId": uuid4().hex,
                        }
                    )
                )
                
                response = await client.send_message(request)
                result = self._extract_response(response)
                return result.get("content", "Không tìm thấy thông tin")
                
        except Exception as e:
            logger.error(f"Regulatory agent call failed: {e}")
            return f"❌ Không thể tìm kiếm thông tin: {str(e)}"
    
    def _extract_response(self, response: Any) -> dict:
        """Extract response content from A2A response."""
        try:
            if hasattr(response, 'result'):
                result = response.result
                if hasattr(result, 'artifacts') and result.artifacts:
                    texts = []
                    for artifact in result.artifacts:
                        if hasattr(artifact, 'parts'):
                            for part in artifact.parts:
                                if hasattr(part, 'text'):
                                    texts.append(part.text)
                    return {"success": True, "content": "\n".join(texts)}
            
            return {"success": True, "content": str(response)}
        except Exception as e:
            return {"success": False, "content": "", "error": str(e)}
    
    async def _generate_answer(self, query: str, docs: List[Dict], trace_id: str) -> str:
        """Generate final answer from validated documents."""
        # Build context from grouped docs
        context_parts = []
        for doc in docs[:3]:
            context_parts.append(
                f"**{doc['name_file']}**\n"
                f"{doc.get('parent_text', '')[:2000]}\n"
                f"Hiệu lực: {doc.get('validation', {}).get('content', 'Chưa xác minh')}"
            )
        
        context = "\n\n---\n\n".join(context_parts)
        
        try:
            llm = self._get_llm()
            response = await llm.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Bạn là trợ lý pháp luật chứng khoán Việt Nam.
Dựa vào tài liệu và thông tin hiệu lực, hãy trả lời câu hỏi.

Hướng dẫn:
- Trích dẫn số hiệu văn bản, điều khoản cụ thể
- Lưu ý tình trạng hiệu lực của văn bản
- Format câu trả lời rõ ràng với markdown"""
                    },
                    {
                        "role": "user",
                        "content": f"Câu hỏi: {query}\n\nTài liệu:\n{context}"
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            
            # Add sources
            sources = "\n".join([f"- {doc['name_file']}" for doc in docs[:3]])
            return f"{answer}\n\n---\n📚 **Nguồn:**\n{sources}"
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
        
        # Fallback
        return f"## 📚 Kết quả\n\n{context}\n\n*trace: {trace_id}*"
    
    async def _send_status(self, event_queue: EventQueue, context: RequestContext, message: str):
        """Send status update - simplified to just logging."""
        # Note: A2A TaskStatusUpdateEvent with Message was causing validation errors
        # Just log the status instead
        logger.info(f"[{context.task_id[:8]}] Status: {message}")
    
    def _extract_response(self, response) -> dict:
        """Extract text content from A2A response."""
        try:
            # Handle SendMessageSuccessResponse
            if hasattr(response, 'root'):
                response = response.root
            
            if hasattr(response, 'result'):
                result = response.result
                
                # Check if result is a Message
                if hasattr(result, 'parts'):
                    for part in result.parts:
                        if hasattr(part, 'root') and hasattr(part.root, 'text'):
                            return {"content": part.root.text}
                        elif hasattr(part, 'text'):
                            return {"content": part.text}
                
                # Check kind='message' response
                if hasattr(result, 'kind') and result.kind == 'message':
                    if hasattr(result, 'parts'):
                        for part in result.parts:
                            if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                return {"content": part.root.text}
                            elif hasattr(part, 'text'):
                                return {"content": part.text}
            
            # Fallback: convert to string
            return {"content": str(response)}
            
        except Exception as e:
            logger.error(f"_extract_response failed: {e}")
            return {"content": f"Error extracting response: {e}"}
    
    def _extract_query(self, context: RequestContext) -> str:
        """Extract query from context."""
        if context.message and context.message.parts:
            for part in context.message.parts:
                # A2A Part structure: part.root is TextPart with .text
                if hasattr(part, 'root') and hasattr(part.root, 'text') and part.root.text:
                    logger.info(f"[_extract_query] Found text in part.root.text: {part.root.text[:50]}...")
                    return part.root.text
                # Fallback: direct text attribute
                elif hasattr(part, 'text') and part.text:
                    logger.info(f"[_extract_query] Found text attribute: {part.text[:50]}...")
                    return part.text
                # Fallback: dict
                elif isinstance(part, dict) and 'text' in part:
                    logger.info(f"[_extract_query] Found text dict: {part['text'][:50]}...")
                    return part['text']
        logger.warning(f"[_extract_query] No text found in context.message.parts: {context.message}")
        return ""
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
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
        name="KnowledgeAgent",
        description="Retrieves, filters, and validates legal documents from knowledge base",
        url=os.getenv("KNOWLEDGE_AGENT_PUBLIC_URL", "http://ai-knowledge:9101/"),
        version="2.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="search_legal_docs",
                name="Search Legal Documents",
                description="Search and validate stock law regulations",
                tags=["search", "legal", "vietnam", "securities"],
                examples=[
                    "Quy định về công bố thông tin",
                    "Điều 8 Nghị định 155/2020"
                ]
            )
        ],
        supportsAuthenticatedExtendedCard=False
    )


def build_app() -> A2AStarletteApplication:
    """Build the A2A Starlette application."""
    executor = KnowledgeAgentExecutor()
    
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore()
    )
    
    return A2AStarletteApplication(
        agent_card=get_agent_card(),
        http_handler=handler
    )


def create_knowledge_executor(**kwargs) -> KnowledgeAgentExecutor:
    """Create a KnowledgeAgentExecutor instance."""
    return KnowledgeAgentExecutor(**kwargs)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Knowledge Agent A2A Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=9101, help="Port to bind")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting Knowledge Agent on {args.host}:{args.port}")
    
    app = build_app()
    uvicorn.run(app.build(), host=args.host, port=args.port)
