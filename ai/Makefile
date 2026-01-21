.PHONY: help build up down logs restart dev test clean up-gpu up-cpu dev-gpu dev-cpu dev-down

# Default target
help:
	@echo "A2A Agent System - Vietnam Stock Law"
	@echo ""
	@echo "Production (docker-compose.yml):"
	@echo "  make build        - Build Docker images"
	@echo "  make up-gpu       - Start with GPU Triton"
	@echo "  make up-cpu       - Start with CPU-only Triton"
	@echo "  make up           - Start services (no Triton)"
	@echo "  make down         - Stop all Docker services"
	@echo "  make logs         - View all service logs"
	@echo ""
	@echo "Development with hot reload (docker-compose.dev.yml):"
	@echo "  make dev-gpu      - Start dev with GPU Triton"
	@echo "  make dev-cpu      - Start dev with CPU Triton"
	@echo "  make dev          - Start dev (no Triton)"
	@echo "  make dev-down     - Stop dev services"
	@echo "  make dev-logs     - View dev logs"
	@echo ""
	@echo "Local (no Docker):"
	@echo "  make local        - Run all services locally"
	@echo "  make gateway      - Run AI Gateway only"
	@echo "  make orchestrator - Run orchestrator only"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Remove Docker images"
	@echo "  make orchestrator - Run orchestrator only"
	@echo "  make knowledge    - Run knowledge agent only"
	@echo "  make validation   - Run validation agent only"
	@echo "  make retrieve     - Run retrieve MCP only"
	@echo "  make rerank       - Run rerank MCP only"

# Development - run locally without Docker
local:
	python -m ai.main

# Production Docker commands
build:
	docker-compose -f docker-compose.yml build

up-gpu:
	docker-compose -f docker-compose.yml --profile gpu up -d

up-cpu:
	docker-compose -f docker-compose.yml --profile cpu up -d

up:
	docker-compose -f docker-compose.yml up -d

down:
	docker-compose -f docker-compose.yml --profile gpu --profile cpu down

logs:
	docker-compose -f docker-compose.yml logs -f

restart:
	docker-compose -f docker-compose.yml restart

# Development Docker commands (with hot reload)
dev-gpu:
	docker-compose -f docker-compose.dev.yml --profile gpu up -d

dev-cpu:
	docker-compose -f docker-compose.dev.yml --profile cpu up -d

dev:
	docker-compose -f docker-compose.dev.yml up -d

dev-down:
	docker-compose -f docker-compose.dev.yml --profile gpu --profile cpu down

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

dev-build:
	docker-compose -f docker-compose.dev.yml build

# Individual services (local)
gateway:
	python -m ai.main gateway

orchestrator:
	python -m ai.main orchestrator

knowledge:
	python -m ai.main knowledge

validation:
	python -m ai.main validation

regulatory_update:
	python -m ai.main regulatory_update

retrieve:
	python -m ai.main retrieve

rerank:
	python -m ai.main rerank

# Testing
test:
	pytest tests/ -v

# Cleanup
clean:
	docker-compose -f docker-compose.yml --profile gpu --profile cpu down --rmi all --volumes
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
