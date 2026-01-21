"""
MCP Tools Module

Provides document retrieval and reranking as MCP tools.
"""
from .server import config, MCPConfig
from .retrieve import retrieve, search_similar
from .rerank import rerank, rerank_with_metadata
from .brightdata import BrightDataMCPClient, get_brightdata_client

__all__ = [
    # Config
    "config",
    "MCPConfig",
    # Retrieve tools
    "retrieve",
    "search_similar",
    # Rerank tools
    "rerank",
    "rerank_with_metadata",
    # BrightData
    "BrightDataMCPClient",
    "get_brightdata_client",
]

