"""
BrightData MCP Client - Using SSE transport

Connects to BrightData MCP server via SSE for web search and scraping.
"""
import os
import logging
from typing import Optional, Any, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BrightDataResult:
    """Result from BrightData search."""
    title: str
    url: str
    snippet: str
    position: int = 0


@dataclass
class BrightDataOutput:
    """Output from BrightData MCP tool."""
    results: List[BrightDataResult]
    success: bool
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class BrightDataMCPClient:
    """
    MCP client for BrightData using SSE transport.
    """
    
    def __init__(
        self,
        api_token: Optional[str] = None,
        timeout: float = 60.0
    ):
        """
        Initialize BrightData MCP client.
        
        Args:
            api_token: BrightData API token (or BRIGHTDATA_MCP_TOKEN env var)
            timeout: Request timeout in seconds
        """
        self.api_token = api_token or os.getenv("BRIGHTDATA_MCP_TOKEN")
        self.timeout = timeout
        self._tools = None
        self._client = None
        
        if not self.api_token:
            logger.error("BRIGHTDATA_MCP_TOKEN not set")
    
    @property
    def sse_url(self) -> str:
        """Get the SSE URL with token."""
        if not self.api_token:
            return ""
        return f"https://mcp.brightdata.com/sse?token={self.api_token}"
    
    async def _get_tools(self):
        """Get or create MCP tools using LangChain adapter."""
        if self._tools is not None:
            return self._tools
        
        if not self.api_token:
            raise ValueError("BRIGHTDATA_MCP_TOKEN not configured. Please set it in .env file.")
        
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
            
            self._client = MultiServerMCPClient(
                {
                    "brightdata": {
                        "url": self.sse_url,
                        "transport": "sse",
                    }
                }
            )
            
            self._tools = await self._client.get_tools()
            logger.info(f"Connected to Bright Data MCP server. Tools: {len(self._tools)}")
            return self._tools
            
        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            raise ValueError("Please install langchain-mcp-adapters: pip install langchain-mcp-adapters")
        except Exception as e:
            logger.error(f"Failed to connect to BrightData MCP: {e}")
            raise
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a tool on the BrightData MCP server.
        
        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result as dictionary
        """
        tools = await self._get_tools()
        
        # Find the tool
        tool = None
        for t in tools:
            if t.name == tool_name or tool_name in t.name.lower():
                tool = t
                break
        
        if not tool:
            available = [t.name for t in tools]
            raise ValueError(f"Tool '{tool_name}' not found. Available: {available}")
        
        # Call the tool
        result = await tool.ainvoke(arguments)
        return result
    
    async def serp_search(
        self,
        query: str,
        country: str = "VN",
        language: str = "vi",
        num_results: int = 10
    ) -> BrightDataOutput:
        """
        Perform SERP search using search_engine tool.
        
        Args:
            query: Search query
            country: Country code
            language: Language code
            num_results: Number of results
            
        Returns:
            Search results
        """
        logger.info(f"BrightData SERP: query='{query[:50]}...'")
        
        try:
            tools = await self._get_tools()
            
            # Find search_engine tool
            search_tool = None
            for t in tools:
                if t.name == "search_engine":
                    search_tool = t
                    break
            
            if not search_tool:
                raise ValueError(f"search_engine tool not found. Available: {[t.name for t in tools]}")
            
            # Call search_engine with query dict
            result = await search_tool.ainvoke({"query": query})
            
            # Parse results - handle BrightData's response format
            results = []
            raw_result = result
            
            # BrightData returns a list with {type: text, text: JSON}
            if isinstance(result, list) and len(result) > 0:
                first_item = result[0]
                if isinstance(first_item, dict) and 'text' in first_item:
                    import json
                    try:
                        parsed = json.loads(first_item['text'])
                        raw_result = parsed
                        # Get organic results
                        organic = parsed.get('organic', [])
                        for i, item in enumerate(organic):
                            results.append(BrightDataResult(
                                title=item.get('title', ''),
                                url=item.get('link', item.get('url', '')),
                                snippet=item.get('description', item.get('snippet', '')),
                                position=i + 1
                            ))
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse BrightData response: {first_item['text'][:100]}")
            elif isinstance(result, dict):
                organic = result.get('organic', result.get('results', []))
                for i, item in enumerate(organic):
                    results.append(BrightDataResult(
                        title=item.get('title', ''),
                        url=item.get('link', item.get('url', '')),
                        snippet=item.get('description', item.get('snippet', '')),
                        position=i + 1
                    ))
            
            return BrightDataOutput(
                results=results,
                success=True,
                raw_response=raw_result if isinstance(raw_result, dict) else {"content": str(raw_result)}
            )
            
        except Exception as e:
            logger.error(f"BrightData SERP failed: {e}")
            return BrightDataOutput(
                results=[],
                success=False,
                error=str(e)
            )
    
    async def scrape_url(
        self,
        url: str
    ) -> BrightDataOutput:
        """
        Scrape a URL using scrape_as_markdown tool.
        
        Args:
            url: URL to scrape
            
        Returns:
            Scraped content
        """
        logger.info(f"BrightData scrape: url='{url}'")
        
        try:
            tools = await self._get_tools()
            
            # Find scrape_as_markdown tool
            scrape_tool = None
            for t in tools:
                if t.name == "scrape_as_markdown":
                    scrape_tool = t
                    break
            
            if not scrape_tool:
                raise ValueError(f"scrape_as_markdown tool not found. Available: {[t.name for t in tools]}")
            
            # Call scrape with URL dict
            result = await scrape_tool.ainvoke({"url": url})
            
            # Parse result properly
            content = ""
            if isinstance(result, list):
                # BrightData returns [{type: 'text', text: '...'}]
                text_parts = []
                for item in result:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = "\n".join(text_parts)
            elif isinstance(result, str):
                content = result
            else:
                content = str(result)
            
            logger.info(f"Scraped {len(content)} chars from {url}")
            
            return BrightDataOutput(
                results=[BrightDataResult(
                    title="Scraped Content",
                    url=url,
                    snippet=content[:1000],
                    position=1
                )],
                success=True,
                raw_response={"content": content}
            )
            
        except Exception as e:
            logger.error(f"BrightData scrape failed: {e}")
            return BrightDataOutput(
                results=[],
                success=False,
                error=str(e)
            )
    
    async def list_tools(self) -> List[str]:
        """List available BrightData tools."""
        tools = await self._get_tools()
        return [t.name for t in tools]


# Singleton instance
_brightdata_client: Optional[BrightDataMCPClient] = None


def get_brightdata_client() -> BrightDataMCPClient:
    """Get or create BrightData client instance."""
    global _brightdata_client
    if _brightdata_client is None:
        _brightdata_client = BrightDataMCPClient()
    return _brightdata_client
