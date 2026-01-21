"""Configuration for AI services."""
import os

# Service ports
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", 9200))
ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", 9100))
KNOWLEDGE_PORT = int(os.getenv("KNOWLEDGE_PORT", 9101))
VALIDATION_PORT = int(os.getenv("VALIDATION_PORT", 9102))
REGULATORY_PORT = int(os.getenv("REGULATORY_PORT", 9103))

# Service URLs (for Docker/internal networking)
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", f"http://localhost:{ORCHESTRATOR_PORT}")
KNOWLEDGE_AGENT_URL = os.getenv("KNOWLEDGE_AGENT_URL", f"http://localhost:{KNOWLEDGE_PORT}")
VALIDATION_AGENT_URL = os.getenv("VALIDATION_AGENT_URL", f"http://localhost:{VALIDATION_PORT}")
REGULATORY_UPDATE_AGENT_URL = os.getenv("REGULATORY_UPDATE_AGENT_URL", f"http://localhost:{REGULATORY_PORT}")

# MCP Tool URLs
RETRIEVE_MCP_URL = os.getenv("RETRIEVE_MCP_URL", "http://localhost:8100")
RERANK_MCP_URL = os.getenv("RERANK_MCP_URL", "http://localhost:8101")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# All services configuration
ALL_SERVICES = {
    "gateway": {
        "name": "AI Gateway",
        "port": GATEWAY_PORT,
        "module": "ai.gateway",
        "function": "run_gateway"
    },
    "orchestrator": {
        "name": "Orchestrator Agent",
        "port": ORCHESTRATOR_PORT,
        "module": "ai.agents.orchestrator.executor",
        "args": ["--port", str(ORCHESTRATOR_PORT)]
    },
    "knowledge": {
        "name": "Knowledge Agent",
        "port": KNOWLEDGE_PORT,
        "module": "ai.agents.knowledge.executor",
        "args": ["--port", str(KNOWLEDGE_PORT)]
    },
    "validation": {
        "name": "Validation Agent",
        "port": VALIDATION_PORT,
        "module": "ai.agents.validate.executor",
        "args": ["--port", str(VALIDATION_PORT)]
    },
    "regulatory_update": {
        "name": "Regulatory Update Agent",
        "port": REGULATORY_PORT,
        "module": "ai.agents.regulatory_update.executor",
        "args": ["--port", str(REGULATORY_PORT)]
    },
    "retrieve": {
        "name": "Retrieve MCP Tool",
        "port": 8100,
        "module": "ai.mcp.retrieve",
        "args": ["--transport", "sse", "--port", "8100"]
    },
    "rerank": {
        "name": "Rerank MCP Tool",
        "port": 8101,
        "module": "ai.mcp.rerank",
        "args": ["--transport", "sse", "--port", "8101"]
    },
}

