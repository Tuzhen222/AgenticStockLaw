.PHONY: init dev dev-be dev-fe build up down logs clean install help run-all dev-gpu dev-cpu dev-all-down

# ============================================
# KHỞI TẠO TỪ ĐẦU (chạy lệnh này đầu tiên)
# ============================================
init:
	@echo "🚀 Khởi tạo Agentic Stock Law..."
	@echo ""
	@echo "📦 [1/4] Cài đặt dependencies backend..."
	cd backend && uv sync
	@echo ""
	@echo "📦 [2/4] Cài đặt dependencies frontend..."
	cd frontend && npm install --legacy-peer-deps
	@echo ""
	@echo "🐘 [3/4] Khởi động PostgreSQL..."
	docker-compose up -d postgres
	@echo "⏳ Đợi PostgreSQL khởi động..."
	@sleep 5
	@echo ""
	@echo "🗄️  [4/4] Chạy database migrations..."
	cd backend && uv run alembic upgrade head
	@echo ""
	@echo "✅ Khởi tạo hoàn tất!"
	@echo ""
	@echo "👉 Chạy 'make dev' để start development server"

# Khởi tạo với Docker (không cần cài local)
init-docker:
	@echo "🐳 Khởi tạo Agentic Stock Law với Docker..."
	@echo ""
	@echo "📦 [1/4] Build Docker images..."
	docker-compose build
	@echo ""
	@echo "🚀 [2/4] Start containers..."
	docker-compose up -d
	@echo ""
	@echo "⏳ Đợi services khởi động..."
	@sleep 10
	@echo ""
	@echo "🗄️  [3/4] Chạy database migrations..."
	docker-compose exec backend alembic upgrade head
	@echo ""
	@echo "📊 [4/4] Seed data..."
	docker-compose exec -T postgres psql -U postgres -d agentic_stock_law < backend/init.sql
	@echo ""
	@echo "✅ Khởi tạo hoàn tất!"
	@echo ""
	@echo "🌐 Backend:  http://localhost:8000"
	@echo "🌐 Frontend: http://localhost:3000"
	@echo "🌐 Nginx:    http://localhost:8080"
	@echo ""
	@echo "👤 Demo accounts:"
	@echo "   admin / admin123456"
	@echo "   user001 / user123456"
	@echo ""
	@echo "👉 Chạy 'make logs' để xem logs"

# Development (chạy local không cần Docker)
dev:
	@echo "🚀 Starting backend and frontend..."
	@make dev-be & make dev-fe

dev-be:
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-fe:
	cd frontend && npm run dev

# Install dependencies
install:
	cd backend && uv sync
	cd frontend && npm install

install-be:
	cd backend && uv sync

install-fe:
	cd frontend && npm install

# ============================================
# DOCKER COMMANDS
# ============================================
build:
	docker-compose build

up:
	docker-compose up -d

up-db:
	docker-compose up -d postgres

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-be:
	docker-compose logs -f backend

logs-fe:
	docker-compose logs -f frontend

logs-db:
	docker-compose logs -f postgres

restart:
	docker-compose restart

restart-be:
	docker-compose restart backend

restart-fe:
	docker-compose restart frontend

# Development với Docker (hot reload)
dev-docker:
	@echo "🔥 Starting development mode with hot reload..."
	docker-compose -f docker-compose.dev.yml up --build

dev-docker-d:
	@echo "🔥 Starting development mode (detached)..."
	docker-compose -f docker-compose.dev.yml up -d --build
	@echo "⏳ Đợi services khởi động..."
	@sleep 10
	@echo ""
	@echo "🗄️ Chạy database migrations..."
	docker-compose exec backend alembic upgrade head
	@echo ""
	@echo "📊 Seed data..."
	docker-compose exec -T postgres psql -U postgres -d agentic_stock_law < backend/init.sql
	@echo ""
	@echo "✅ Development mode started!"
	@echo "🌐 Backend:  http://localhost:8000 (auto-reload on .py changes)"
	@echo "🌐 Frontend: http://localhost:3000 (hot-reload on .tsx changes)"
	@echo ""
	@echo "👉 Run 'make logs-dev' to view logs"

down-dev:
	docker-compose -f docker-compose.dev.yml down

logs-dev:
	docker-compose -f docker-compose.dev.yml logs -f

reset-dev:
	@echo "🔄 Resetting development database..."
	docker-compose -f docker-compose.dev.yml down -v
	@echo "✅ Database volume removed. Run 'make dev-docker' to start fresh."

# ============================================
# DATABASE
# ============================================
db-shell:
	docker-compose exec postgres psql -U postgres -d agentic_stock_law

db-migrate:
	cd backend && uv run alembic upgrade head

db-makemigration:
	cd backend && uv run alembic revision --autogenerate -m "$(msg)"

db-downgrade:
	cd backend && uv run alembic downgrade -1

db-history:
	cd backend && uv run alembic history

db-reset:
	docker-compose down -v
	docker-compose up -d postgres
	@echo "⏳ Đợi PostgreSQL khởi động..."
	@sleep 5
	cd backend && uv run alembic upgrade head
	@echo "✅ Database đã reset!"

# ============================================
# CLEANUP
# ============================================
clean:
	docker-compose down -v --rmi local
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true

# ============================================
# RUN ALL (Complete Setup)
# ============================================
run-all:
	@echo "🚀 Starting complete development setup..."
	@echo ""
	@echo "🔥 [1/5] Starting all services with GPU Triton..."
	docker-compose -f docker-compose.dev.yml --profile with-triton-cpu up -d
	@echo ""
	@echo "⏳ Waiting for services to start..."
	@sleep 15
	@echo ""
	@echo "🗄️  [2/5] Running database migrations..."
	docker-compose -f docker-compose.dev.yml exec -T backend alembic upgrade head
	@echo ""
	@echo "📊 [3/5] Seeding initial data..."
	docker-compose -f docker-compose.dev.yml exec -T postgres psql -U postgres -d agentic_stock_law < backend/init.sql
	@echo ""
	@echo "📤 [4/5] Uploading documents to MinIO..."
	cd ai/utils && uv run python upload_documents.py
	@echo ""
	@echo "📥 [5/5] Ingesting data into Qdrant..."
	cd ai && ./entrypoint.sh
	@echo ""
	@echo "✅ Complete setup finished!"
	@echo ""
	@echo "🌐 Services:"
	@echo "   Frontend:      http://localhost:3000"
	@echo "   Backend:       http://localhost:8000"
	@echo "   AI Gateway:    http://localhost:9200"
	@echo "   Triton gRPC:   http://localhost:8001"
	@echo "   Qdrant:        http://localhost:6333"
	@echo "   MinIO:         http://localhost:9000"
	@echo ""
	@echo "👉 Run 'make dev-logs' to view logs"

dev-gpu:
	@echo "🔥 Starting all services with GPU Triton..."
	docker-compose -f docker-compose.dev.yml --profile with-triton-gpu up -d

dev-cpu:
	@echo "🔥 Starting all services with CPU Triton..."
	docker-compose -f docker-compose.dev.yml --profile with-triton-cpu up -d

dev-all-down:
	docker-compose -f docker-compose.dev.yml --profile with-triton-gpu --profile with-triton-cpu down

# ============================================
# AI / MODEL COMMANDS
# ============================================
convert-onnx:
	@echo "🔄 Converting PyTorch model to ONNX..."
	cd triton_server && python convert_pytorch_to_onnx.py
	@echo "✅ ONNX conversion complete!"

ai-entrypoint:
	@echo "🚀 Running AI entrypoint..."
	cd ai && bash entrypoint.sh
	@echo "✅ AI entrypoint complete!"

upload-docs:
	@echo "📤 Uploading documents to MinIO..."
	cd ai && MINIO_HOST=localhost uv run python utils/upload_documents.py
	@echo "✅ Document upload complete!"

ingest:
	@echo "📥 Ingesting data into Qdrant..."
	cd ai && uv run python -m knowledge.vector_db.ingest
	@echo "✅ Data ingestion complete!"

# ============================================
# HELP
# ============================================
help:
	@echo "╔══════════════════════════════════════════════╗"
	@echo "║       🏛️  AGENTIC STOCK LAW                  ║"
	@echo "╚══════════════════════════════════════════════╝"
	@echo ""
	@echo "🎬 BẮT ĐẦU:"
	@echo "  make init        - Khởi tạo từ đầu (chạy 1 lần)"
	@echo "  make run-all     - Setup đầy đủ (GPU Triton + DB + MinIO + Qdrant)"
	@echo "  make dev         - Chạy development server"
	@echo ""
	@echo "📦 CÀI ĐẶT:"
	@echo "  make install     - Cài đặt tất cả dependencies"
	@echo "  make install-be  - Cài đặt backend"
	@echo "  make install-fe  - Cài đặt frontend"
	@echo ""
	@echo "🐳 DOCKER:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start tất cả containers"
	@echo "  make up-db       - Start PostgreSQL"
	@echo "  make down        - Stop containers"
	@echo "  make logs        - Xem logs"
	@echo ""
	@echo "🗄️  DATABASE:"
	@echo "  make db-migrate           - Chạy migrations"
	@echo "  make db-makemigration msg='...' - Tạo migration mới"
	@echo "  make db-downgrade         - Rollback 1 bước"
	@echo "  make db-history           - Xem lịch sử migrations"
	@echo "  make db-shell             - Vào psql shell"
	@echo "  make db-reset             - Reset toàn bộ database"
	@echo ""
	@echo "🧹 CLEANUP:"
	@echo "  make clean       - Xóa containers, volumes, cache"
