.PHONY: help install test lint format typecheck clean shell dev docker-up docker-down docker-dev api engine-identity engine-catalogue engine-ordering engine-inventory engine-payments engine-fulfillment engine-reviews engine-notifications engine-loyalty domain-check domain-check-identity domain-check-catalogue domain-check-ordering domain-check-inventory domain-check-payments domain-check-fulfillment domain-check-reviews domain-check-notifications domain-check-loyalty ir ir-summary schemas docs-generate docs-catalog docs-check doctest ir-check ir-diff loadtest loadtest-mixed loadtest-stress loadtest-headless loadtest-spike loadtest-stack loadtest-stack-scaled loadtest-install loadtest-clean loadtest-cross-domain loadtest-race loadtest-flash-sale loadtest-cross-flood loadtest-priority loadtest-priority-headless loadtest-backfill-drain loadtest-starvation loadtest-baseline loadtest-fulfillment loadtest-loyalty loadtest-loyalty-events verify-loyalty verify-timeline verify-timeline-skip-seed

# Default target
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-30s %s\n", $$1, $$2}'

# Installation and Setup
install: ## Install dependencies
	uv sync

install-pre-commit: ## Install pre-commit hooks
	uv run pre-commit install

# ──────────────────────────────────────────────
# Application-level testing (all domains)
# ──────────────────────────────────────────────
test: ## Run all tests across all domains
	uv run pytest

test-domain: ## Run domain layer tests across all domains
	uv run pytest tests/identity/domain/ tests/catalogue/domain/ tests/ordering/domain/ tests/inventory/domain/ tests/payments/domain/ tests/fulfillment/domain/ tests/reviews/domain/ tests/notifications/domain/ tests/loyalty/domain/

test-application: ## Run application layer tests across all domains
	uv run pytest tests/identity/application/ tests/catalogue/application/ tests/ordering/application/ tests/inventory/application/ tests/payments/application/ tests/fulfillment/application/ tests/reviews/application/ tests/notifications/application/ tests/loyalty/application/

test-integration: ## Run integration tests across all domains
	uv run pytest tests/identity/integration/ tests/catalogue/integration/ tests/ordering/integration/ tests/inventory/integration/ tests/payments/integration/ tests/fulfillment/integration/ tests/reviews/integration/ tests/notifications/integration/ tests/integration/

test-fast: ## Run fast tests across all domains (domain + application)
	uv run pytest tests/identity/domain/ tests/identity/application/ tests/catalogue/domain/ tests/catalogue/application/ tests/ordering/domain/ tests/ordering/application/ tests/inventory/domain/ tests/inventory/application/ tests/payments/domain/ tests/payments/application/ tests/fulfillment/domain/ tests/fulfillment/application/ tests/reviews/domain/ tests/reviews/application/ tests/notifications/domain/ tests/notifications/application/ -m "not slow"

# ──────────────────────────────────────────────
# Memory-mode testing (no Docker/infrastructure needed)
# Uses PROTEAN_ENV=memory → in-memory DB, inline broker, memory event store
# ──────────────────────────────────────────────
test-memory: ## Run all tests with in-memory adapters (no Docker needed)
	uv run pytest --protean-env memory

test-memory-domain: ## Run domain tests with in-memory adapters
	uv run pytest tests/identity/domain/ tests/catalogue/domain/ tests/ordering/domain/ tests/inventory/domain/ tests/payments/domain/ tests/fulfillment/domain/ tests/reviews/domain/ tests/notifications/domain/ tests/loyalty/domain/ --protean-env memory

test-memory-application: ## Run application tests with in-memory adapters
	uv run pytest tests/identity/application/ tests/catalogue/application/ tests/ordering/application/ tests/inventory/application/ tests/payments/application/ tests/fulfillment/application/ tests/reviews/application/ tests/notifications/application/ tests/loyalty/application/ --protean-env memory

test-memory-integration: ## Run integration tests with in-memory adapters
	uv run pytest tests/identity/integration/ tests/catalogue/integration/ tests/ordering/integration/ tests/inventory/integration/ tests/payments/integration/ tests/fulfillment/integration/ tests/reviews/integration/ tests/notifications/integration/ tests/integration/ --protean-env memory

test-memory-fast: ## Run fast memory tests (domain + application, excludes slow)
	uv run pytest tests/identity/domain/ tests/identity/application/ tests/catalogue/domain/ tests/catalogue/application/ tests/ordering/domain/ tests/ordering/application/ tests/inventory/domain/ tests/inventory/application/ tests/payments/domain/ tests/payments/application/ tests/fulfillment/domain/ tests/fulfillment/application/ tests/reviews/domain/ tests/reviews/application/ tests/notifications/domain/ tests/notifications/application/ tests/loyalty/domain/ tests/loyalty/application/ -m "not slow" --protean-env memory

test-memory-cov: ## Run all memory tests with coverage report
	uv run pytest --protean-env memory --cov=identity --cov=catalogue --cov=ordering --cov=inventory --cov=payments --cov=fulfillment --cov=reviews --cov=notifications --cov-report=term-missing --cov-report=html --cov-report=xml

test-cov: ## Run all tests with combined coverage report
	uv run pytest --cov=identity --cov=catalogue --cov=ordering --cov=inventory --cov=payments --cov=fulfillment --cov=reviews --cov=notifications --cov-report=term-missing --cov-report=html --cov-report=xml

# ──────────────────────────────────────────────
# Identity domain testing
# ──────────────────────────────────────────────
test-identity: ## Run all identity tests
	uv run pytest tests/identity/

test-identity-domain: ## Run identity domain layer tests
	uv run pytest tests/identity/domain/ --cov=identity --cov-report=term-missing

test-identity-application: ## Run identity application layer tests
	uv run pytest tests/identity/application/ --cov=identity --cov-report=term-missing

test-identity-integration: ## Run identity integration tests
	uv run pytest tests/identity/integration/ --cov=identity --cov-report=term-missing

test-identity-cov: ## Run all identity tests with coverage report
	uv run pytest tests/identity/ --cov=identity --cov-report=term-missing --cov-report=html:htmlcov/identity

# ──────────────────────────────────────────────
# Catalogue domain testing
# ──────────────────────────────────────────────
test-catalogue: ## Run all catalogue tests
	uv run pytest tests/catalogue/

test-catalogue-domain: ## Run catalogue domain layer tests
	uv run pytest tests/catalogue/domain/ --cov=catalogue --cov-report=term-missing

test-catalogue-application: ## Run catalogue application layer tests
	uv run pytest tests/catalogue/application/ --cov=catalogue --cov-report=term-missing

test-catalogue-integration: ## Run catalogue integration tests
	uv run pytest tests/catalogue/integration/ --cov=catalogue --cov-report=term-missing

test-catalogue-cov: ## Run all catalogue tests with coverage report
	uv run pytest tests/catalogue/ --cov=catalogue --cov-report=term-missing --cov-report=html:htmlcov/catalogue

# ──────────────────────────────────────────────
# Ordering domain testing
# ──────────────────────────────────────────────
test-ordering: ## Run all ordering tests
	uv run pytest tests/ordering/

test-ordering-domain: ## Run ordering domain layer tests
	uv run pytest tests/ordering/domain/ --cov=ordering --cov-report=term-missing

test-ordering-application: ## Run ordering application layer tests
	uv run pytest tests/ordering/application/ --cov=ordering --cov-report=term-missing

test-ordering-integration: ## Run ordering integration tests
	uv run pytest tests/ordering/integration/ --cov=ordering --cov-report=term-missing

test-ordering-cov: ## Run all ordering tests with coverage report
	uv run pytest tests/ordering/ --cov=ordering --cov-report=term-missing --cov-report=html:htmlcov/ordering

# ──────────────────────────────────────────────
# Inventory domain testing
# ──────────────────────────────────────────────
test-inventory: ## Run all inventory tests
	uv run pytest tests/inventory/

test-inventory-domain: ## Run inventory domain layer tests
	uv run pytest tests/inventory/domain/ --cov=inventory --cov-report=term-missing

test-inventory-application: ## Run inventory application layer tests
	uv run pytest tests/inventory/application/ --cov=inventory --cov-report=term-missing

test-inventory-integration: ## Run inventory integration tests
	uv run pytest tests/inventory/integration/ --cov=inventory --cov-report=term-missing

test-inventory-cov: ## Run all inventory tests with coverage report
	uv run pytest tests/inventory/ --cov=inventory --cov-report=term-missing --cov-report=html:htmlcov/inventory

# ──────────────────────────────────────────────
# Payments domain testing
# ──────────────────────────────────────────────
test-payments: ## Run all payments tests
	uv run pytest tests/payments/

test-payments-domain: ## Run payments domain layer tests
	uv run pytest tests/payments/domain/ --cov=payments --cov-report=term-missing

test-payments-application: ## Run payments application layer tests
	uv run pytest tests/payments/application/ --cov=payments --cov-report=term-missing

test-payments-integration: ## Run payments integration tests
	uv run pytest tests/payments/integration/ --cov=payments --cov-report=term-missing

test-payments-cov: ## Run all payments tests with coverage report
	uv run pytest tests/payments/ --cov=payments --cov-report=term-missing --cov-report=html:htmlcov/payments

# ──────────────────────────────────────────────
# Fulfillment domain testing
# ──────────────────────────────────────────────
test-fulfillment: ## Run all fulfillment tests
	uv run pytest tests/fulfillment/

test-fulfillment-domain: ## Run fulfillment domain layer tests
	uv run pytest tests/fulfillment/domain/ --cov=fulfillment --cov-report=term-missing

test-fulfillment-application: ## Run fulfillment application layer tests
	uv run pytest tests/fulfillment/application/ --cov=fulfillment --cov-report=term-missing

test-fulfillment-integration: ## Run fulfillment integration tests
	uv run pytest tests/fulfillment/integration/ --cov=fulfillment --cov-report=term-missing

test-fulfillment-cov: ## Run all fulfillment tests with coverage report
	uv run pytest tests/fulfillment/ --cov=fulfillment --cov-report=term-missing --cov-report=html:htmlcov/fulfillment

# ──────────────────────────────────────────────
# Reviews domain testing
# ──────────────────────────────────────────────
test-reviews: ## Run all reviews tests
	uv run pytest tests/reviews/

test-reviews-domain: ## Run reviews domain layer tests
	uv run pytest tests/reviews/domain/ --cov=reviews --cov-report=term-missing

test-reviews-application: ## Run reviews application layer tests
	uv run pytest tests/reviews/application/ --cov=reviews --cov-report=term-missing

test-reviews-integration: ## Run reviews integration tests
	uv run pytest tests/reviews/integration/ --cov=reviews --cov-report=term-missing

test-reviews-cov: ## Run all reviews tests with coverage report
	uv run pytest tests/reviews/ --cov=reviews --cov-report=term-missing --cov-report=html:htmlcov/reviews

# ──────────────────────────────────────────────
# Notifications domain testing
# ──────────────────────────────────────────────
test-notifications: ## Run all notifications tests
	uv run pytest tests/notifications/

test-notifications-domain: ## Run notifications domain layer tests
	uv run pytest tests/notifications/domain/ --cov=notifications --cov-report=term-missing

test-notifications-application: ## Run notifications application layer tests
	uv run pytest tests/notifications/application/ --cov=notifications --cov-report=term-missing

test-notifications-integration: ## Run notifications integration tests
	uv run pytest tests/notifications/integration/ --cov=notifications --cov-report=term-missing

test-notifications-cov: ## Run all notifications tests with coverage report
	uv run pytest tests/notifications/ --cov=notifications --cov-report=term-missing --cov-report=html:htmlcov/notifications

test-loyalty: ## Run all loyalty tests
	uv run pytest tests/loyalty/

test-loyalty-domain: ## Run loyalty domain layer tests
	uv run pytest tests/loyalty/domain/ --cov=loyalty --cov-report=term-missing

test-loyalty-application: ## Run loyalty application layer tests
	uv run pytest tests/loyalty/application/ --cov=loyalty --cov-report=term-missing

test-loyalty-cov: ## Run all loyalty tests with coverage report
	uv run pytest tests/loyalty/ --cov=loyalty --cov-report=term-missing --cov-report=html:htmlcov/loyalty

# ──────────────────────────────────────────────
# Test utilities
# ──────────────────────────────────────────────
test-watch: ## Run tests in watch mode
	uv run pytest-watch

# Code Quality
lint: ## Run linting with ruff
	uv run ruff check src/ tests/

check-src-clean: ## Fail if reference code (src/) imports test/verification-only tools
	@bad=$$(grep -rnE '^[[:space:]]*(import|from)[[:space:]]+(pytest|hypothesis|schemathesis|toxiproxy)([[:space:].]|$$)' src/ || true); \
	if [ -n "$$bad" ]; then \
		echo "$$bad"; echo ""; \
		echo "src/ (reference code) must not import test/verification tools — move it to tests/ or verification/."; \
		exit 1; \
	fi; \
	echo "src/ is clean (no test-tool imports)"

format: ## Format code with ruff
	uv run ruff format src/ tests/

typecheck: ## Run type checking with mypy
	uv run mypy src/

check: lint typecheck test ## Run all checks (lint, typecheck, test)

pre-commit: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

# ──────────────────────────────────────────────
# Domain diagnostics (protean check)
# ──────────────────────────────────────────────
domain-check: ## Run protean check on all domains
	@failed=0; \
	for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		PYTHONPATH=src uv run protean check --domain=$$d.domain || \
			if [ $$? -eq 1 ]; then failed=1; fi; \
	done; \
	exit $$failed

domain-check-identity: ## Run protean check on identity domain
	PYTHONPATH=src uv run protean check --domain=identity.domain

domain-check-catalogue: ## Run protean check on catalogue domain
	PYTHONPATH=src uv run protean check --domain=catalogue.domain

domain-check-ordering: ## Run protean check on ordering domain
	PYTHONPATH=src uv run protean check --domain=ordering.domain

domain-check-inventory: ## Run protean check on inventory domain
	PYTHONPATH=src uv run protean check --domain=inventory.domain

domain-check-payments: ## Run protean check on payments domain
	PYTHONPATH=src uv run protean check --domain=payments.domain

domain-check-fulfillment: ## Run protean check on fulfillment domain
	PYTHONPATH=src uv run protean check --domain=fulfillment.domain

domain-check-reviews: ## Run protean check on reviews domain
	PYTHONPATH=src uv run protean check --domain=reviews.domain

domain-check-notifications: ## Run protean check on notifications domain
	PYTHONPATH=src uv run protean check --domain=notifications.domain

domain-check-loyalty: ## Run protean check on loyalty domain
	PYTHONPATH=src uv run protean check --domain=loyalty.domain

# ──────────────────────────────────────────────
# IR & Schema Generation
# ──────────────────────────────────────────────
ir: ## Generate IR (intermediate representation) for all domains
	@# --canonical: sorted keys + no volatile `generated_at`, so committed baselines
	@# diff only on real changes (no key-reorder or timestamp churn between runs/versions).
	@for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		mkdir -p .protean/$$d; \
		PYTHONPATH=src PROTEAN_ENV=memory uv run protean ir show --domain=$$d.domain --canonical > .protean/$$d/ir.json; \
		echo "✓ $$d"; \
	done

ir-summary: ## Show IR summary for all domains
	@for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		PYTHONPATH=src PROTEAN_ENV=memory uv run protean ir show --domain=$$d.domain --format=summary; \
		echo ""; \
	done

schemas: ## Generate JSON Schemas for all domains
	@for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		PYTHONPATH=src uv run protean schema generate --domain=$$d.domain --output=.protean/$$d; \
	done

docs-generate: ## Generate domain documentation (diagrams + event catalog)
	@for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		echo "Generating docs for $$d..."; \
		PYTHONPATH=src uv run protean docs generate --domain=$$d.domain --type=clusters --output=docs/$$d/clusters.md; \
		PYTHONPATH=src uv run protean docs generate --domain=$$d.domain --type=events --output=docs/$$d/event-flows.md; \
		PYTHONPATH=src uv run protean docs generate --domain=$$d.domain --type=handlers --output=docs/$$d/handler-wiring.md; \
		PYTHONPATH=src uv run protean docs generate --domain=$$d.domain --type=catalog --output=docs/$$d/catalog.md; \
	done

docs-catalog: ## Regenerate the event/command catalog docs from the live domains
	@for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		PYTHONPATH=src PROTEAN_ENV=memory uv run protean docs generate --domain=$$d.domain --type=catalog --output=docs/$$d/catalog.md; \
		echo "✓ docs/$$d/catalog.md"; \
	done

docs-check: ## CI gate — fail if any committed catalog.md is stale vs the code
	@# Docs are generated FROM the domain, so they cannot claim a feature the code
	@# lacks. This fails the build if a committed catalog drifts — run 'make docs-catalog'.
	@fail=0; for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		PYTHONPATH=src PROTEAN_ENV=memory uv run protean docs generate --domain=$$d.domain --type=catalog --output=/tmp/catalog_check_$$d.md >/dev/null 2>&1; \
		if ! diff -q docs/$$d/catalog.md /tmp/catalog_check_$$d.md >/dev/null 2>&1; then \
			echo "STALE: docs/$$d/catalog.md — run 'make docs-catalog' and commit"; fail=1; \
		fi; \
	done; \
	if [ $$fail -eq 0 ]; then echo "✓ all catalog docs current"; else exit 1; fi

doctest: ## Run doctests on the value objects (executable examples in docstrings)
	PYTHONPATH=src PROTEAN_ENV=memory uv run pytest --doctest-modules \
		src/catalogue/shared/money.py src/catalogue/shared/sku.py src/reviews/review/review.py -q

ir-check: ## Check staleness of materialized IR for all domains
	@for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		printf "$$d: "; \
		PYTHONPATH=src PROTEAN_ENV=memory uv run protean ir check --domain=$$d.domain --dir=.protean/$$d 2>&1 | head -1; \
	done

ir-diff: ## Diff live IR against saved baselines (.protean/<domain>/ir.json)
	@for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		if [ -f .protean/$$d/ir.json ]; then \
			echo "=== $$d ==="; \
			PYTHONPATH=src PROTEAN_ENV=memory uv run protean ir diff --domain=$$d.domain --dir=.protean/$$d 2>&1 || true; \
			echo ""; \
		else \
			echo "=== $$d === (no baseline, run 'make ir' first)"; \
		fi; \
	done

ir-gate: ## CI gate — fail on a BREAKING IR change vs the committed baseline (prints full detail)
	@echo "--- protean build under test ---"; \
	PYTHONPATH=src uv run python -c 'import importlib.metadata as m; d=m.distribution("protean"); print(d.version, (d.read_text("direct_url.json") or "").strip())'
	@fail=0; \
	for d in identity catalogue ordering inventory payments fulfillment reviews notifications loyalty; do \
		out=$$(PYTHONPATH=src PROTEAN_ENV=memory uv run protean --log-level ERROR ir diff --domain=$$d.domain --dir=.protean/$$d 2>&1); \
		code=$$?; \
		if [ $$code -eq 0 ]; then echo "ok: $$d"; \
		elif [ $$code -eq 2 ]; then echo "note: non-breaking IR change in $$d (baseline behind; run 'make ir')"; \
		elif [ $$code -eq 1 ]; then echo ""; echo "=== BREAKING IR change in $$d (exit 1) ==="; echo "$$out"; echo "=== end $$d ==="; fail=1; \
		else echo ""; echo "=== ir diff ERROR for $$d (exit $$code) ==="; echo "$$out"; echo "=== end $$d ==="; fail=1; fi; \
	done; \
	if [ $$fail -ne 0 ]; then echo ""; echo "IR gate FAILED (details above). If a change is intended, run 'make ir' and commit the reviewed baseline."; exit 1; fi; \
	echo ""; echo "IR gate passed (no breaking changes)"

# ──────────────────────────────────────────────
# Web Server
# ──────────────────────────────────────────────
api: ## Start FastAPI web server (Swagger UI at http://localhost:8000/docs)
	uv run uvicorn app:app --host 0.0.0.0 --port 8000 --reload --app-dir src

# ──────────────────────────────────────────────
# Engine Workers (async event processing)
# Uses Protean CLI: protean server --domain <path> [--workers N]
# ──────────────────────────────────────────────
engine-identity: ## Start Identity domain engine
	uv run protean server --domain identity.domain

engine-catalogue: ## Start Catalogue domain engine
	uv run protean server --domain catalogue.domain

engine-ordering: ## Start Ordering domain engine
	uv run protean server --domain ordering.domain

engine-inventory: ## Start Inventory domain engine
	uv run protean server --domain inventory.domain

engine-payments: ## Start Payments domain engine
	uv run protean server --domain payments.domain

engine-fulfillment: ## Start Fulfillment domain engine
	uv run protean server --domain fulfillment.domain

engine-reviews: ## Start Reviews domain engine
	uv run protean server --domain reviews.domain

engine-notifications: ## Start Notifications domain engine
	uv run protean server --domain notifications.domain

engine-loyalty: ## Start Loyalty domain engine
	uv run protean server --domain loyalty.domain

engine-identity-scaled: ## Start Identity engine with 4 workers
	uv run protean server --domain identity.domain --workers 4

engine-catalogue-scaled: ## Start Catalogue engine with 4 workers
	uv run protean server --domain catalogue.domain --workers 4

engine-ordering-scaled: ## Start Ordering engine with 4 workers
	uv run protean server --domain ordering.domain --workers 4

engine-inventory-scaled: ## Start Inventory engine with 4 workers
	uv run protean server --domain inventory.domain --workers 4

engine-payments-scaled: ## Start Payments engine with 4 workers
	uv run protean server --domain payments.domain --workers 4

engine-fulfillment-scaled: ## Start Fulfillment engine with 4 workers
	uv run protean server --domain fulfillment.domain --workers 4

# ──────────────────────────────────────────────
# Docker-based Engine Workers
# ──────────────────────────────────────────────
engine-docker: ## Start all engines in Docker (1 worker each)
	docker compose up engine-identity engine-catalogue engine-ordering engine-inventory engine-payments engine-fulfillment engine-notifications engine-loyalty

engine-docker-scaled: ## Start scaled engines in Docker (3 identity, 2 catalogue, 2 ordering, 2 inventory, 2 payments, 2 fulfillment)
	docker compose up --scale engine-identity=3 --scale engine-catalogue=2 --scale engine-ordering=2 --scale engine-inventory=2 --scale engine-payments=2 --scale engine-fulfillment=2

# ──────────────────────────────────────────────
# Observability
# ──────────────────────────────────────────────
observatory: ## Start Observatory dashboard (port 9000, live message flow + Prometheus metrics)
	uv run protean observatory --domain ordering.domain --domain identity.domain --domain catalogue.domain --domain inventory.domain --domain payments.domain --domain fulfillment.domain --domain reviews.domain --domain notifications.domain --title "ShopStream Observatory"

verify-loyalty: ## Verify Loyalty end-to-end: account/points/transfer/campaign/redemption API checks (requires running stack + engine-loyalty)
	./scripts/verify-loyalty.sh

verify-observatory: ## Verify Observatory Timeline + Causation Graph: seeds data + runs ~66 API checks (requires running stack)
	./scripts/verify-observatory.sh

verify-observatory-skip-seed: ## Verify Observatory without re-seeding data
	./scripts/verify-observatory.sh --skip-seed

verify-domain-visualizer: ## Verify Domain Visualizer (Epic 2.1): IR API, D3 graphs, UI rendering (requires running stack)
	./scripts/verify-domain-visualizer.sh

verify-domain-visualizer-skip-seed: ## Verify Domain Visualizer without re-seeding data
	./scripts/verify-domain-visualizer.sh --skip-seed

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
setup-db: ## Create database schemas for all domains
	uv run protean db setup --domain identity.domain
	uv run protean db setup --domain catalogue.domain
	uv run protean db setup --domain ordering.domain
	uv run protean db setup --domain inventory.domain
	uv run protean db setup --domain payments.domain
	uv run protean db setup --domain fulfillment.domain
	uv run protean db setup --domain reviews.domain
	uv run protean db setup --domain notifications.domain
	uv run protean db setup --domain loyalty.domain

drop-db: ## Drop database schemas for all domains
	uv run protean db drop --domain identity.domain --yes
	uv run protean db drop --domain catalogue.domain --yes
	uv run protean db drop --domain ordering.domain --yes
	uv run protean db drop --domain inventory.domain --yes
	uv run protean db drop --domain payments.domain --yes
	uv run protean db drop --domain fulfillment.domain --yes
	uv run protean db drop --domain reviews.domain --yes
	uv run protean db drop --domain notifications.domain --yes

truncate-db: ## Delete all data from all tables (preserves schema)
	uv run protean db truncate --domain identity.domain --yes
	uv run protean db truncate --domain catalogue.domain --yes
	uv run protean db truncate --domain ordering.domain --yes
	uv run protean db truncate --domain inventory.domain --yes
	uv run protean db truncate --domain payments.domain --yes
	uv run protean db truncate --domain fulfillment.domain --yes
	uv run protean db truncate --domain reviews.domain --yes
	uv run protean db truncate --domain notifications.domain --yes

# Protean Commands
shell: ## Start Protean shell
	uv run protean shell

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
	uv sync --group loadtest

loadtest: ## Start Locust web UI for interactive load testing (all scenarios)
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000

loadtest-mixed: ## Run mixed workload scenario (web UI)
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 MixedWorkloadUser

loadtest-stress: ## Run event pipeline stress test (web UI)
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 EventFloodUser

loadtest-headless: ## Run headless load test (50 users, 5/sec spawn, 5 min, CSV + HTML report)
	@mkdir -p results
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		MixedWorkloadUser --headless \
		-u 50 -r 5 -t 300s \
		--csv=results/loadtest --csv-full-history \
		--html=results/loadtest-report.html

loadtest-spike: ## Run spike test (100 users, instant spawn, 2 min)
	@mkdir -p results
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		SpikeUser --headless \
		-u 100 -r 100 -t 120s \
		--csv=results/spike-test --csv-full-history \
		--html=results/spike-report.html

loadtest-cross-domain: ## Run cross-domain workload scenario (web UI)
	uv run locust -f loadtests/locustfile.py,loadtests/scenarios/cross_domain.py --host http://localhost:8000 CrossDomainUser

loadtest-race: ## Run race condition scenarios (web UI)
	uv run locust -f loadtests/locustfile.py,loadtests/scenarios/cross_domain.py --host http://localhost:8000 RaceConditionUser

loadtest-flash-sale: ## Run flash sale simulation (web UI)
	uv run locust -f loadtests/locustfile.py,loadtests/scenarios/cross_domain.py --host http://localhost:8000 FlashSaleUser

loadtest-cross-flood: ## Run cross-domain flood stress test (web UI)
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 CrossDomainFloodUser

loadtest-headless-race: ## Run headless race condition test (30 users, 10/sec spawn, 3 min, reports)
	@mkdir -p results
	uv run locust -f loadtests/locustfile.py,loadtests/scenarios/cross_domain.py --host http://localhost:8000 \
		RaceConditionUser --headless \
		-u 30 -r 10 -t 180s \
		--csv=results/race-test --csv-full-history \
		--html=results/race-report.html

loadtest-headless-flash: ## Run headless flash sale test (50 users, instant spawn, 2 min, reports)
	@mkdir -p results
	uv run locust -f loadtests/locustfile.py,loadtests/scenarios/cross_domain.py --host http://localhost:8000 \
		FlashSaleUser --headless \
		-u 50 -r 50 -t 120s \
		--csv=results/flash-sale-test --csv-full-history \
		--html=results/flash-sale-report.html

loadtest-stack: ## Start full load test stack (Docker API + engines + Observatory + Locust)
	./scripts/loadtest-stack.sh

loadtest-stack-scaled: ## Start scaled load test stack (3+2+2+2+2 engines across all domains)
	./scripts/loadtest-stack.sh --scaled

loadtest-priority: ## Run migration + production priority lanes scenario (web UI)
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 MigrationWithProductionTrafficUser

loadtest-priority-headless: ## Run headless priority lanes test (30 users, 5/sec spawn, 3 min, reports)
	@mkdir -p results
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		MigrationWithProductionTrafficUser --headless \
		-u 30 -r 5 -t 180s \
		--csv=results/priority-test --csv-full-history \
		--html=results/priority-report.html

loadtest-backfill-drain: ## Run backfill drain rate measurement (headless, 10 users, 3 min)
	@mkdir -p results
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		BackfillDrainRateUser --headless \
		-u 10 -r 10 -t 180s \
		--csv=results/backfill-drain --csv-full-history \
		--html=results/backfill-drain-report.html

loadtest-starvation: ## Run priority starvation test (headless, 50 users, 5 min)
	@mkdir -p results
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		PriorityStarvationTestUser --headless \
		-u 50 -r 10 -t 300s \
		--csv=results/starvation-test --csv-full-history \
		--html=results/starvation-report.html

loadtest-baseline: ## Run priority lanes disabled baseline (headless, 30 users, 3 min)
	@mkdir -p results
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 \
		PriorityLanesDisabledBaseline --headless \
		-u 30 -r 5 -t 180s \
		--csv=results/baseline-test --csv-full-history \
		--html=results/baseline-report.html

loadtest-fulfillment: ## Run fulfillment workflow load test (web UI)
	uv run locust -f loadtests/locustfile.py --host http://localhost:8000 FulfillmentUser

loadtest-loyalty: ## Run loyalty HTTP API load test (enrol/earn/redeem/transfer + campaigns)
	uv run locust -f loadtests/scenarios/loyalty.py --host http://localhost:8000 LoyaltyUser

loadtest-loyalty-events: ## Run loyalty event-driven load test (order lifecycle) — needs engine-loyalty
	uv run locust -f loadtests/scenarios/loyalty.py --host http://localhost:8000 LoyaltyRewardsUser

loadtest-seed: ## Seed baseline data (20 customers, 15 products, 5 categories, 3 warehouses, 10 loyalty accounts)
	uv run python -m loadtests.seed --host http://localhost:8000

loadtest-clean: truncate-db ## Clean all data for a fresh load test run
	docker exec shopstream-redis-1 redis-cli FLUSHDB

# Documentation
docs: ## Build documentation
	uv run mkdocs build

docs-serve: ## Serve documentation locally
	uv run mkdocs serve
