"""
Conversation Memory Service - Redis-based short-term memory.

Features:
- Buffer of 5 most recent messages per session
- LLM summarization when buffer overflows
- Session recovery from PostgreSQL
- TTL for automatic expiration
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .client import get_redis_client

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Redis-based conversation memory with LLM summarization.
    
    Key Structure:
    - session:{session_id}:buffer → List of recent messages (max BUFFER_SIZE)
    - session:{session_id}:summary → Summary of older conversation
    - session:{session_id}:meta → Session metadata
    """
    
    BUFFER_SIZE = 5
    TTL_SECONDS = 3600  # 1 hour default
    
    def __init__(
        self,
        buffer_size: int = None,
        ttl_seconds: int = None,
        llm_client = None
    ):
        self.buffer_size = buffer_size or int(os.getenv("MEMORY_BUFFER_SIZE", self.BUFFER_SIZE))
        self.ttl_seconds = ttl_seconds or int(os.getenv("MEMORY_TTL_SECONDS", self.TTL_SECONDS))
        self.redis = get_redis_client()
        self._llm_client = llm_client
    
    def _buffer_key(self, session_id: str) -> str:
        return f"session:{session_id}:buffer"
    
    def _summary_key(self, session_id: str) -> str:
        return f"session:{session_id}:summary"
    
    def _meta_key(self, session_id: str) -> str:
        return f"session:{session_id}:meta"
    
    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get conversation context for LLM.
        
        Returns:
            {
                "summary": "Previous conversation summary...",
                "messages": [{"role": "user", "content": "..."}, ...],
                "has_history": True/False
            }
        """
        try:
            # Get summary
            summary = await self.redis.get(self._summary_key(session_id))
            
            # Get buffer
            buffer_data = await self.redis.lrange(self._buffer_key(session_id), 0, -1)
            messages = [json.loads(msg) for msg in buffer_data] if buffer_data else []
            
            # Refresh TTL
            if messages or summary:
                await self._refresh_ttl(session_id)
            
            return {
                "summary": summary or "",
                "messages": messages,
                "has_history": bool(summary or messages)
            }
            
        except Exception as e:
            logger.error(f"Failed to get context for session {session_id}: {e}")
            return {"summary": "", "messages": [], "has_history": False}
    
    async def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: Dict = None
    ) -> None:
        """
        Add a message to the buffer.
        If buffer exceeds BUFFER_SIZE, trigger summarization.
        """
        try:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            buffer_key = self._buffer_key(session_id)
            
            # Push to buffer
            await self.redis.rpush(buffer_key, json.dumps(message, ensure_ascii=False))
            
            # Check buffer size
            buffer_len = await self.redis.llen(buffer_key)
            
            if buffer_len > self.buffer_size:
                # Trigger summarization
                await self._summarize_and_compress(session_id)
            
            # Refresh TTL
            await self._refresh_ttl(session_id)
            
            logger.debug(f"Added {role} message to session {session_id}, buffer_len={buffer_len}")
            
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
    
    async def _summarize_and_compress(self, session_id: str) -> None:
        """
        Summarize old messages and compress buffer.
        Keeps only the most recent messages after summarization.
        """
        try:
            buffer_key = self._buffer_key(session_id)
            summary_key = self._summary_key(session_id)
            
            # Get all messages
            all_messages = await self.redis.lrange(buffer_key, 0, -1)
            messages = [json.loads(msg) for msg in all_messages]
            
            if len(messages) <= self.buffer_size:
                return
            
            # Split: older messages to summarize, recent to keep
            keep_count = self.buffer_size - 1  # Keep 4, summarize rest
            to_summarize = messages[:-keep_count]
            to_keep = messages[-keep_count:]
            
            # Get existing summary
            existing_summary = await self.redis.get(summary_key) or ""
            
            # Generate new summary with LLM
            new_summary = await self._call_llm_summarize(
                existing_summary=existing_summary,
                messages=to_summarize
            )
            
            # Update summary
            await self.redis.set(summary_key, new_summary)
            
            # Replace buffer with recent messages only
            await self.redis.delete(buffer_key)
            for msg in to_keep:
                await self.redis.rpush(buffer_key, json.dumps(msg, ensure_ascii=False))
            
            logger.info(f"Summarized {len(to_summarize)} messages for session {session_id}")
            
        except Exception as e:
            logger.error(f"Summarization failed for session {session_id}: {e}")
    
    async def _call_llm_summarize(
        self, 
        existing_summary: str, 
        messages: List[Dict]
    ) -> str:
        """Call LLM to summarize conversation."""
        try:
            from openai import AsyncOpenAI
            from ai.utils.api_key_manager import get_api_key_manager
            
            # Build conversation text
            convo_text = ""
            for msg in messages:
                role = "Người dùng" if msg["role"] == "user" else "Trợ lý"
                convo_text += f"{role}: {msg['content'][:500]}\n"
            
            # Get LLM client with key rotation
            if self._llm_client:
                client = self._llm_client
            else:
                try:
                    key_manager = get_api_key_manager()
                    api_key = key_manager.get_next_key()
                except Exception:
                    api_key = os.getenv("OPENAI_API_KEY")
                client = AsyncOpenAI(api_key=api_key)
            
            prompt = f"""Tóm tắt ngắn gọn cuộc hội thoại dưới đây thành 2-3 câu.
Giữ lại các thông tin quan trọng về pháp luật chứng khoán mà người dùng đã hỏi.

{f"Tóm tắt trước đó: {existing_summary}" if existing_summary else ""}

Cuộc hội thoại mới:
{convo_text}

Tóm tắt:"""

            response = await client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            # Fallback: simple concatenation
            if existing_summary:
                return f"{existing_summary} [Thêm {len(messages)} tin nhắn]"
            return f"[{len(messages)} tin nhắn trước đó]"
    
    async def load_from_postgresql(
        self, 
        session_id: str, 
        messages: List[Dict]
    ) -> None:
        """
        Load messages from PostgreSQL into Redis buffer.
        Called when user returns and Redis buffer is empty.
        """
        try:
            if not messages:
                return
            
            buffer_key = self._buffer_key(session_id)
            
            # Clear existing buffer
            await self.redis.delete(buffer_key)
            
            # Add recent messages (up to buffer_size)
            recent = messages[-self.buffer_size:]
            for msg in recent:
                formatted = {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("created_at", datetime.now().isoformat()),
                    "metadata": msg.get("extra_data", {})
                }
                await self.redis.rpush(buffer_key, json.dumps(formatted, ensure_ascii=False))
            
            # If more messages exist, summarize older ones
            if len(messages) > self.buffer_size:
                older = messages[:-self.buffer_size]
                summary = await self._call_llm_summarize("", older)
                await self.redis.set(self._summary_key(session_id), summary)
            
            await self._refresh_ttl(session_id)
            logger.info(f"Loaded {len(recent)} messages from PostgreSQL for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to load from PostgreSQL: {e}")
    
    async def _refresh_ttl(self, session_id: str) -> None:
        """Refresh TTL for all session keys."""
        keys = [
            self._buffer_key(session_id),
            self._summary_key(session_id),
            self._meta_key(session_id)
        ]
        for key in keys:
            await self.redis.expire(key, self.ttl_seconds)
    
    async def clear(self, session_id: str) -> None:
        """Clear all memory for a session."""
        try:
            keys = [
                self._buffer_key(session_id),
                self._summary_key(session_id),
                self._meta_key(session_id)
            ]
            await self.redis.delete(*keys)
            logger.info(f"Cleared memory for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to clear session {session_id}: {e}")
    
    async def has_memory(self, session_id: str) -> bool:
        """Check if session has any memory in Redis."""
        try:
            buffer_exists = await self.redis.exists(self._buffer_key(session_id))
            summary_exists = await self.redis.exists(self._summary_key(session_id))
            return bool(buffer_exists or summary_exists)
        except Exception as e:
            logger.error(f"Failed to check memory for session {session_id}: {e}")
            return False


# Singleton instance
_memory_service: Optional[ConversationMemory] = None


def get_memory_service() -> ConversationMemory:
    """Get or create ConversationMemory instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = ConversationMemory()
    return _memory_service
