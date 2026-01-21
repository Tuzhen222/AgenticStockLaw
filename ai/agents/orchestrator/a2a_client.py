"""
A2A Client Helper - Utility for agent-to-agent communication.

Provides async methods for calling other agents via A2A protocol.
"""
import logging
from uuid import uuid4
from typing import Optional, Any

import httpx

from a2a.client import A2AClient, A2ACardResolver
from a2a.types import SendMessageRequest, MessageSendParams

logger = logging.getLogger(__name__)


class A2AClientHelper:
    """Helper class for making A2A calls to other agents."""
    
    def __init__(self, timeout: float = 120.0):
        self.timeout = timeout
    
    async def send_message(
        self,
        agent_url: str,
        text: str,
        trace_id: Optional[str] = None,
        memory_context: Optional[dict] = None
    ) -> dict:
        """
        Send a message to another agent via A2A protocol.
        
        Args:
            agent_url: Base URL of the target agent (e.g., http://localhost:9101)
            text: Message text to send
            trace_id: Optional trace ID for observability
            memory_context: Optional conversation memory context to include
            
        Returns:
            Response dictionary from the agent
        """
        trace_id = trace_id or uuid4().hex
        
        # Prefix message with memory context if provided
        full_text = text
        if memory_context and memory_context.get("has_history"):
            context_str = self._format_memory_context(memory_context)
            if context_str:
                full_text = f"[CONTEXT]\n{context_str}\n[/CONTEXT]\n\n{text}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            try:
                # 1. Discover agent via Agent Card
                resolver = A2ACardResolver(
                    httpx_client=http_client, 
                    base_url=agent_url
                )
                agent_card = await resolver.get_agent_card()
                
                # 2. Create A2A client
                client = A2AClient(
                    httpx_client=http_client, 
                    agent_card=agent_card
                )
                
                # 3. Build message request
                request = SendMessageRequest(
                    id=str(uuid4()),
                    params=MessageSendParams(
                        message={
                            "role": "user",
                            "parts": [{"kind": "text", "text": full_text}],
                            "messageId": uuid4().hex,
                        }
                    )
                )
                
                # 4. Send message
                response = await client.send_message(request)
                
                # 5. Extract response
                return self._extract_response(response, trace_id)
                
            except Exception as e:
                logger.error(f"A2A call to {agent_url} failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "trace_id": trace_id
                }
    
    def _extract_response(self, response: Any, trace_id: str) -> dict:
        """Extract usable response from A2A response object."""
        try:
            logger.info(f"[A2A] Extracting response, type: {type(response)}")
            
            # Handle different response structures
            if hasattr(response, 'result'):
                result = response.result
                logger.info(f"[A2A] Result type: {type(result)}, kind: {getattr(result, 'kind', 'N/A')}")
                
                # Handle message-type responses (new_agent_text_message)
                if hasattr(result, 'kind') and result.kind == 'message':
                    if hasattr(result, 'parts') and result.parts:
                        texts = []
                        for part in result.parts:
                            text = self._extract_text_from_part(part)
                            if text:
                                texts.append(text)
                        
                        if texts:
                            content = "\n".join(texts)
                            logger.info(f"[A2A] Extracted {len(content)} chars from message.parts")
                            return {
                                "success": True,
                                "content": content,
                                "trace_id": trace_id
                            }
                
                # Handle artifact-based responses
                if hasattr(result, 'artifacts') and result.artifacts:
                    texts = []
                    for artifact in result.artifacts:
                        logger.info(f"[A2A] Artifact type: {type(artifact)}, has parts: {hasattr(artifact, 'parts')}")
                        if hasattr(artifact, 'parts'):
                            for part in artifact.parts:
                                text = self._extract_text_from_part(part)
                                if text:
                                    texts.append(text)
                    
                    if texts:
                        content = "\n".join(texts)
                        logger.info(f"[A2A] Extracted {len(content)} chars from artifacts")
                        return {
                            "success": True,
                            "content": content,
                            "trace_id": trace_id
                        }
                
                # Handle status.message
                elif hasattr(result, 'status') and hasattr(result.status, 'message'):
                    msg = result.status.message
                    if hasattr(msg, 'parts'):
                        texts = []
                        for p in msg.parts:
                            text = self._extract_text_from_part(p)
                            if text:
                                texts.append(text)
                        
                        if texts:
                            content = "\n".join(texts)
                            logger.info(f"[A2A] Extracted {len(content)} chars from status.message")
                            return {
                                "success": True,
                                "content": content,
                                "trace_id": trace_id
                            }
            
            # Fallback: dump the response
            logger.warning(f"[A2A] Falling back to model dump")
            return {
                "success": True,
                "content": str(response.model_dump(mode="json", exclude_none=True)),
                "trace_id": trace_id
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract response: {e}")
            return {
                "success": True,
                "content": str(response),
                "trace_id": trace_id
            }
    
    def _extract_text_from_part(self, part: Any) -> str:
        """Extract text from an A2A Part object which may have different structures."""
        # Try direct text attribute
        if hasattr(part, 'text') and part.text:
            return part.text
        
        # Try part.root.text (A2A TextPart structure)
        if hasattr(part, 'root') and hasattr(part.root, 'text') and part.root.text:
            return part.root.text
        
        # Try dict
        if isinstance(part, dict) and 'text' in part:
            return part['text']
        
        return ""
    
    def _format_memory_context(self, memory_context: dict) -> str:
        """Format memory context for inclusion in A2A message."""
        parts = []
        
        # Add summary if exists
        summary = memory_context.get("summary", "")
        if summary:
            parts.append(f"Tóm tắt: {summary}")
        
        # Add recent messages
        messages = memory_context.get("messages", [])
        for msg in messages[-3:]:  # Only last 3 messages
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")[:300]  # Limit
            parts.append(f"{role}: {content}")
        
        return "\n".join(parts) if parts else ""


# Singleton instance
a2a_client = A2AClientHelper()
