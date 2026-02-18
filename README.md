# ShopStream

**Version 0.1.0**

E-Commerce Platform built on [Protean](https://github.com/proteanhq/protean) — a Domain-Driven Design framework for Python.

ShopStream implements a multi-domain CQRS architecture with two bounded contexts:

- **Identity** — Customer accounts, profiles, addresses, tiers
- **Catalogue** — Products, variants, categories, pricing

Commands are processed synchronously via a FastAPI web server. Events flow asynchronously through the outbox pattern and Redis Streams, with Engine workers maintaining read-model projections.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Running the Platform](#running-the-platform)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Load Testing](#load-testing)
- [Configuration](#configuration)
- [Available Commands](#available-commands)

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/) for dependency management
- Docker and Docker Compose for infrastructure services
- Make (optional, for convenience commands)

## Quick Start

```bash
# Install dependencies
make install

# Start infrastructure (PostgreSQL, Message DB, Redis)
make docker-up

# Create database schemas
make setup-db

# Start the API server
make api
```

The API is now available at `http://localhost:8000`. Browse the interactive API docs at **http://localhost:8000/docs** (powered by [Scalar](https://scalar.com)).

```bash
curl -X POST http://localhost:8000/customers \
  -H "Content-Type: application/json" \
  -d '{"external_id":"EXT-1","email":"jane@example.com","first_name":"Jane","last_name":"Doe"}'
```

To process events asynchronously (update projections, etc.), start the Engine workers in separate terminals:

```bash
make engine-identity   # Terminal 2
make engine-catalogue  # Terminal 3
```

## Architecture

```
  ┌──────────────────────┐          ┌─────────────────────┐
  │  FastAPI Web Server  │          │   PostgreSQL (5432)  │
  │    (port 8000)       │          │  identity_local DB   │
  │                      │          │  catalogue_local DB  │
  │  /customers/*        │─────────▶│                      │
  │  /products/*         │ commands │  Outbox Table        │
  │  /categories/*       │          └──────────┬───────────┘
  └──────────────────────┘                     │
                                               │ OutboxProcessor
                                               ▼
  ┌──────────────────────┐          ┌──────────────────────┐
  │  Engine Workers      │◀─────────│   Redis Streams      │
  │                      │ consume  │   (port 6379)        │
  │  Identity Engine     │          └──────────────────────┘
  │  Catalogue Engine    │
  │                      │          ┌──────────────────────┐
  │  - OutboxProcessor   │          │   Message DB (5433)  │
  │  - Projector Subs    │          │   Event Store        │
  └──────────────────────┘          └──────────────────────┘

  ┌──────────────────────┐
  │  Monitor (port 9000) │
  │  /outbox, /streams   │
  │  /health             │
  └──────────────────────┘
```

### Event Flow

1. HTTP request hits the FastAPI server
2. Command handler mutates the aggregate and raises domain events
3. UoW commit writes aggregate state + outbox records **atomically**
4. HTTP response returns to client
5. Engine's OutboxProcessor picks up pending outbox records and publishes to Redis Streams
6. Engine's StreamSubscription reads from Redis, invokes projectors to update read models
7. On failure, messages are retried with exponential backoff, then moved to a DLQ

### Process Model

| Process | Command | Port | Purpose |
|---------|---------|------|---------|
| Web Server | `make api` | 8000 | Synchronous command processing |
| Identity Engine | `make engine-identity` | — | Async event processing for Identity domain |
| Catalogue Engine | `make engine-catalogue` | — | Async event processing for Catalogue domain |
| Observatory | `make observatory` | 9000 | Live message flow dashboard + Prometheus metrics |

## Running the Platform

### 1. Infrastructure

```bash
# Start PostgreSQL, Message DB, and Redis
make docker-up

# Create database tables for both domains
make setup-db
```

### 2. API Server

```bash
make api
```

Starts a FastAPI server on port 8000 with hot-reload. Routes are mapped to domain contexts:

| Route prefix | Domain |
|-------------|--------|
| `/customers/*` | Identity |
| `/products/*` | Catalogue |
| `/categories/*` | Catalogue |
| `/health` | — |
| `/docs` | Interactive API reference (Scalar) |
| `/redoc` | ReDoc API documentation |
| `/openapi.json` | OpenAPI 3.x spec |

### 3. Engine Workers

Engine workers process events asynchronously. Each engine runs an OutboxProcessor (polls the outbox table, publishes to Redis Streams) and StreamSubscriptions (consume from Redis, invoke projectors).

```bash
# Run both engines in one process
make engine

# Or run individually (recommended for production)
make engine-identity
make engine-catalogue
```

### 4. Observatory

```bash
make observatory
```

Available at `http://localhost:9000` — provides a live message flow dashboard and Prometheus metrics endpoint at `/metrics` for monitoring outbox depth, Redis stream health, and broker statistics across both domains.

### Development Workflow

```bash
# One-command setup: starts Docker + creates schemas
make dev

# Then in separate terminals:
make api               # Terminal 1: web server
make engine-identity   # Terminal 2: identity worker
make engine-catalogue  # Terminal 3: catalogue worker
make observatory       # Terminal 4: monitoring (optional)
```

## Testing

```bash
# Run all tests (626 tests)
make test

# With coverage report
make test-cov

# By layer
make test-domain        # Pure business logic (no DB)
make test-application   # Command handler tests (with DB)
make test-integration   # Cross-domain outbox/event tests

# By domain
make test-identity
make test-catalogue

# Fast tests only (skip slow/integration)
make test-fast
```

Tests use `PROTEAN_ENV=test`, which keeps `event_processing = "sync"` so projectors fire during UoW commit for deterministic assertions. Tests run against separate `_test` databases so they never destroy dev data (see [Configuration](#configuration)).

## Load Testing

ShopStream includes a [Locust](https://locust.io)-based load testing suite that simulates realistic e-commerce traffic across both domains. It exercises the full event pipeline — API throughput, outbox processing, Redis Streams publishing, and projector consumption.

```bash
# Install load testing dependencies
make loadtest-install

# Start the backend (API + engines in Docker)
make docker-dev                # or make docker-dev-scaled for multi-worker engines

# Start the Observatory for monitoring
make observatory               # Terminal 2

# Start Locust web UI
make loadtest                  # Terminal 3 — opens at http://localhost:8089
```

The suite provides 5 user classes covering 6 journey scenarios:

| User Class | Scenarios | Purpose |
|------------|-----------|---------|
| `MixedWorkloadUser` | All 6 journeys, weighted | Realistic cross-domain baseline |
| `IdentityUser` | Customer registration, lifecycle, tiers | Identity domain focus |
| `CatalogueUser` | Product building, lifecycle, categories | Catalogue domain focus |
| `EventFloodUser` | Rapid aggregate creation | Event pipeline saturation |
| `SpikeUser` | Burst registration | Sudden traffic handling |

```bash
# Key commands
make loadtest-mixed            # Mixed workload (web UI)
make loadtest-stress           # Event pipeline stress (web UI)
make loadtest-headless         # CI mode: 50 users, 5 min, CSV + HTML report
make loadtest-spike            # Burst: 100 users, instant spawn, 2 min
make loadtest-stack            # Full stack: Docker + Observatory + Locust
make loadtest-stack-scaled     # Same with 3 identity + 2 catalogue engines
make loadtest-clean            # Truncate all data for a fresh run
```

During testing, monitor three dashboards simultaneously: **Locust** (`:8089`) for request metrics, **Observatory** (`:9000`) for event flow and outbox depth, and **Prometheus** (`:9000/metrics`) for raw counters. See [`loadtests/README.md`](loadtests/README.md) for full documentation.

## Configuration

### Domain Configuration

Each domain has a `domain.toml` in its package directory. Key settings:

```toml
event_processing = "sync"        # Base config (development)
command_processing = "sync"
enable_outbox = true             # Events written to outbox table

[databases.default]
provider = "postgresql"
database_uri = "${DATABASE_URL|postgresql://.../<domain>_local}"

[brokers.default]
provider = "redis"
URI = "redis://127.0.0.1:6379/0"

[event_store]
provider = "message_db"
database_uri = "${MESSAGE_DB_URL|postgresql://...}"

# Test overlay — separate database for tests
[test]
testing = true
[test.databases.default]
database_uri = "${TEST_DATABASE_URL|postgresql://.../<domain>_test}"

# Production overlay
[production]
event_processing = "async"       # Projectors fire via Engine workers
debug = false
[production.databases.default]
database_uri = "${DATABASE_URL|postgresql://.../<domain>}"
```

### Environment Overlays

Protean applies config sections from `domain.toml` based on `PROTEAN_ENV`:

| Environment | Identity DB | Catalogue DB | `event_processing` | Projectors fire... |
|-------------|------------|-------------|-------------------|-------------------|
| _(unset)_ — development | `identity_local` | `catalogue_local` | sync | During UoW commit |
| `test` | `identity_test` | `catalogue_test` | sync | During UoW commit |
| `production` | `identity` | `catalogue` | async | Via Engine workers |

Tests and dev use separate databases so running the test suite never destroys development data.

### Environment Variables

See [.env.example](.env.example) for all variables:

```bash
PROTEAN_ENV=production

# Development databases
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/identity_local
CATALOGUE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/catalogue_local

# Test databases (used when PROTEAN_ENV=test)
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/identity_test
TEST_CATALOGUE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/catalogue_test

MESSAGE_DB_URL=postgresql://message_store:message_store@localhost:5433/message_store
REDIS_URL=redis://127.0.0.1:6379/0
SECRET_KEY=change-me-in-production
```

## Available Commands

Run `make help` for the full list.

### API & Workers

```bash
make api                    # FastAPI web server (port 8000)
make engine-identity        # Identity engine only
make engine-catalogue       # Catalogue engine only
make engine-identity-scaled # Identity engine with 4 workers
make engine-catalogue-scaled# Catalogue engine with 4 workers
make observatory            # Observatory dashboard (port 9000)
```

### Database

```bash
make setup-db          # Create all database schemas
make drop-db           # Drop all database schemas
make truncate-db       # Delete all data (preserves schema)
```

### Testing

```bash
make test              # All tests
make test-cov          # Tests with coverage
make test-domain       # Domain layer only
make test-application  # Application layer only
make test-integration  # Integration tests
make test-fast         # Skip slow tests
```

### Code Quality

```bash
make lint              # Ruff linting
make format            # Ruff formatting
make typecheck         # MyPy type checking
make check             # All checks (lint + typecheck + test)
make pre-commit        # Run pre-commit hooks
```

### Docker

```bash
make docker-up         # Start infrastructure services
make docker-dev        # Full stack in Docker (API + engines)
make docker-dev-scaled # Full stack with scaled engines
make docker-down       # Stop services
make docker-logs       # Follow service logs
make docker-clean      # Stop + remove volumes
make dev               # docker-up (infrastructure only)
```

### Load Testing

```bash
make loadtest-install       # Install Locust dependency
make loadtest               # Locust web UI (all scenarios)
make loadtest-mixed         # Mixed workload
make loadtest-stress        # Event pipeline stress
make loadtest-headless      # Headless: 50 users, 5 min, reports
make loadtest-spike         # Spike: 100 users, instant burst
make loadtest-stack         # Full stack + Locust (one command)
make loadtest-stack-scaled  # Same with scaled engines
make loadtest-clean         # Truncate data for fresh run
```
