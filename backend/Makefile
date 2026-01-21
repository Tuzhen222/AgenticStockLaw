.PHONY: install install-dev sync run dev test lint format clean migrate upgrade downgrade

# Package Management (uv)
install:
	uv sync

install-dev:
	uv sync --all-extras

sync:
	uv sync

add:
	uv add $(pkg)

add-dev:
	uv add --dev $(pkg)

remove:
	uv remove $(pkg)

# Development Server
run:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Testing
test:
	uv run pytest

test-cov:
	uv run pytest --cov=app --cov-report=html

# Linting & Formatting
lint:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

format:
	uv run ruff format .

format-check:
	uv run ruff format . --check

type-check:
	uv run mypy app

# Database Migrations (Alembic)
migrate:
	uv run alembic revision --autogenerate -m "$(msg)"

upgrade:
	uv run alembic upgrade head

downgrade:
	uv run alembic downgrade -1

migrate-history:
	uv run alembic history

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

# Help
help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies using uv"
	@echo "  install-dev  - Install with dev dependencies"
	@echo "  sync         - Sync dependencies"
	@echo "  add pkg=X    - Add a package"
	@echo "  add-dev pkg=X- Add a dev package"
	@echo "  run          - Run production server"
	@echo "  dev          - Run development server with reload"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  lint         - Run linter"
	@echo "  lint-fix     - Run linter with auto-fix"
	@echo "  format       - Format code"
	@echo "  type-check   - Run type checking"
	@echo "  migrate msg=X- Create new migration"
	@echo "  upgrade      - Apply migrations"
	@echo "  downgrade    - Rollback last migration"
	@echo "  clean        - Remove cache files"
