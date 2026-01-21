"""
Retrieve MCP Tool

Document retrieval from Qdrant using Triton embeddings.
Run: python -m ai.mcp.retrieve --transport sse --port 8100
"""
import logging

from mcp.server.fastmcp import FastMCP

from .server import config, get_qdrant_client, generate_embedding

logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("RetrieveTool")


@mcp.tool()
async def retrieve(
    query: str,
    collection: str = None,
    limit: int = 5,
    score_threshold: float = 0.7
) -> dict:
    """
    Retrieve documents from the legal knowledge base.
    
    Args:
        query: Search query text
        collection: Qdrant collection name (default: stock_law_chunks)
        limit: Maximum number of documents to return
        score_threshold: Minimum similarity score (0-1)
        
    Returns:
        Dictionary with 'documents' list and 'total' count
    """
    collection = collection or config.default_collection
    logger.info(f"retrieve: query='{query[:50]}...', collection={collection}")
    
    try:
        # Generate embedding
        embedding = await generate_embedding(query)
        
        # Search Qdrant
        client = await get_qdrant_client()
        results = client.search(
            collection_name=collection,
            query_vector=embedding,
            limit=limit,
            score_threshold=score_threshold
        )
        
        # Format documents
        documents = []
        for r in results:
            documents.append({
                "id": str(r.id),
                "content": r.payload.get("child_text", ""),
                "score": r.score,
                "metadata": {k: v for k, v in r.payload.items() if k != "child_text"}
            })
        
        return {"documents": documents, "total": len(documents)}
        
    except Exception as e:
        logger.error(f"Retrieve error: {e}")
        return {"documents": [], "total": 0, "error": str(e)}


@mcp.tool()
async def search_similar(
    document_id: str,
    collection: str = None,
    limit: int = 5
) -> dict:
    """
    Find documents similar to a given document.
    
    Args:
        document_id: ID of the source document
        collection: Qdrant collection name
        limit: Maximum number of similar documents
        
    Returns:
        Dictionary with 'documents' list
    """
    collection = collection or config.default_collection
    
    try:
        client = await get_qdrant_client()
        
        # Get the document vector
        point = client.retrieve(
            collection_name=collection,
            ids=[document_id],
            with_vectors=True
        )
        
        if not point:
            return {"documents": [], "error": "Document not found"}
        
        # Search for similar
        results = client.search(
            collection_name=collection,
            query_vector=point[0].vector,
            limit=limit + 1
        )
        
        # Filter out self
        documents = [
            {
                "id": str(r.id),
                "content": r.payload.get("child_text", ""),
                "score": r.score,
                "metadata": {k: v for k, v in r.payload.items() if k != "child_text"}
            }
            for r in results if str(r.id) != document_id
        ][:limit]
        
        return {"documents": documents, "total": len(documents)}
        
    except Exception as e:
        logger.error(f"Search similar error: {e}")
        return {"documents": [], "error": str(e)}


def run_server(transport: str = "stdio", port: int = None):
    """Run the MCP server."""
    port = port or config.retrieve_port
    
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
    
    parser = argparse.ArgumentParser(description="Retrieve MCP Tool Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--port", type=int, default=config.retrieve_port)
    args = parser.parse_args()
    
    logger.info(f"Starting Retrieve MCP on transport={args.transport}, port={args.port}")
    run_server(args.transport, args.port)
