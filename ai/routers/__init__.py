"""Routers module for AI Gateway."""
from .chat import router as chat_router
from .debug import router as debug_router
from .health import router as health_router
from .session import router as session_router

__all__ = [
    "chat_router",
    "debug_router", 
    "health_router",
    "session_router",
]
