# AI Gateway Implementation

## Overview

Implemented an AI Gateway service as the single public entry point for backend communication.

## Architecture

```
Backend (8000) → AI Gateway (9200 /chat) → Orchestrator (9100) → agents/tools → response
```

## File Structure

```
ai/api/
├── __init__.py     # Package exports
├── config.py       # Service configurations (GATEWAY, AGENTS, MCP_TOOLS)
├── runners.py      # Service runner functions
├── gateway.py      # FastAPI app with /chat endpoint
└── schemas.py      # Pydantic request/response models
```

## Files

### `ai/api/config.py`
Service configurations:
- `GATEWAY` - Gateway config (port 9200)
- `AGENTS` - A2A agent configs (orchestrator, knowledge, validation, regulatory_update)
- `MCP_TOOLS` - MCP tool configs (retrieve, rerank)

### `ai/api/runners.py`
Runner functions:
- `run_gateway()` - Run AI Gateway
- `run_agent()` - Run A2A agent
- `run_mcp_tool()` - Run MCP tool  
- `run_single_service()` - Run any service by name
- `run_all_services()` - Run all services in parallel

### `ai/api/gateway.py`
FastAPI application:
- `POST /chat` - Main chat endpoint
- `GET /health` - Health check

### `ai/api/schemas.py`
Pydantic models:
- `ChatRequest` - message, session_id, knowledge_base, metadata
- `ChatResponse` - answer, sources, session_id, metadata

### `ai/main.py`
Simple entry point that imports from `ai.api` and routes commands.

## Port Assignments

| Service | Port | Exposure |
|---------|------|----------|
| gateway | 9200 | Public |
| orchestrator | 9100 | 127.0.0.1 (debug) |
| knowledge | 9101 | 127.0.0.1 (debug) |
| validation | 9102 | 127.0.0.1 (debug) |
| regulatory_update | 9103 | 127.0.0.1 (debug) |
| retrieve | 8100 | 127.0.0.1 (debug) |
| rerank | 8101 | 127.0.0.1 (debug) |

## Usage

```bash
# Run gateway only
python -m ai.main gateway

# Run all services
python -m ai.main

# Swagger docs
http://localhost:9200/docs
```
