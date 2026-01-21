"""Chat router - Backend endpoint to call AI Gateway with user authentication."""
import os
import logging
from typing import Optional, List
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.crud import chat_crud
from app.logger.chat_logger import ChatLogger

logger = logging.getLogger(__name__)

# Initialize chat trace logger
chat_trace_logger = ChatLogger()

router = APIRouter(prefix="/chat", tags=["Chat"])

# AI Gateway URL
AI_GATEWAY_URL = os.getenv("AI_GATEWAY_URL", "http://ai-gateway:9200")


def log_chat_trace(query: str, result: dict, user_id: str = "anonymous") -> None:
    """
    Extract and log trace data from AI Gateway response.
    
    Trace is in result.metadata.knowledge_trace
    """
    try:
        metadata = result.get("metadata", {})
        trace = metadata.get("knowledge_trace")
        
        if trace:
            # Enrich trace with request info
            trace["request"] = {
                "query": query,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            trace["answer"] = result.get("answer", "")[:500]  # Truncate for logging
            chat_trace_logger.log_trace(trace)
            logger.info(f"Chat trace logged: {trace.get('trace_id', 'unknown')}")
        else:
            # Log basic trace if no knowledge_trace
            basic_trace = {
                "trace_id": metadata.get("trace_id", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query": query,
                "user_id": user_id,
                "routed_to": metadata.get("routed_to", "unknown"),
                "answer": result.get("answer", "")[:500]
            }
            chat_trace_logger.log_trace(basic_trace)
    except Exception as e:
        logger.warning(f"Failed to log chat trace: {e}")


# ============ Pydantic Schemas for Chat History ============

class SessionCreate(BaseModel):
    title: str = "New Chat"

class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    extra_data: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


# ============ Chat History Endpoints ============

@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all chat sessions for current user."""
    sessions = chat_crud.get_sessions(db, current_user.id)
    return [
        SessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat() if s.created_at else "",
            updated_at=s.updated_at.isoformat() if s.updated_at else ""
        )
        for s in sessions
    ]


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat session."""
    session = chat_crud.create_session(db, current_user.id, data.title)
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat() if session.created_at else "",
        updated_at=session.updated_at.isoformat() if session.updated_at else ""
    )


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all messages in a session and warmup Redis memory."""
    # Verify ownership
    session = chat_crud.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = chat_crud.get_messages(db, session_id)
    
    # Warmup Redis memory (async, don't block response)
    try:
        print(f"[WARMUP] Starting warmup for session {session_id} with {len(messages)} messages")
        warmup_data = {
            "session_id": str(session_id),
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "extra_data": m.extra_data
                }
                for m in messages
            ]
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{AI_GATEWAY_URL}/session/warmup",
                json=warmup_data,
                headers={"Content-Type": "application/json"}
            )
            print(f"[WARMUP] Response: {resp.status_code} - {resp.text[:100]}")
            logger.info(f"Warmed up session {session_id} with {len(messages)} messages")
    except Exception as e:
        print(f"[WARMUP] ERROR: {e}")
        logger.warning(f"Session warmup failed (non-blocking): {e}")
    
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            extra_data=m.extra_data,
            created_at=m.created_at.isoformat() if m.created_at else ""
        )
        for m in messages
    ]


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat session."""
    success = chat_crud.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


# ============ Existing Chat Endpoints ============



class ChatRequest(BaseModel):
    """Chat request from frontend."""
    query: str = Field(..., min_length=1, max_length=5000, examples=["Mức phạt công bố thông tin trễ?"])
    session_id: Optional[str] = None
    knowledge_base: Optional[str] = "stock_law_chunks"


class SourceDocument(BaseModel):
    """Source document in response."""
    title: str
    content: str
    score: Optional[float] = None
    metadata: Optional[dict] = None


class ChatResponse(BaseModel):
    """Chat response to frontend."""
    answer: str
    sources: list[SourceDocument] = []
    session_id: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Chat endpoint with user authentication.
    
    Receives query from authenticated user, forwards to AI Gateway,
    and returns the response.
    """
    try:
        logger.info(f"Chat request from user {current_user.id}: {request.query[:50]}...")
        
        # Prepare request for AI Gateway
        gateway_request = {
            "query": request.query,
            "session_id": request.session_id,
            "user_id": str(current_user.id),
            "knowledge_base": request.knowledge_base
        }
        
        # Call AI Gateway
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{AI_GATEWAY_URL}/chat",
                json=gateway_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                logger.error(f"AI Gateway error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"AI Gateway returned {response.status_code}"
                )
            
            result = response.json()
        
        # Log trace to chat_trace.log
        log_chat_trace(request.query, result, str(current_user.id))
        
        # Parse sources
        sources = []
        for src in result.get("sources", []):
            sources.append(SourceDocument(
                title=src.get("title", ""),
                content=src.get("content", ""),
                score=src.get("score"),
                metadata=src.get("metadata")
            ))
        
        logger.info(f"Chat response: {len(result.get('answer', ''))} chars, {len(sources)} sources")
        
        return ChatResponse(
            answer=result.get("answer", ""),
            sources=sources,
            session_id=result.get("session_id"),
            metadata=result.get("metadata")
        )
        
    except httpx.TimeoutException:
        logger.error("AI Gateway timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI Gateway timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"AI Gateway connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cannot connect to AI Gateway: {e}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/anonymous", response_model=ChatResponse)
async def chat_anonymous(request: ChatRequest):
    """
    Anonymous chat endpoint (no authentication required).
    
    For testing or public demo.
    """
    try:
        logger.info(f"Anonymous chat: {request.query[:50]}...")
        
        gateway_request = {
            "query": request.query,
            "session_id": request.session_id,
            "user_id": "anonymous",
            "knowledge_base": request.knowledge_base
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{AI_GATEWAY_URL}/chat",
                json=gateway_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"AI Gateway returned {response.status_code}"
                )
            
            result = response.json()
        
        sources = [
            SourceDocument(
                title=src.get("title", ""),
                content=src.get("content", ""),
                score=src.get("score"),
                metadata=src.get("metadata")
            )
            for src in result.get("sources", [])
        ]
        
        return ChatResponse(
            answer=result.get("answer", ""),
            sources=sources,
            session_id=result.get("session_id"),
            metadata=result.get("metadata")
        )
        
    except Exception as e:
        logger.exception(f"Anonymous chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    SSE Streaming chat endpoint - proxies to AI Gateway.
    
    Returns Server-Sent Events with tokens for real-time streaming.
    """
    from fastapi.responses import StreamingResponse
    
    async def stream_proxy():
        try:
            logger.info(f"Stream chat: {request.query[:50]}...")
            
            gateway_request = {
                "query": request.query,
                "session_id": request.session_id,
                "user_id": "anonymous",
                "knowledge_base": request.knowledge_base
            }
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    f"{AI_GATEWAY_URL}/chat/stream",
                    json=gateway_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
                        
        except Exception as e:
            import json
            logger.exception(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n".encode()
    
    return StreamingResponse(
        stream_proxy(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


class AuthChatRequest(BaseModel):
    """Authenticated chat request with session support."""
    query: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[int] = None  # DB session ID
    knowledge_base: Optional[str] = "stock_law_chunks"


@router.post("/stream/auth")
async def chat_stream_auth(
    request: AuthChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Authenticated SSE Streaming chat endpoint - saves messages to database.
    
    If session_id is provided, uses existing session.
    If session_id is None, creates a new session.
    """
    from fastapi.responses import StreamingResponse
    import json
    
    # Get or create session
    session_db_id = request.session_id
    if session_db_id is None:
        # Create new session with first 30 chars of query as title
        title = request.query[:30] + ("..." if len(request.query) > 30 else "")
        new_session = chat_crud.create_session(db, current_user.id, title)
        session_db_id = new_session.id
    else:
        # Verify ownership
        existing = chat_crud.get_session(db, session_db_id, current_user.id)
        if not existing:
            raise HTTPException(status_code=404, detail="Session not found")
    
    # Save user message
    chat_crud.create_message(db, session_db_id, "user", request.query)
    
    async def stream_and_save():
        full_response = []
        
        try:
            logger.info(f"Auth stream chat: user={current_user.id}, session={session_db_id}")
            
            gateway_request = {
                "query": request.query,
                "session_id": str(session_db_id),
                "user_id": str(current_user.id),
                "knowledge_base": request.knowledge_base
            }
            
            # First, send session_id to frontend
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_db_id})}\n\n"
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    f"{AI_GATEWAY_URL}/chat/stream",
                    json=gateway_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    async for chunk in response.aiter_bytes():
                        # Parse chunk to extract content for saving
                        try:
                            chunk_str = chunk.decode('utf-8')
                            for line in chunk_str.strip().split('\n'):
                                if line.startswith('data: '):
                                    data = json.loads(line[6:])
                                    if data.get('type') == 'token':
                                        full_response.append(data.get('content', ''))
                        except:
                            pass
                        yield chunk
            
            # Save assistant message after streaming complete
            assistant_content = ''.join(full_response)
            if assistant_content:
                chat_crud.create_message(db, session_db_id, "assistant", assistant_content)
                        
        except Exception as e:
            logger.exception(f"Auth stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n".encode()
    
    return StreamingResponse(
        stream_and_save(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
