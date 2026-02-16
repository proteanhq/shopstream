.PHONY: help install test test-unit test-integration test-bdd test-cov lint format typecheck clean run shell server migrate

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
# ──────────────────────────────────────────────
engine: ## Start all domain engines
	PROTEAN_ENV=production poetry run python src/server.py

engine-identity: ## Start Identity domain engine
	PROTEAN_ENV=production poetry run python src/server.py --domain identity

engine-catalogue: ## Start Catalogue domain engine
	PROTEAN_ENV=production poetry run python src/server.py --domain catalogue

# ──────────────────────────────────────────────
# Monitoring
# ──────────────────────────────────────────────
monitor: ## Start monitoring dashboard (port 9000)
	poetry run uvicorn src.monitor:app --host 0.0.0.0 --port 9000

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
setup-db: ## Create database schemas for all domains
	poetry run python src/manage.py setup-db

drop-db: ## Drop database schemas for all domains
	poetry run python src/manage.py drop-db

# Protean Commands
shell: ## Start Protean shell
	poetry run protean shell

generate-docker: ## Generate docker-compose file for infrastructure
	poetry run protean generate docker

# Docker
docker-up: ## Start Docker services
	docker-compose up -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-clean: ## Clean Docker volumes
	docker-compose down -v

docker-build: ## Build application Docker image
	docker build -t shopstream:latest .

docker-build-dev: ## Build development Docker image
	docker build -f Dockerfile.dev -t shopstream:dev .

docker-run: ## Run application in Docker
	docker-compose up app

docker-run-detached: ## Run application in Docker (detached)
	docker-compose up -d app

docker-shell: ## Open shell in application container
	docker-compose run --rm app /bin/bash

docker-exec: ## Execute command in running container
	docker-compose exec app $(cmd)

docker-ps: ## List running containers
	docker-compose ps

docker-restart: ## Restart all services
	docker-compose restart

docker-rebuild: ## Rebuild and restart all services
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

docker-prod: ## Run production stack
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

docker-prod-logs: ## View production logs
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

docker-prod-down: ## Stop production stack
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Development
dev: docker-up setup-db ## Start development environment (Docker services + database setup)

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
