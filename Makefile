.PHONY: help install test lint format typecheck clean shell dev docker-up docker-down docker-dev api engine-identity engine-catalogue

# Default target
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-30s %s\n", $$1, $$2}'

# Installation and Setup
install: ## Install dependencies using Poetry
	poetry install --with dev,test,docs,types

install-pre-commit: ## Install pre-commit hooks
	poetry run pre-commit install

# ──────────────────────────────────────────────
# Application-level testing (all domains)
# ──────────────────────────────────────────────
test: ## Run all tests across all domains
	poetry run pytest

test-domain: ## Run domain layer tests across all domains
	poetry run pytest tests/identity/domain/ tests/catalogue/domain/

test-application: ## Run application layer tests across all domains
	poetry run pytest tests/identity/application/ tests/catalogue/application/

test-integration: ## Run integration tests across all domains
	poetry run pytest tests/identity/integration/ tests/catalogue/integration/ tests/integration/

test-fast: ## Run fast tests across all domains (domain + application)
	poetry run pytest tests/identity/domain/ tests/identity/application/ tests/catalogue/domain/ tests/catalogue/application/ -m "not slow"

test-cov: ## Run all tests with combined coverage report
	poetry run pytest --cov=identity --cov=catalogue --cov-report=term-missing --cov-report=html --cov-report=xml

# ──────────────────────────────────────────────
# Identity domain testing
# ──────────────────────────────────────────────
test-identity: ## Run all identity tests
	poetry run pytest tests/identity/

test-identity-domain: ## Run identity domain layer tests
	poetry run pytest tests/identity/domain/ --cov=identity --cov-report=term-missing

test-identity-application: ## Run identity application layer tests
	poetry run pytest tests/identity/application/ --cov=identity --cov-report=term-missing

test-identity-integration: ## Run identity integration tests
	poetry run pytest tests/identity/integration/ --cov=identity --cov-report=term-missing

test-identity-cov: ## Run all identity tests with coverage report
	poetry run pytest tests/identity/ --cov=identity --cov-report=term-missing --cov-report=html:htmlcov/identity

# ──────────────────────────────────────────────
# Catalogue domain testing
# ──────────────────────────────────────────────
test-catalogue: ## Run all catalogue tests
	poetry run pytest tests/catalogue/

test-catalogue-domain: ## Run catalogue domain layer tests
	poetry run pytest tests/catalogue/domain/ --cov=catalogue --cov-report=term-missing

test-catalogue-application: ## Run catalogue application layer tests
	poetry run pytest tests/catalogue/application/ --cov=catalogue --cov-report=term-missing

test-catalogue-integration: ## Run catalogue integration tests
	poetry run pytest tests/catalogue/integration/ --cov=catalogue --cov-report=term-missing

test-catalogue-cov: ## Run all catalogue tests with coverage report
	poetry run pytest tests/catalogue/ --cov=catalogue --cov-report=term-missing --cov-report=html:htmlcov/catalogue

# ──────────────────────────────────────────────
# Test utilities
# ──────────────────────────────────────────────
test-watch: ## Run tests in watch mode
	poetry run pytest-watch

# Code Quality
lint: ## Run linting with ruff
	poetry run ruff check src/ tests/

format: ## Format code with ruff
	poetry run ruff format src/ tests/

typecheck: ## Run type checking with mypy
	poetry run mypy src/

check: lint typecheck test ## Run all checks (lint, typecheck, test)

pre-commit: ## Run pre-commit hooks on all files
	poetry run pre-commit run --all-files

# ──────────────────────────────────────────────
# Web Server
# ──────────────────────────────────────────────
api: ## Start FastAPI web server (Swagger UI at http://localhost:8000/docs)
	poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload --app-dir src

# ──────────────────────────────────────────────
# Engine Workers (async event processing)
# Uses Protean CLI: protean server --domain <path> [--workers N]
# ──────────────────────────────────────────────
engine-identity: ## Start Identity domain engine
	poetry run protean server --domain identity.domain

engine-catalogue: ## Start Catalogue domain engine
	poetry run protean server --domain catalogue.domain

engine-identity-scaled: ## Start Identity engine with 4 workers
	poetry run protean server --domain identity.domain --workers 4

engine-catalogue-scaled: ## Start Catalogue engine with 4 workers
	poetry run protean server --domain catalogue.domain --workers 4

# ──────────────────────────────────────────────
# Docker-based Engine Workers
# ──────────────────────────────────────────────
engine-docker: ## Start all engines in Docker (1 worker each)
	docker compose up engine-identity engine-catalogue

engine-docker-scaled: ## Start scaled engines in Docker (3 identity, 2 catalogue)
	docker compose up --scale engine-identity=3 --scale engine-catalogue=2

# ──────────────────────────────────────────────
# Observability
# ──────────────────────────────────────────────
observatory: ## Start Observatory dashboard (port 9000, live message flow + Prometheus metrics)
	poetry run uvicorn src.observatory:app --host 0.0.0.0 --port 9000 --timeout-graceful-shutdown 3

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
setup-db: ## Create database schemas for all domains
	poetry run protean db setup --domain identity.domain
	poetry run protean db setup --domain catalogue.domain

drop-db: ## Drop database schemas for all domains
	poetry run protean db drop --domain identity.domain --yes
	poetry run protean db drop --domain catalogue.domain --yes

truncate-db: ## Delete all data from all tables (preserves schema)
	poetry run protean db truncate --domain identity.domain --yes
	poetry run protean db truncate --domain catalogue.domain --yes

# Protean Commands
shell: ## Start Protean shell
	poetry run protean shell

# ──────────────────────────────────────────────
# Docker
# ──────────────────────────────────────────────
docker-up: ## Start infrastructure services (Postgres, Redis, Message DB)
	docker compose up -d postgres message-db redis

docker-dev: ## Start full stack in Docker (infra + api + engines)
	docker compose up

docker-down: ## Stop all Docker services
	docker compose down

docker-logs: ## View Docker service logs
	docker compose logs -f

docker-clean: ## Stop all services and remove volumes
	docker compose down -v

docker-ps: ## List running containers
	docker compose ps

docker-rebuild: ## Rebuild dev image and restart (after dependency changes)
	docker compose build --no-cache
	docker compose up

# ──────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────
dev: docker-up ## Start dev environment (infrastructure services)

# Cleanup
clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true

# Documentation
docs: ## Build documentation
	poetry run mkdocs build

docs-serve: ## Serve documentation locally
	poetry run mkdocs serve
