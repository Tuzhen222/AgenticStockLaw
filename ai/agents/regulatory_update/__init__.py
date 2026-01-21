"""
RegulatoryUpdate Agent Module

Fallback agent for finding missing legal documents via web search.
"""
from .executor import (
    RegulatoryUpdateAgentExecutor,
    build_app,
    get_agent_card
)

__all__ = [
    "RegulatoryUpdateAgentExecutor",
    "build_app",
    "get_agent_card",
]
