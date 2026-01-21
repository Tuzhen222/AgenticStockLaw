# MCP Tool Servers

## Files

| File | Description |
|------|-------------|
| `retrieve_server.py` | Document retrieval (Triton + Qdrant) |
| `rerank_server.py` | Document reranking (Cohere) |
| `brightdata.py` | Web search (BrightData SERP) |
| `client.py` | MCP client for agent integration |

## Running Servers

```bash
# Stdio transport (for local agent communication)
python -m ai.mcp.retrieve_server --transport stdio
python -m ai.mcp.rerank_server --transport stdio

# SSE transport (for network access)
python -m ai.mcp.retrieve_server --transport sse --port 8100
python -m ai.mcp.rerank_server --transport sse --port 8101
```

## Environment Variables

```bash
# Triton (for retrieve)
TRITON_URL=localhost:8001
QDRANT_HOST=localhost
QDRANT_PORT=6334

# Cohere (for rerank)
COHERE_API_KEY=your-key

# BrightData (for web search)
BRIGHTDATA_API_TOKEN=your-token
```

## Usage from Agent

```python
from ai.mcp import get_retrieve_client

client = get_retrieve_client()
async with client.connect() as session:
    result = await session.call_tool("retrieve", {
        "query": "mức phạt công bố thông tin sai lệch",
        "limit": 5
    })
```
