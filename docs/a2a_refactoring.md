┌──────────────────────────────────────────────────────────────────────────────┐
│                                    USER / UI                                  │
│  Web / App / Chat / API                                                       │
└──────────────────────────────────────────────┬───────────────────────────────┘
                                               │ user message
                                               v
┌──────────────────────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR AGENT (Gateway) — A2A Server                      │
│                                                                              │
│  1) ONE-CALL NLU (LLM) -> { type, intent }                                    │
│     - type: GENERAL_CHAT | NOT_RELATED | RELATED                              │
│     - intent (if RELATED): LAW_CURRENCY_CHANGE | LEGAL_ANALYSIS               │
│                                                                              │
│  2) ROUTING RULES                                                             │
│     a) type = GENERAL_CHAT → answer normally (no agent calls)                 │
│     b) type = NOT_RELATED → “out of scope” response + redirect (no calls)     │
│     c) type = RELATED:                                                        │
│        - intent = LAW_CURRENCY_CHANGE:                                        │
│            → call ValidationAgent (A2A)                                       │
│            → aggregate → final answer                                         │
│        - intent = LEGAL_ANALYSIS:                                             │
│            → call KnowledgeAgent (A2A)                                        │
│            → if KnowledgeAgent has NO docs:                                   │
│                 call RegulatoryUpdateAgent (A2A)                              │
│                 (skip ValidationAgent)                                        │
│              else:                                                           │
│                 call ValidationAgent (A2A)                                    │
│            → aggregate → final answer                                         │
│                                                                              │
│  3) AGENT REGISTRY (module/service)                                           │
│     - AgentID → URL + skills + version + enabled + ACL                        │
│                                                                              │
│  4) AGGREGATOR                                                                │
│     Issue → Rules → Analysis → Risk → Next steps → Sources                    │
│                                                                              │
│  5) OBSERVABILITY                                                             │
│     trace_id propagation + audit log                                          │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │ resolve AgentID → URL
                               v
┌──────────────────────────────────────────────────────────────────────────────┐
│                         AGENT REGISTRY (module/service)                       │
│  - indexes agent endpoints + (optional) Agent Cards                           │
│  - used by orchestrator router                                                │
└───────────────┬──────────────────────────────┬──────────────────────────────┘
                │                              │
                │ A2A message/send              │ A2A message/send
                v                              v
┌────────────────────────────────────────────┐    ┌────────────────────────────────────────────┐
│          KnowledgeAgent — A2A Server       │    │          ValidationAgent — A2A Server      │
│  Purpose: retrieve internal legal docs     │    │  Purpose: currency/change questions        │
│                                            │    │  + validate retrieved docs                 │
│  Tools (internal):                         │    │  Tools (external):                        │
│   - RetrieveTool (RAG / vector search)     │    │   - BrightData SERP (via MCP tool)        │
│   - RerankTool (improve relevance order)  │    │  Output: effective status, amendment      │
│  Output: docs[] + citations + score       │    │  chain, changes summary, citations/links  │
└──────────────────────────┬───────────────┘    └────────────────────────────────────────────┘      
                           │                                            
                           │ if docs[] is empty                           
                           │ (ONLY then)                                  
                           v                                             
┌──────────────────────────────────────────┐                             
│     RegulatoryUpdateAgent — A2A Server   │
│  Purpose: fallback to find missing docs  │
│  Tools (external):                        │
│   - BrightData SERP (via MCP tool)       │
│  Output: found docs/links/excerpts        │
└──────────────────────────────────────────┘
