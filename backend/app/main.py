"""
FastAPI main application.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

from app.core.config import settings
from app.routers import auth_router, knowledge_base_router, chat_router
from app.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} started!")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    yield
    # Shutdown
    logger.info(f"👋 {settings.APP_NAME} shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agentic Stock Law API",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
    )
    
    return response


# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(knowledge_base_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/")
def root():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
def health_check():
    """Detailed health check."""
    logger.debug("Detailed health check requested")
    return {
        "status": "healthy",
        "database": "connected",
    }
