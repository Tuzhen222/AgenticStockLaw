"""
Rerank MCP Tool

Document reranking using Cohere API.
Run: python -m ai.mcp.rerank --transport sse --port 8101
"""
import logging

from mcp.server.fastmcp import FastMCP

from .server import config, get_cohere_client

logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("RerankTool")


@mcp.tool()
async def rerank(
    query: str,
    documents: list[str],
    top_n: int = 5,
    return_documents: bool = True
) -> dict:
    """
    Rerank documents by relevance to query using Cohere.
    
    Args:
        query: The search query
        documents: List of document texts to rerank
        top_n: Number of top results to return
        return_documents: Whether to include document text in results
        
    Returns:
        Dictionary with 'results' containing reranked documents with scores
    """
    logger.info(f"rerank: query='{query[:50]}...', docs={len(documents)}")
    
    if not documents:
        return {"results": [], "total": 0}
    
    try:
        client = get_cohere_client()
        
        response = client.rerank(
            query=query,
            documents=documents,
            model=config.cohere_model,
            top_n=min(top_n, len(documents)),
            return_documents=return_documents
        )
        
        results = []
        for result in response.results:
            item = {
                "index": result.index,
                "relevance_score": result.relevance_score
            }
            if return_documents and hasattr(result, 'document'):
                item["document"] = result.document.text
            results.append(item)
        
        return {"results": results, "total": len(results), "model": config.cohere_model}
        
    except ValueError as e:
        logger.warning(f"Cohere not configured: {e}, using mock rerank")
        return _mock_rerank(query, documents, top_n)
    except Exception as e:
        logger.error(f"Rerank error: {e}")
        return {"results": [], "error": str(e)}


@mcp.tool()
async def rerank_with_metadata(
    query: str,
    documents: list[dict],
    top_n: int = 5,
    text_field: str = "content"
) -> dict:
    """
    Rerank documents with metadata by relevance to query.
    
    Args:
        query: The search query
        documents: List of document dicts with text and metadata
        top_n: Number of top results to return
        text_field: Field name containing the document text
        
    Returns:
        Dictionary with 'results' containing reranked documents with original metadata
    """
    logger.info(f"rerank_with_metadata: query='{query[:50]}...', docs={len(documents)}")
    
    if not documents:
        return {"results": [], "total": 0}
    
    try:
        client = get_cohere_client()
        
        # Extract texts
        texts = [doc.get(text_field, "") for doc in documents]
        
        response = client.rerank(
            query=query,
            documents=texts,
            model=config.cohere_model,
            top_n=min(top_n, len(documents)),
            return_documents=False
        )
        
        # Combine with original metadata
        results = []
        for result in response.results:
            original_doc = documents[result.index]
            results.append({
                "relevance_score": result.relevance_score,
                **original_doc
            })
        
        return {"results": results, "total": len(results)}
        
    except ValueError as e:
        logger.warning(f"Cohere not configured: {e}, using mock rerank")
        return _mock_rerank_with_metadata(query, documents, top_n, text_field)
    except Exception as e:
        logger.error(f"Rerank with metadata error: {e}")
        return {"results": [], "error": str(e)}


def _mock_rerank(query: str, documents: list[str], top_n: int) -> dict:
    """Mock rerank for testing."""
    results = []
    for i, doc in enumerate(documents[:top_n]):
        query_words = set(query.lower().split())
        doc_words = set(doc.lower().split())
        overlap = len(query_words & doc_words)
        score = min(0.9, 0.5 + (overlap * 0.1))
        
        results.append({
            "index": i,
            "relevance_score": score,
            "document": doc
        })
    
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return {"results": results, "total": len(results), "model": "mock"}


def _mock_rerank_with_metadata(
    query: str, 
    documents: list[dict], 
    top_n: int,
    text_field: str
) -> dict:
    """Mock rerank with metadata."""
    results = []
    for doc in documents[:top_n]:
        text = doc.get(text_field, "")
        query_words = set(query.lower().split())
        doc_words = set(text.lower().split())
        overlap = len(query_words & doc_words)
        score = min(0.9, 0.5 + (overlap * 0.1))
        
        results.append({"relevance_score": score, **doc})
    
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return {"results": results, "total": len(results)}


def run_server(transport: str = "stdio", port: int = None):
    """Run the MCP server."""
    port = port or config.rerank_port
    
    if transport == "stdio":
        mcp.run()
    else:
        # SSE transport - run with uvicorn
        import uvicorn
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route
        
        sse = SseServerTransport("/messages/")
        
        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await mcp._mcp_server.run(
                    streams[0], streams[1], mcp._mcp_server.create_initialization_options()
                )
        
        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/messages/", endpoint=sse.handle_post_message, methods=["POST"]),
            ]
        )
        
        uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Rerank MCP Tool Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--port", type=int, default=config.rerank_port)
    args = parser.parse_args()
    
    logger.info(f"Starting Rerank MCP on transport={args.transport}, port={args.port}")
    run_server(args.transport, args.port)
