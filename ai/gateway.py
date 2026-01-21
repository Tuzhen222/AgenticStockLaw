"""
AI Gateway - FastAPI application for chat and debug endpoints.

Architecture:
┌─────────────┐     ┌─────────────────┐     ┌───────────────────┐
│   Backend   │────►│   AI Gateway    │────►│   Orchestrator    │
│   (8000)    │     │   (9200/chat)   │     │   A2A (9100)      │
└─────────────┘     └─────────────────┘     └───────┬───────────┘
                                                    │
                         ┌──────────────────────────┼──────────────────────────┐
                         │                          │                          │
                         ▼                          ▼                          ▼
              ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
              │  KnowledgeAgent  │      │ ValidationAgent  │      │ RegulatoryAgent  │
              │   A2A (9101)     │      │   A2A (9102)     │      │   A2A (9103)     │
              └──────────────────┘      └──────────────────┘      └──────────────────┘

Endpoints:
- POST /chat - Main chat endpoint
- GET /health - Health check
- GET /debug/* - Debug endpoints for each component
"""
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from ai.routers import chat_router, debug_router, health_router, session_router

logger = logging.getLogger(__name__)

# Configuration
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", 9200))
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:9100")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"AI Gateway starting on port {GATEWAY_PORT}")
    logger.info(f"Orchestrator URL: {ORCHESTRATOR_URL}")
    yield
    logger.info("AI Gateway shutting down")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="AI Gateway",
        description="Gateway API for Vietnam Stock Law Assistant. Includes debug endpoints for testing individual components.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # CORS middleware for backend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(debug_router)
    app.include_router(session_router)
    
    return app


def run_gateway():
    """Run the gateway server."""
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=GATEWAY_PORT, log_level="info")


if __name__ == "__main__":
    run_gateway()
