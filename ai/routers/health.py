"""Health check router."""
import os
import logging

import httpx
from fastapi import APIRouter

from ai.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:9100")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    services = {}
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ORCHESTRATOR_URL}/.well-known/agent.json")
            services["orchestrator"] = "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception as e:
        services["orchestrator"] = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services=services
    )


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Gateway",
        "version": "1.0.0",
        "orchestrator": ORCHESTRATOR_URL,
        "endpoints": {
            "POST /chat": "Send query, receive final answer",
            "GET /health": "Health check",
            "GET /docs": "Swagger UI",
            "GET /debug/*": "Debug endpoints for each component",
        }
    }
