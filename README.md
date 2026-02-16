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

The API is now available at `http://localhost:8000`. Try it:

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
| Monitor | `make monitor` | 9000 | Outbox/stream/health dashboard |

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

### 3. Engine Workers

Engine workers process events asynchronously. Each engine runs an OutboxProcessor (polls the outbox table, publishes to Redis Streams) and StreamSubscriptions (consume from Redis, invoke projectors).

```bash
# Run both engines in one process
make engine

# Or run individually (recommended for production)
make engine-identity
make engine-catalogue
```

### 4. Monitoring

```bash
make monitor
```

Available at `http://localhost:9000`:

| Endpoint | Description |
|----------|-------------|
| `GET /` | System overview |
| `GET /health` | Infrastructure health (Redis connectivity, memory, uptime) |
| `GET /outbox` | Combined outbox status for all domains |
| `GET /identity/outbox` | Identity outbox queue depth by status |
| `GET /catalogue/outbox` | Catalogue outbox queue depth by status |
| `GET /streams` | Redis stream lengths, consumer groups, pending messages |

### Development Workflow

```bash
# One-command setup: starts Docker + creates schemas
make dev

# Then in separate terminals:
make api               # Terminal 1: web server
make engine-identity   # Terminal 2: identity worker
make engine-catalogue  # Terminal 3: catalogue worker
make monitor           # Terminal 4: monitoring (optional)
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

Tests use `PROTEAN_ENV=test`, which keeps `event_processing = "sync"` so projectors fire during UoW commit for deterministic assertions.

## Configuration

### Domain Configuration

Each domain has a `domain.toml` in its package directory. Key settings:

```toml
event_processing = "sync"        # Base: sync for tests
command_processing = "sync"
enable_outbox = true             # Events written to outbox table

[databases.default]
provider = "postgresql"
database_uri = "${DATABASE_URL|postgresql://...}"

[brokers.default]
provider = "redis"
URI = "redis://127.0.0.1:6379/0"

[event_store]
provider = "message_db"
database_uri = "${MESSAGE_DB_URL|postgresql://...}"

# Production overlay (PROTEAN_ENV=production)
[production]
event_processing = "async"       # Projectors fire via Engine workers
debug = false
```

### Environment Overlays

Protean applies config sections based on `PROTEAN_ENV`:

| Environment | `event_processing` | Projectors fire... |
|-------------|-------------------|-------------------|
| `test` | sync | During UoW commit (immediate) |
| `production` (default) | async | Via Engine workers (eventually consistent) |

### Environment Variables

See [.env.example](.env.example) for all variables:

```bash
PROTEAN_ENV=production
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/identity_local
CATALOGUE_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/catalogue_local
MESSAGE_DB_URL=postgresql://message_store:message_store@localhost:5433/message_store
REDIS_URL=redis://127.0.0.1:6379/0
SECRET_KEY=change-me-in-production
```

## Available Commands

Run `make help` for the full list.

### API & Workers

```bash
make api               # FastAPI web server (port 8000)
make engine            # All domain engines
make engine-identity   # Identity engine only
make engine-catalogue  # Catalogue engine only
make monitor           # Monitoring dashboard (port 9000)
```

### Database

```bash
make setup-db          # Create all database schemas
make drop-db           # Drop all database schemas
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
make docker-down       # Stop services
make docker-logs       # Follow service logs
make docker-clean      # Stop + remove volumes
make dev               # docker-up + setup-db
```
