"""Session management router - Handles session warmup and memory operations."""
import logging
from typing import List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from ai.knowledge.redis import get_memory_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["Session"])


class MessageData(BaseModel):
    """Message from PostgreSQL."""
    role: str
    content: str
    created_at: Optional[str] = None
    extra_data: Optional[dict] = None


class WarmupRequest(BaseModel):
    """Request to warmup a session from PostgreSQL history."""
    session_id: str
    messages: List[MessageData]


class WarmupResponse(BaseModel):
    """Response from warmup operation."""
    success: bool
    session_id: str
    loaded_count: int
    has_summary: bool


@router.post("/warmup", response_model=WarmupResponse)
async def warmup_session(request: WarmupRequest):
    """
    Warmup a session by loading messages from PostgreSQL into Redis.
    
    Called by backend when user opens an old chat session.
    This ensures Redis has the conversation context and TTL is refreshed.
    """
    try:
        memory = get_memory_service()
        
        # Check if session already has memory in Redis
        has_existing = await memory.has_memory(request.session_id)
        
        if has_existing:
            # Just refresh TTL
            await memory._refresh_ttl(request.session_id)
            context = await memory.get_context(request.session_id)
            logger.info(f"Session {request.session_id} already warm, refreshed TTL")
            return WarmupResponse(
                success=True,
                session_id=request.session_id,
                loaded_count=len(context.get("messages", [])),
                has_summary=bool(context.get("summary"))
            )
        
        # Load from PostgreSQL messages
        messages_dict = [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at,
                "extra_data": msg.extra_data or {}
            }
            for msg in request.messages
        ]
        
        await memory.load_from_postgresql(request.session_id, messages_dict)
        
        # Get the loaded context
        context = await memory.get_context(request.session_id)
        
        logger.info(f"Warmed up session {request.session_id} with {len(messages_dict)} messages")
        
        return WarmupResponse(
            success=True,
            session_id=request.session_id,
            loaded_count=len(context.get("messages", [])),
            has_summary=bool(context.get("summary"))
        )
        
    except Exception as e:
        logger.error(f"Session warmup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/{session_id}")
async def check_session(session_id: str):
    """Check if a session has memory in Redis."""
    try:
        memory = get_memory_service()
        has_memory = await memory.has_memory(session_id)
        context = await memory.get_context(session_id) if has_memory else {}
        
        return {
            "session_id": session_id,
            "has_memory": has_memory,
            "message_count": len(context.get("messages", [])),
            "has_summary": bool(context.get("summary"))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
