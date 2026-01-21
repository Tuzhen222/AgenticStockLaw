"""A2A Streaming Service - Streaming agent-to-agent communication using A2A SDK."""
import logging
from typing import AsyncGenerator
from uuid import uuid4

import httpx
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import SendMessageRequest, MessageSendParams

logger = logging.getLogger(__name__)


class A2AStreamingService:
    """Service for streaming calls to A2A agents using A2A SDK."""
    
    def __init__(self, timeout: float = 120.0):
        self.timeout = timeout
    
    async def call_agent_streaming(
        self,
        agent_url: str,
        query: str
    ) -> AsyncGenerator[dict, None]:
        """
        Call an A2A agent with streaming response using A2A SDK.
        
        Yields events:
        - {"type": "status", "content": "..."} - Status updates
        - {"type": "token", "content": "..."} - LLM tokens
        - {"type": "done", "trace_id": "..."} - Completion
        - {"type": "error", "content": "..."} - Error
        """
        trace_id = uuid4().hex[:8]
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http_client:
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
                            "parts": [{"kind": "text", "text": query}],
                            "messageId": uuid4().hex,
                        }
                    )
                )
                
                # 4. Send streaming message - yields events
                logger.info(f"[A2A STREAM {trace_id}] Calling agent at {agent_url}")
                
                async for event in client.send_message_streaming(request):
                    parsed = self._parse_sdk_event(event)
                    if parsed:
                        yield parsed
                
                yield {"type": "done", "trace_id": trace_id}
                
        except Exception as e:
            logger.error(f"[A2A STREAM {trace_id}] Error: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}
    
    def _parse_sdk_event(self, event) -> dict | None:
        """Parse event from A2A SDK streaming response."""
        try:
            # Handle different event types from A2A SDK
            event_type = type(event).__name__
            logger.debug(f"[A2A STREAM] Event type: {event_type}")
            
            # TaskStatusUpdateEvent - status updates like "Đang tìm kiếm..."
            if hasattr(event, 'status'):
                status = event.status
                if hasattr(status, 'state') and hasattr(status, 'message'):
                    text = self._extract_text_from_message(status.message)
                    if text:
                        state = str(status.state) if hasattr(status.state, 'value') else str(status.state)
                        if 'working' in state.lower():
                            return {"type": "status", "content": text}
                        else:
                            return {"type": "token", "content": text}
            
            # TaskArtifactUpdateEvent or final message
            if hasattr(event, 'artifact'):
                artifact = event.artifact
                if hasattr(artifact, 'parts'):
                    text = self._extract_text_from_parts(artifact.parts)
                    if text:
                        return {"type": "token", "content": text}
            
            # Direct message event
            if hasattr(event, 'message'):
                text = self._extract_text_from_message(event.message)
                if text:
                    return {"type": "token", "content": text}
            
            # Result with message
            if hasattr(event, 'result'):
                result = event.result
                if hasattr(result, 'status') and hasattr(result.status, 'message'):
                    text = self._extract_text_from_message(result.status.message)
                    if text:
                        return {"type": "token", "content": text}
            
            return None
            
        except Exception as e:
            logger.warning(f"[A2A STREAM] Failed to parse event: {e}")
            return None
    
    def _extract_text_from_message(self, message) -> str:
        """Extract text from A2A message."""
        if not message:
            return ""
        
        parts = message.parts if hasattr(message, 'parts') else []
        return self._extract_text_from_parts(parts)
    
    def _extract_text_from_parts(self, parts) -> str:
        """Extract text from A2A parts."""
        texts = []
        for part in parts or []:
            text = self._extract_text_from_part(part)
            if text:
                texts.append(text)
        return "".join(texts)
    
    def _extract_text_from_part(self, part) -> str:
        """Extract text from a single part."""
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


# Singleton
_streaming_service = None


def get_a2a_streaming_service() -> A2AStreamingService:
    """Get or create streaming service instance."""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = A2AStreamingService()
    return _streaming_service
