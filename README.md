# AgenticStockLaw

Hệ thống hỏi đáp pháp luật chứng khoán Việt Nam sử dụng kiến trúc đa tác nhân (multi-agent RAG) với giao thức A2A (Agent-to-Agent) và MCP (Model Context Protocol).

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Tech Stack](#tech-stack)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Cài đặt & Khởi chạy](#cài-đặt--khởi-chạy)
- [Biến môi trường](#biến-môi-trường)
- [API Endpoints](#api-endpoints)
- [Lệnh Make](#lệnh-make)
- [Tài khoản demo](#tài-khoản-demo)

---

## Tổng quan

AgenticStockLaw là hệ thống hỏi đáp thông minh về luật chứng khoán Việt Nam. Hệ thống sử dụng:

- **RAG (Retrieval-Augmented Generation)**: tìm kiếm tài liệu pháp lý liên quan trước khi sinh câu trả lời.
- **Multi-agent A2A**: các agent chuyên biệt giao tiếp với nhau để phân tích, xác thực, và cập nhật thông tin pháp luật.
- **MCP Tools**: tích hợp công cụ tìm kiếm vector, rerank, và tìm kiếm web theo chuẩn Model Context Protocol.
- **Short-term Memory**: Redis lưu lịch sử hội thoại (TTL → tóm tắt khi vượt ngưỡng).

---

## Kiến trúc hệ thống

```
User Query
    │
    ▼
┌──────────────────────────────────────────┐
│              AI Gateway (:9200)          │
│  - Chat endpoint                        │
│  - Session management                   │
└───────────────────┬──────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────┐
│         Orchestrator Agent (:9100)       │
│  - LLM Classifier (NLU)                 │
│  - Agent Registry                       │
│  - Routing: GENERAL / NOT_RELATED /     │
│    LEGAL_ANALYSIS / LAW_CURRENCY_CHANGE │
└──────┬───────────────────────┬───────────┘
       │                       │
       ▼                       ▼
┌─────────────────┐   ┌──────────────────────┐
│ Knowledge Agent │   │  Validation Agent    │
│    (:9101)      │──►│      (:9102)         │
│  - MCP Retrieve │   │  - check_in_force    │
│  - MCP Rerank   │   │  - check_amendments  │
└────────┬────────┘   └──────────────────────┘
         │ (nếu không tìm thấy tài liệu)
         ▼
┌──────────────────────┐
│ RegulatoryUpdate     │
│ Agent (:9103)        │
│  - BrightData SERP   │
│  - Web fallback      │
└──────────────────────┘

MCP Tool Servers
├── Retrieve Tool (:8100)  ─── Triton gRPC + Qdrant
├── Rerank Tool   (:8101)  ─── Cohere API
└── BrightData    (:8102)  ─── SERP / Web Scrape

Storage Layer
├── PostgreSQL   - User data, sessions, audit log
├── Qdrant       - Vector DB (BGE-M3 embeddings, dim=1024)
├── MinIO        - Object storage (documents)
└── Redis        - Short-term memory (conversation history)

Inference
└── NVIDIA Triton Server
    ├── bge-m3 ONNX
    └── bge-m3 TensorRT (GPU)
```

---

## Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python, Alembic, PostgreSQL |
| AI Agents | LangGraph, A2A SDK, OpenAI GPT-4o |
| MCP Tools | MCP SDK, Cohere (rerank), BrightData (SERP) |
| Embeddings | BGE-M3 via NVIDIA Triton (ONNX / TensorRT) |
| Vector DB | Qdrant |
| Object Storage | MinIO |
| Memory | Redis |
| Reverse Proxy | Nginx |
| Container | Docker, Docker Compose |

---

## Cấu trúc dự án

```
AgenticStockLaw/
├── frontend/           # Next.js UI
├── backend/            # FastAPI REST API + DB
│   ├── app/
│   │   ├── routers/    # Endpoints
│   │   ├── crud/       # Database operations
│   │   ├── schemas/    # Pydantic schemas
│   │   └── services/   # Business logic
│   └── alembic/        # DB migrations
├── ai/                 # AI Gateway + Multi-agent system
│   ├── gateway.py      # AI Gateway (port 9200)
│   ├── agents/
│   │   ├── orchestrator/   # Orchestrator Agent (9100)
│   │   ├── knowledge/      # Knowledge Agent (9101)
│   │   ├── validate/       # Validation Agent (9102)
│   │   └── regulatory_update/ # Regulatory Agent (9103)
│   ├── mcp/            # MCP Tool Servers
│   │   ├── retrieve.py     # Retrieve Tool (8100)
│   │   ├── rerank.py       # Rerank Tool (8101)
│   │   └── brightdata.py   # BrightData SERP (8102)
│   ├── services/       # Shared services (LLM, memory, trace...)
│   └── knowledge/      # Vector DB & Redis helpers
├── triton_server/      # Model conversion + Triton config
│   ├── model_repository/
│   ├── convert_pytorch_to_onnx.py
│   └── convert_onnx_to_tensorrt.py
├── data/               # Tài liệu pháp luật (preprocessed)
├── nginx/              # Nginx config
├── docker-compose.yml       # Production
├── docker-compose.dev.yml   # Development (hot-reload)
└── Makefile            # Shortcut commands
```

---

## Cài đặt & Khởi chạy

### Yêu cầu

- Docker & Docker Compose
- (tuỳ chọn) NVIDIA GPU + CUDA cho Triton TensorRT
- Python ≥ 3.11 + [uv](https://github.com/astral-sh/uv) (nếu chạy local)
- Node.js ≥ 18 (nếu chạy frontend local)

### 1. Clone repo & cấu hình môi trường

```bash
git clone <repo-url>
cd AgenticStockLaw

# Tạo file .env cho AI module
cp ai/.env.example ai/.env
# Điền các API key: OPENAI_API_KEY, COHERE_API_KEY, BRIGHTDATA_API_TOKEN, ...
```

### 2a. Khởi chạy đầy đủ với Docker (khuyến nghị)

```bash
# Lần đầu tiên (setup DB + seed data)
make init-docker

# Sau đó chỉ cần
make up
```

### 2b. Development với hot-reload

```bash
# GPU Triton
make dev-gpu

# hoặc CPU Triton
make dev-cpu

# Setup DB + seed sau khi container lên
make db-migrate
```

### 2c. Khởi chạy hoàn chỉnh (DB + MinIO + Qdrant + Documents)

```bash
make run-all
```

### 3. Ingest tài liệu pháp luật

```bash
make upload-docs   # Upload lên MinIO
make ingest        # Ingest vào Qdrant vector DB
```

---

## Biến môi trường

Tạo file `ai/.env` với nội dung:

```env
# LLM
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Cohere (rerank)
COHERE_API_KEY=...

# BrightData (web search)
BRIGHTDATA_API_TOKEN=...

# Triton
TRITON_URL=localhost:8001

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=legal_law

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=legal-documents

# Redis
REDIS_URL=redis://localhost:6379

# Service Ports (tuỳ chọn, có giá trị mặc định)
GATEWAY_PORT=9200
ORCHESTRATOR_PORT=9100
KNOWLEDGE_PORT=9101
VALIDATION_PORT=9102
REGULATORY_PORT=9103
```

Tạo file `.env` ở thư mục gốc cho Docker Compose:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=agentic_stock_law
SECRET_KEY=your-secret-key
MINIO_USER=minioadmin
MINIO_PASSWORD=minioadmin
```

---

## API Endpoints

### Backend (port 8000)

| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/api/auth/login` | Đăng nhập |
| POST | `/api/auth/register` | Đăng ký |
| GET | `/api/chat/sessions` | Danh sách phiên chat |
| POST | `/api/chat/sessions` | Tạo phiên chat mới |
| DELETE | `/api/chat/sessions/{id}` | Xoá phiên chat |

### AI Gateway (port 9200)

| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/chat` | Gửi câu hỏi (streaming) |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |
| GET | `/debug/*` | Debug từng component |

---

## Lệnh Make

```bash
make help            # Xem tất cả lệnh
make init            # Khởi tạo lần đầu (local)
make init-docker     # Khởi tạo lần đầu (Docker)
make run-all         # Setup đầy đủ GPU

make dev             # Local dev (backend + frontend)
make dev-gpu         # Docker dev với GPU Triton
make dev-cpu         # Docker dev với CPU Triton

make up              # Start containers (production)
make down            # Stop containers
make logs            # Xem logs

make db-migrate                    # Chạy migrations
make db-makemigration msg="desc"   # Tạo migration mới
make db-reset                      # Reset DB

make convert-onnx    # Convert BGE-M3 sang ONNX
make upload-docs     # Upload tài liệu lên MinIO
make ingest          # Ingest vào Qdrant

make clean           # Xoá containers, volumes, cache
```

---

## Tài khoản demo

Sau khi chạy `init-docker` hoặc `run-all`:

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123456` | Admin |
| `user001` | `user123456` | User |

---

## Ports tham chiếu

| Service | Port |
|---------|------|
| Frontend (Next.js) | 3000 |
| Backend (FastAPI) | 8000 |
| Nginx | 80 |
| AI Gateway | 9200 |
| Orchestrator Agent | 9100 |
| Knowledge Agent | 9101 |
| Validation Agent | 9102 |
| Regulatory Agent | 9103 |
| MCP Retrieve Tool | 8100 |
| MCP Rerank Tool | 8101 |
| Triton HTTP | 8003 |
| Triton gRPC | 8001 |
| PostgreSQL | 5432 |
| Qdrant HTTP | 6333 |
| Qdrant gRPC | 6334 |
| MinIO API | 9000 |
| MinIO Console | 9001 |
| Redis | 6379 |
