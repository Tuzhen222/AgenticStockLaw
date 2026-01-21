"""
Agents package - A2A SDK based agent executors.

Provides agents:
- KnowledgeAgentExecutor: Document retrieval from knowledge base
- ValidateAgentExecutor: Legal document validation  
- OrchestratorAgentExecutor: Orchestrates other agents for comprehensive answers
- RegulatoryUpdateAgentExecutor: Monitors regulatory updates
"""

# A2A SDK based executors
from ai.agents.base import BaseAgentExecutor

__all__ = [
    "BaseAgentExecutor",
]
