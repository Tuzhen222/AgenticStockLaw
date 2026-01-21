"""
Knowledge Agent Module

Sub-orchestrator agent for legal document retrieval and validation.
"""
from .executor import (
    KnowledgeAgentExecutor,
    build_app,
    get_agent_card,
    create_knowledge_executor
)

__all__ = [
    "KnowledgeAgentExecutor",
    "build_app",
    "get_agent_card",
    "create_knowledge_executor",
]
