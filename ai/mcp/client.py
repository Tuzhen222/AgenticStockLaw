"""
MCP Client - Connect to MCP tool servers.

Helper for agents to call MCP tools.
"""
import asyncio
import logging
from typing import Any, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for connecting to MCP tool servers.
    
    Supports stdio and SSE transports.
    """
    
    def __init__(self, server_command: list[str] = None, sse_url: str = None):
        """
        Initialize MCP client.
        
        Args:
            server_command: Command to start server (for stdio transport)
            sse_url: URL for SSE transport (e.g., http://localhost:8100)
        """
        self.server_command = server_command
        self.sse_url = sse_url
        self._session = None
    
    @asynccontextmanager
    async def connect(self):
        """Connect to MCP server and yield session."""
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client
        from mcp.client.sse import sse_client
        
        try:
            if self.sse_url:
                async with sse_client(self.sse_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        yield session
            elif self.server_command:
                async with stdio_client(self.server_command[0], self.server_command[1:]) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        yield session
            else:
                raise ValueError("Either server_command or sse_url must be provided")
        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        async with self.connect() as session:
            result = await session.call_tool(tool_name, arguments)
            return result


# Pre-configured clients for common tools
def get_retrieve_client(transport: str = "stdio") -> MCPClient:
    """Get client for RetrieveTool MCP server."""
    if transport == "stdio":
        return MCPClient(server_command=["python", "-m", "ai.mcp.retrieve_server"])
    return MCPClient(sse_url="http://localhost:8100")


def get_rerank_client(transport: str = "stdio") -> MCPClient:
    """Get client for RerankTool MCP server."""
    if transport == "stdio":
        return MCPClient(server_command=["python", "-m", "ai.mcp.rerank_server"])
    return MCPClient(sse_url="http://localhost:8101")
