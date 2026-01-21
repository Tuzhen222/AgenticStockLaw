"""
Orchestrator Agent Module

Gateway agent for Vietnam stock law Q&A system.
Handles NLU classification, routing to specialists, and final answer generation.
"""
from .executor import (
    OrchestratorAgentExecutor,
    build_app,
    get_agent_card
)
from .nlu import NLUClassifier, QueryType, Intent, NLUResult
from .a2a_client import A2AClientHelper, a2a_client
from .registry import AgentRegistry, AgentInfo, agent_registry
from .llm import LLMClient, llm_client

__all__ = [
    # Executor
    "OrchestratorAgentExecutor",
    "build_app",
    "get_agent_card",
    # NLU
    "NLUClassifier",
    "QueryType",
    "Intent",
    "NLUResult",
    # A2A Client
    "A2AClientHelper",
    "a2a_client",
    # Registry
    "AgentRegistry",
    "AgentInfo",
    "agent_registry",
    # LLM
    "LLMClient",
    "llm_client",
]
