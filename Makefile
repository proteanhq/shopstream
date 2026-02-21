.PHONY: help install test lint format typecheck clean shell dev docker-up docker-down docker-dev api engine-identity engine-catalogue engine-ordering engine-inventory engine-payments engine-fulfillment loadtest loadtest-mixed loadtest-stress loadtest-headless loadtest-spike loadtest-stack loadtest-stack-scaled loadtest-install loadtest-clean loadtest-cross-domain loadtest-race loadtest-flash-sale loadtest-cross-flood loadtest-priority loadtest-priority-headless loadtest-backfill-drain loadtest-starvation loadtest-baseline loadtest-fulfillment

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
	poetry run pytest tests/identity/domain/ tests/catalogue/domain/ tests/ordering/domain/ tests/inventory/domain/ tests/payments/domain/ tests/fulfillment/domain/

test-application: ## Run application layer tests across all domains
	poetry run pytest tests/identity/application/ tests/catalogue/application/ tests/ordering/application/ tests/inventory/application/ tests/payments/application/ tests/fulfillment/application/

test-integration: ## Run integration tests across all domains
	poetry run pytest tests/identity/integration/ tests/catalogue/integration/ tests/ordering/integration/ tests/inventory/integration/ tests/payments/integration/ tests/fulfillment/integration/ tests/integration/

test-fast: ## Run fast tests across all domains (domain + application)
	poetry run pytest tests/identity/domain/ tests/identity/application/ tests/catalogue/domain/ tests/catalogue/application/ tests/ordering/domain/ tests/ordering/application/ tests/inventory/domain/ tests/inventory/application/ tests/payments/domain/ tests/payments/application/ tests/fulfillment/domain/ tests/fulfillment/application/ -m "not slow"

# ──────────────────────────────────────────────
# Memory-mode testing (no Docker/infrastructure needed)
# Uses PROTEAN_ENV=memory → in-memory DB, inline broker, memory event store
# ──────────────────────────────────────────────
test-memory: ## Run all tests with in-memory adapters (no Docker needed)
	poetry run pytest --protean-env memory

test-memory-domain: ## Run domain tests with in-memory adapters
	poetry run pytest tests/identity/domain/ tests/catalogue/domain/ tests/ordering/domain/ tests/inventory/domain/ tests/payments/domain/ tests/fulfillment/domain/ --protean-env memory

test-memory-application: ## Run application tests with in-memory adapters
	poetry run pytest tests/identity/application/ tests/catalogue/application/ tests/ordering/application/ tests/inventory/application/ tests/payments/application/ tests/fulfillment/application/ --protean-env memory

test-memory-integration: ## Run integration tests with in-memory adapters
	poetry run pytest tests/identity/integration/ tests/catalogue/integration/ tests/ordering/integration/ tests/inventory/integration/ tests/payments/integration/ tests/fulfillment/integration/ tests/integration/ --protean-env memory

test-memory-fast: ## Run fast memory tests (domain + application, excludes slow)
	poetry run pytest tests/identity/domain/ tests/identity/application/ tests/catalogue/domain/ tests/catalogue/application/ tests/ordering/domain/ tests/ordering/application/ tests/inventory/domain/ tests/inventory/application/ tests/payments/domain/ tests/payments/application/ tests/fulfillment/domain/ tests/fulfillment/application/ -m "not slow" --protean-env memory

test-memory-cov: ## Run all memory tests with coverage report
	poetry run pytest --protean-env memory --cov=identity --cov=catalogue --cov=ordering --cov=inventory --cov=payments --cov=fulfillment --cov-report=term-missing --cov-report=html --cov-report=xml

test-cov: ## Run all tests with combined coverage report
	poetry run pytest --cov=identity --cov=catalogue --cov=ordering --cov=inventory --cov=payments --cov=fulfillment --cov-report=term-missing --cov-report=html --cov-report=xml

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
# Ordering domain testing
# ──────────────────────────────────────────────
test-ordering: ## Run all ordering tests
	poetry run pytest tests/ordering/

test-ordering-domain: ## Run ordering domain layer tests
	poetry run pytest tests/ordering/domain/ --cov=ordering --cov-report=term-missing

test-ordering-application: ## Run ordering application layer tests
	poetry run pytest tests/ordering/application/ --cov=ordering --cov-report=term-missing

test-ordering-integration: ## Run ordering integration tests
	poetry run pytest tests/ordering/integration/ --cov=ordering --cov-report=term-missing

test-ordering-cov: ## Run all ordering tests with coverage report
	poetry run pytest tests/ordering/ --cov=ordering --cov-report=term-missing --cov-report=html:htmlcov/ordering

# ──────────────────────────────────────────────
# Inventory domain testing
# ──────────────────────────────────────────────
test-inventory: ## Run all inventory tests
	poetry run pytest tests/inventory/

test-inventory-domain: ## Run inventory domain layer tests
	poetry run pytest tests/inventory/domain/ --cov=inventory --cov-report=term-missing

test-inventory-application: ## Run inventory application layer tests
	poetry run pytest tests/inventory/application/ --cov=inventory --cov-report=term-missing

test-inventory-integration: ## Run inventory integration tests
	poetry run pytest tests/inventory/integration/ --cov=inventory --cov-report=term-missing

test-inventory-cov: ## Run all inventory tests with coverage report
	poetry run pytest tests/inventory/ --cov=inventory --cov-report=term-missing --cov-report=html:htmlcov/inventory

# ──────────────────────────────────────────────
# Payments domain testing
# ──────────────────────────────────────────────
test-payments: ## Run all payments tests
	poetry run pytest tests/payments/

test-payments-domain: ## Run payments domain layer tests
	poetry run pytest tests/payments/domain/ --cov=payments --cov-report=term-missing

test-payments-application: ## Run payments application layer tests
	poetry run pytest tests/payments/application/ --cov=payments --cov-report=term-missing

test-payments-integration: ## Run payments integration tests
	poetry run pytest tests/payments/integration/ --cov=payments --cov-report=term-missing

test-payments-cov: ## Run all payments tests with coverage report
	poetry run pytest tests/payments/ --cov=payments --cov-report=term-missing --cov-report=html:htmlcov/payments

# ──────────────────────────────────────────────
# Fulfillment domain testing
# ──────────────────────────────────────────────
test-fulfillment: ## Run all fulfillment tests
	poetry run pytest tests/fulfillment/

test-fulfillment-domain: ## Run fulfillment domain layer tests
	poetry run pytest tests/fulfillment/domain/ --cov=fulfillment --cov-report=term-missing

test-fulfillment-application: ## Run fulfillment application layer tests
	poetry run pytest tests/fulfillment/application/ --cov=fulfillment --cov-report=term-missing

test-fulfillment-integration: ## Run fulfillment integration tests
	poetry run pytest tests/fulfillment/integration/ --cov=fulfillment --cov-report=term-missing

test-fulfillment-cov: ## Run all fulfillment tests with coverage report
	poetry run pytest tests/fulfillment/ --cov=fulfillment --cov-report=term-missing --cov-report=html:htmlcov/fulfillment

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

engine-ordering: ## Start Ordering domain engine
	poetry run protean server --domain ordering.domain

engine-inventory: ## Start Inventory domain engine
	poetry run protean server --domain inventory.domain

engine-payments: ## Start Payments domain engine
	poetry run protean server --domain payments.domain

engine-fulfillment: ## Start Fulfillment domain engine
	poetry run protean server --domain fulfillment.domain

engine-identity-scaled: ## Start Identity engine with 4 workers
	poetry run protean server --domain identity.domain --workers 4

engine-catalogue-scaled: ## Start Catalogue engine with 4 workers
	poetry run protean server --domain catalogue.domain --workers 4

engine-ordering-scaled: ## Start Ordering engine with 4 workers
	poetry run protean server --domain ordering.domain --workers 4

engine-inventory-scaled: ## Start Inventory engine with 4 workers
	poetry run protean server --domain inventory.domain --workers 4

engine-payments-scaled: ## Start Payments engine with 4 workers
	poetry run protean server --domain payments.domain --workers 4

engine-fulfillment-scaled: ## Start Fulfillment engine with 4 workers
	poetry run protean server --domain fulfillment.domain --workers 4

# ──────────────────────────────────────────────
# Docker-based Engine Workers
# ──────────────────────────────────────────────
engine-docker: ## Start all engines in Docker (1 worker each)
	docker compose up engine-identity engine-catalogue engine-ordering engine-inventory engine-payments engine-fulfillment

engine-docker-scaled: ## Start scaled engines in Docker (3 identity, 2 catalogue, 2 ordering, 2 inventory, 2 payments, 2 fulfillment)
	docker compose up --scale engine-identity=3 --scale engine-catalogue=2 --scale engine-ordering=2 --scale engine-inventory=2 --scale engine-payments=2 --scale engine-fulfillment=2

# ──────────────────────────────────────────────
# Observability
# ──────────────────────────────────────────────
observatory: ## Start Observatory dashboard (port 9000, live message flow + Prometheus metrics)
	poetry run protean observatory --domain identity.domain --domain catalogue.domain --domain ordering.domain --domain inventory.domain --domain payments.domain --domain fulfillment.domain --title "ShopStream Observatory"

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
setup-db: ## Create database schemas for all domains
	poetry run protean db setup --domain identity.domain
	poetry run protean db setup --domain catalogue.domain
	poetry run protean db setup --domain ordering.domain
	poetry run protean db setup --domain inventory.domain
	poetry run protean db setup --domain payments.domain
	poetry run protean db setup --domain fulfillment.domain

drop-db: ## Drop database schemas for all domains
	poetry run protean db drop --domain identity.domain --yes
	poetry run protean db drop --domain catalogue.domain --yes
	poetry run protean db drop --domain ordering.domain --yes
	poetry run protean db drop --domain inventory.domain --yes
	poetry run protean db drop --domain payments.domain --yes
	poetry run protean db drop --domain fulfillment.domain --yes

truncate-db: ## Delete all data from all tables (preserves schema)
	poetry run protean db truncate --domain identity.domain --yes
	poetry run protean db truncate --domain catalogue.domain --yes
	poetry run protean db truncate --domain ordering.domain --yes
	poetry run protean db truncate --domain inventory.domain --yes
	poetry run protean db truncate --domain payments.domain --yes
	poetry run protean db truncate --domain fulfillment.domain --yes

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

docker-dev-scaled: ## Full stack in Docker with scaled engines (3 identity, 2 catalogue, 2 ordering)
	docker compose up --scale engine-identity=3 --scale engine-catalogue=2 --scale engine-ordering=2

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

# ──────────────────────────────────────────────
# Load Testing
# ──────────────────────────────────────────────
loadtest-install: ## Install load testing dependencies
	poetry install --with loadtest

loadtest: ## Start Locust web UI for interactive load testing (all scenarios)
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000

loadtest-mixed: ## Run mixed workload scenario (web UI)
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 MixedWorkloadUser

loadtest-stress: ## Run event pipeline stress test (web UI)
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 EventFloodUser

loadtest-headless: ## Run headless load test (50 users, 5/sec spawn, 5 min, CSV + HTML report)
	@mkdir -p results
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		MixedWorkloadUser --headless \
		-u 50 -r 5 -t 300s \
		--csv=results/loadtest --csv-full-history \
		--html=results/loadtest-report.html

loadtest-spike: ## Run spike test (100 users, instant spawn, 2 min)
	@mkdir -p results
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		SpikeUser --headless \
		-u 100 -r 100 -t 120s \
		--csv=results/spike-test --csv-full-history \
		--html=results/spike-report.html

loadtest-cross-domain: ## Run cross-domain workload scenario (web UI)
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 CrossDomainUser

loadtest-race: ## Run race condition scenarios (web UI)
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 RaceConditionUser

loadtest-flash-sale: ## Run flash sale simulation (web UI)
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 FlashSaleUser

loadtest-cross-flood: ## Run cross-domain flood stress test (web UI)
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 CrossDomainFloodUser

loadtest-headless-race: ## Run headless race condition test (30 users, 10/sec spawn, 3 min, reports)
	@mkdir -p results
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		RaceConditionUser --headless \
		-u 30 -r 10 -t 180s \
		--csv=results/race-test --csv-full-history \
		--html=results/race-report.html

loadtest-headless-flash: ## Run headless flash sale test (50 users, instant spawn, 2 min, reports)
	@mkdir -p results
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		FlashSaleUser --headless \
		-u 50 -r 50 -t 120s \
		--csv=results/flash-sale-test --csv-full-history \
		--html=results/flash-sale-report.html

loadtest-stack: ## Start full load test stack (Docker API + engines + Observatory + Locust)
	./scripts/loadtest-stack.sh

loadtest-stack-scaled: ## Start scaled load test stack (3+2+2+2+2 engines across all domains)
	./scripts/loadtest-stack.sh --scaled

loadtest-priority: ## Run migration + production priority lanes scenario (web UI)
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 MigrationWithProductionTrafficUser

loadtest-priority-headless: ## Run headless priority lanes test (30 users, 5/sec spawn, 3 min, reports)
	@mkdir -p results
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		MigrationWithProductionTrafficUser --headless \
		-u 30 -r 5 -t 180s \
		--csv=results/priority-test --csv-full-history \
		--html=results/priority-report.html

loadtest-backfill-drain: ## Run backfill drain rate measurement (headless, 10 users, 3 min)
	@mkdir -p results
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		BackfillDrainRateUser --headless \
		-u 10 -r 10 -t 180s \
		--csv=results/backfill-drain --csv-full-history \
		--html=results/backfill-drain-report.html

loadtest-starvation: ## Run priority starvation test (headless, 50 users, 5 min)
	@mkdir -p results
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		PriorityStarvationTestUser --headless \
		-u 50 -r 10 -t 300s \
		--csv=results/starvation-test --csv-full-history \
		--html=results/starvation-report.html

loadtest-baseline: ## Run priority lanes disabled baseline (headless, 30 users, 3 min)
	@mkdir -p results
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		PriorityLanesDisabledBaseline --headless \
		-u 30 -r 5 -t 180s \
		--csv=results/baseline-test --csv-full-history \
		--html=results/baseline-report.html

loadtest-fulfillment: ## Run fulfillment workflow load test (web UI)
	poetry run locust -f loadtests/locustfile.py --host http://localhost:8000 FulfillmentUser

loadtest-clean: truncate-db ## Clean all data for a fresh load test run

# Documentation
docs: ## Build documentation
	poetry run mkdocs build

docs-serve: ## Serve documentation locally
	poetry run mkdocs serve
