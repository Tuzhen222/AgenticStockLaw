"""Chat router - Main chat endpoint using A2A protocol."""
import os
import re
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from ai.schemas import ChatRequest, ChatResponse, SourceDocument
from ai.services import get_a2a_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])

# Agent URLs
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:9100")


def extract_trace(content: str) -> tuple[str, dict | None]:
    """
    Extract embedded trace from response content.
    
    Trace is embedded as: <!-- TRACE:{json} -->
    
    Returns:
        (clean_content, trace_dict) - content without trace marker, and parsed trace
    """
    pattern = r'<!-- TRACE:(\{.*?\}) -->'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        try:
            trace_json = match.group(1)
            trace_data = json.loads(trace_json)
            clean_content = re.sub(pattern, '', content).strip()
            return clean_content, trace_data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse trace JSON: {e}")
            return content, None
    
    return content, None


def log_step(trace_id: str, step: int, name: str, details: str = ""):
    """Log a pipeline step."""
    msg = f"[{trace_id}] Step {step}: {name}"
    if details:
        msg += f" | {details}"
    logger.info(msg)
    print(f"🔹 {msg}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint - Routes ALL requests through Orchestrator via A2A.
    
    Pipeline:
    1. Send query to Orchestrator (A2A)
    2. Orchestrator handles NLU + routing + LLM
    3. Return final answer
    """
    try:
        trace_id = uuid4().hex[:8]
        a2a_service = get_a2a_service()
        
        print(f"\n{'='*60}")
        print(f"🚀 NEW CHAT REQUEST [{trace_id}]")
        print(f"📝 Query: {request.query}")
        print(f"{'='*60}\n")
        
        # ========== Route to Orchestrator ==========
        log_step(trace_id, 1, "A2A Call", f"Sending to Orchestrator ({ORCHESTRATOR_URL})...")
        
        result = await a2a_service.call_agent(ORCHESTRATOR_URL, request.query, session_id=request.session_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Orchestrator call failed"))
        
        raw_answer = result.get("parsed_content", "")
        
        # Extract trace from response
        answer, trace_data = extract_trace(raw_answer)
        
        log_step(trace_id, 2, "Response", f"Got {len(answer)} chars from Orchestrator")
        
        if trace_data:
            logger.info(f"[{trace_id}] Trace extracted: {len(json.dumps(trace_data))} chars")
        
        print(f"\n{'='*60}")
        print(f"✅ CHAT COMPLETE [{trace_id}]")
        print(f"📤 Answer: {answer[:100]}...")
        print(f"{'='*60}\n")
        
        # Build metadata with trace
        metadata = {
            "routed_to": "orchestrator",
            "trace_id": trace_id
        }
        if trace_data:
            metadata["knowledge_trace"] = trace_data
        
        return ChatResponse(
            answer=answer,
            sources=[],
            session_id=request.session_id,
            metadata=metadata
        )
        
    except Exception as e:
        logger.exception(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    SSE Streaming Chat endpoint.
    
    Flow:
    1. Gateway calls Orchestrator via A2A (gets full response)
    2. Gateway splits response into words and streams as SSE
    3. Frontend receives tokens one by one for smooth UX
    
    Event types:
    - status: Pipeline status updates
    - token: Response tokens (words)
    - done: Completion signal
    - error: Error message
    """
    from fastapi.responses import StreamingResponse
    import json
    import asyncio
    
    async def event_generator():
        trace_id = uuid4().hex[:8]
        a2a_service = get_a2a_service()
        
        try:
            print(f"[STREAM {trace_id}] Starting for: {request.query[:50]}...")
            logger.info(f"[STREAM {trace_id}] Starting for: {request.query[:50]}...")
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'content': 'Đang xử lý câu hỏi...'})}\n\n"
            
            # Call Orchestrator via A2A - gets full response
            print(f"[STREAM {trace_id}] Calling Orchestrator at {ORCHESTRATOR_URL}")
            result = await a2a_service.call_agent(ORCHESTRATOR_URL, request.query, session_id=request.session_id)
            
            print(f"[STREAM {trace_id}] A2A result: success={result.get('success')}, error={result.get('error')}")
            print(f"[STREAM {trace_id}] parsed_content length: {len(result.get('parsed_content', ''))}")
            
            if not result.get("success"):
                error_msg = result.get("error", "Orchestrator call failed")
                print(f"[STREAM {trace_id}] ERROR: {error_msg}")
                logger.error(f"[STREAM {trace_id}] Error: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
                return
            
            answer = result.get("parsed_content", "")
            print(f"[STREAM {trace_id}] Got {len(answer)} chars: {answer[:200]}...")
            logger.info(f"[STREAM {trace_id}] Got {len(answer)} chars, streaming to client")
            
            if not answer:
                print(f"[STREAM {trace_id}] WARNING: Empty answer!")
                yield f"data: {json.dumps({'type': 'error', 'content': 'Không nhận được phản hồi từ hệ thống.'})}\n\n"
                return
            
            # Simulate streaming by splitting into words
            words = answer.split()
            print(f"[STREAM {trace_id}] Streaming {len(words)} words to client")
            for i, word in enumerate(words):
                if i > 0:
                    yield f"data: {json.dumps({'type': 'token', 'content': ' ' + word})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'token', 'content': word})}\n\n"
                # Small delay for smoother streaming effect
                await asyncio.sleep(0.01)
            
            yield f"data: {json.dumps({'type': 'done', 'trace_id': trace_id, 'routed_to': 'orchestrator'})}\n\n"
            print(f"[STREAM {trace_id}] Complete")
            logger.info(f"[STREAM {trace_id}] Complete")
            
        except Exception as e:
            print(f"[STREAM {trace_id}] EXCEPTION: {e}")
            logger.exception(f"[STREAM {trace_id}] Error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
