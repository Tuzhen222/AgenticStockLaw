# A2A Agent System - Implementation Documentation

## Overview

This document describes the A2A (Agent-to-Agent) agent system for Vietnam Stock Law Q&A.

## Architecture

```
User → Orchestrator Agent (:9100)
            │
            ├── LAW_CURRENCY_CHANGE → ValidationAgent (:9102)
            │
            └── LEGAL_ANALYSIS → KnowledgeAgent (:9101)
                                      │
                                      ├── retrieve (MCP :8100)
                                      ├── rerank (MCP :8101)
                                      │
                                      ├── if NO docs → RegulatoryUpdateAgent (:9103)
                                      │
                                      └── else → ValidationAgent (:9102) → merge → return
```

## Agents

### 1. Orchestrator Agent (Port 9100)
- **Purpose**: Gateway, NLU classification, routing, final answer generation
- **NLU Types**: `GENERAL_CHAT`, `NOT_RELATED`, `RELATED`
- **Intents**: `LAW_CURRENCY_CHANGE`, `LEGAL_ANALYSIS`
- **Files**: `ai/agents/orchestrator/`

### 2. Knowledge Agent (Port 9101)
- **Purpose**: Document retrieval and validation coordination
- **Sub-orchestrator**: Calls RegulatoryUpdate and Validation agents
- **MCP Tools**: `retrieve`, `rerank`
- **Files**: `ai/agents/knowledge/`

### 3. Validation Agent (Port 9102)
- **Purpose**: Check document validity, amendments, status
- **Skills**: `check_in_force`, `check_amendments`, `validate_info`
- **Files**: `ai/agents/validate/`

### 4. RegulatoryUpdate Agent (Port 9103)
- **Purpose**: Fallback web search for missing documents
- **Called by**: KnowledgeAgent when no local docs found
- **Files**: `ai/agents/regulatory_update/`

## MCP Servers

| Server | Port | Tools |
|--------|------|-------|
| RetrieveTool | 8100 | `retrieve`, `search_similar` |
| RerankTool | 8101 | `rerank`, `rerank_with_metadata` |
| BrightData | 8102 | `serp`, `web_scrape` |

## Running Agents

```bash
# Start all agents
python -m ai.agents.orchestrator.executor --port 9100
python -m ai.agents.knowledge.executor --port 9101
python -m ai.agents.validate.executor --port 9102
python -m ai.agents.regulatory_update.executor --port 9103

# Start MCP servers
python -m ai.mcp.retrieve_server --transport sse --port 8100
python -m ai.mcp.rerank_server --transport sse --port 8101
```

## Environment Variables

```bash
# LLM
OPENAI_API_KEY=sk-xxx
LLM_MODEL=gpt-4o

# BrightData MCP
BRIGHTDATA_MCP_TOKEN=66d7868f-1625-40ca-b0e6-7b27cf105685

# Agent URLs
KNOWLEDGE_AGENT_URL=http://localhost:9101
VALIDATION_AGENT_URL=http://localhost:9102
REGULATORY_UPDATE_AGENT_URL=http://localhost:9103

# Infra
TRITON_URL=localhost:8001
QDRANT_HOST=localhost
QDRANT_PORT=6334
```

## A2A Protocol

All agents communicate via A2A protocol:
- Discovery: `GET /.well-known/agent-card.json`
- Messages: `POST /message/send` (JSON-RPC)

Example call:
```python
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import SendMessageRequest, MessageSendParams

async with httpx.AsyncClient() as client:
    resolver = A2ACardResolver(httpx_client=client, base_url="http://localhost:9101")
    card = await resolver.get_agent_card()
    
    a2a_client = A2AClient(httpx_client=client, agent_card=card)
    request = SendMessageRequest(
        id="1",
        params=MessageSendParams(
            message={"role": "user", "parts": [{"kind": "text", "text": "Hello"}]}
        )
    )
    response = await a2a_client.send_message(request)
```
