# Testing Guide

850+ tests organized by domain and layer. Tests run against separate `_test` databases so they never destroy dev data.

## Running Tests

```bash
make test                  # All tests
make test-domain           # Pure business logic (no DB)
make test-application      # Command handler tests (with DB)
make test-integration      # Cross-domain outbox/event tests
make test-fast             # Skip slow/integration tests
make test-identity         # All identity tests
make test-catalogue        # All catalogue tests
make test-reviews          # All reviews tests
make test-<domain>-cov     # Per-domain coverage report
make test-cov              # All tests with coverage (85% minimum)
```

## Test Structure

```
tests/
├── conftest.py                        # Auto-marks tests by directory, frozen-clock helpers
├── identity/
│   ├── conftest.py                    # Domain init, DB setup/teardown, context fixtures
│   ├── domain/                        # Pure aggregate/VO/entity logic (no DB)
│   │   ├── test_customer_aggregate.py
│   │   ├── test_customer_registration.py
│   │   ├── test_customer_addresses.py
│   │   ├── test_customer_profile.py
│   │   ├── test_customer_account_lifecycle.py
│   │   ├── test_customer_tier.py
│   │   ├── test_customer_events.py
│   │   ├── test_customer_commands.py
│   │   ├── test_customer_invariants.py
│   │   ├── test_email_value_object.py
│   │   ├── test_phone_value_object.py
│   │   ├── test_geo_coordinates.py
│   │   ├── test_profile_value_object.py
│   │   └── test_address_entity.py
│   ├── application/                   # Command handlers (requires DB)
│   │   ├── test_registration.py
│   │   ├── test_profile.py
│   │   ├── test_addresses.py
│   │   ├── test_account.py
│   │   └── test_tier.py
│   └── integration/                   # Full stack with projections
│       ├── test_api.py
│       ├── test_customer_persistence.py
│       └── test_customer_projections.py
├── catalogue/
│   ├── conftest.py
│   ├── domain/                        # ~15 test files
│   ├── application/                   # ~6 test files
│   └── integration/                   # ~4 test files
├── reviews/
│   ├── conftest.py                    # DomainFixture (session) + _ctx (autouse)
│   ├── domain/                        # Pure aggregate behavior (116 tests)
│   │   ├── test_review_aggregate.py
│   │   ├── test_rating_value_object.py
│   │   ├── test_review_invariants.py
│   │   ├── test_review_state_machine.py
│   │   ├── test_review_editing.py
│   │   ├── test_review_moderation.py
│   │   ├── test_review_voting.py
│   │   ├── test_review_reporting.py
│   │   ├── test_review_removal.py
│   │   ├── test_review_reply.py
│   │   └── test_review_events.py
│   ├── application/                   # Command handler tests (32 tests)
│   │   ├── test_submit_review_cmd.py
│   │   ├── test_submit_review_extended.py
│   │   ├── test_edit_review_cmd.py
│   │   ├── test_moderate_review_cmd.py
│   │   ├── test_vote_review_cmd.py
│   │   ├── test_report_review_cmd.py
│   │   ├── test_remove_review_cmd.py
│   │   ├── test_reply_review_cmd.py
│   │   └── test_ordering_events_handler.py
│   ├── integration/                   # API + projection tests (71 tests)
│   │   ├── test_review_api.py
│   │   ├── test_review_projections.py
│   │   ├── test_review_projections_extended.py
│   │   └── test_projector_edge_cases.py
│   └── bdd/                           # BDD scenarios (13 tests)
│       ├── conftest.py
│       ├── features/
│       │   ├── review_submission.feature
│       │   ├── review_moderation.feature
│       │   ├── review_voting.feature
│       │   └── review_lifecycle.feature
│       ├── test_review_submission.py
│       ├── test_review_moderation.py
│       ├── test_review_voting.py
│       └── test_review_lifecycle.py
└── integration/
    ├── conftest.py
    └── test_event_publishing.py       # Cross-domain event flow
```

## Test Layers

### Domain Tests (`tests/<domain>/domain/`)
- **No database required** — pure in-memory business logic
- Test aggregate creation, method behavior, invariant enforcement
- Test value object validation (EmailAddress, SKU, Price, etc.)
- Test entity behavior and constraints
- Test event raising from aggregate methods
- Test command field validation
- Auto-marked `@pytest.mark.domain`

### Application Tests (`tests/<domain>/application/`)
- **Requires database** — tests command handlers end-to-end
- Create command → `current_domain.process(command, asynchronous=False)` → verify persisted state
- Load aggregate from repository after processing to assert mutations
- Auto-marked `@pytest.mark.application`

### Integration Tests (`tests/<domain>/integration/`)
- Uses the DB, event store and broker (real ones under `test`, in-memory ones under `--protean-env memory`)
- Test API endpoints via `TestClient(app)`
- Test persistence round-trips
- Test projections updated correctly after events
- Auto-marked `@pytest.mark.integration`, plus `@pytest.mark.slow` unless the test carries `@pytest.mark.fast`

## Configuration

### The `--protean-env` option
Protean's pytest plugin adds `--protean-env` (default: `test`). It sets `PROTEAN_ENV` before collection (unless the variable is already set), so the matching `domain.toml` overlay applies when the domain modules are imported. `--protean-env memory` switches every domain to in-memory adapters, so no Docker is needed.

### Root `conftest.py`
- Auto-marks tests based on directory location:
  - `/domain/` → `@pytest.mark.domain`
  - `/application/` → `@pytest.mark.application`
  - `/integration/` → `@pytest.mark.integration`, plus `@pytest.mark.slow` unless the test already carries `@pytest.mark.fast`
  - `/bdd/` → `@pytest.mark.bdd`
- Holds the frozen-clock helpers (`frozen_clock` fixture, `frozen_clocks()`, `FrozenClock`) and `as_utc()`

### Domain `conftest.py` (one per package under `tests/`)
Two fixtures built on Protean's `DomainFixture`:

1. **`<domain>_bed`** (session scope): imports the domain, wraps it in a `DomainFixture`, calls `setup()` once (init plus schema) and `teardown()` at the end
2. **`_ctx`** (function scope, auto-used): enters `bed.domain_context()` for each test. On exit it resets the fixture's own domain's providers, brokers and event store

In a full run, all nine domains share one pytest session. Each test enters its own domain's context through `_ctx`, so `current_domain` resolves to that domain. Each `DomainFixture` owns one domain, so the reset on exit touches only that domain's providers, brokers and event store. The other domains' stores are left alone.

```python
@pytest.fixture(scope="session")
def identity_bed():
    from identity.domain import identity

    bed = DomainFixture(identity)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(autouse=True)
def _ctx(identity_bed):
    with identity_bed.domain_context():
        yield
```

## Test Patterns

### Domain Layer Test
```python
def test_customer_registration():
    customer = Customer.register(
        external_id="EXT-1",
        email="jane@example.com",
        first_name="Jane",
        last_name="Doe",
    )
    assert customer.external_id == "EXT-1"
    assert customer.email.address == "jane@example.com"
    assert customer.status == "Active"
    assert len(customer._events) == 1
    assert isinstance(customer._events[0], CustomerRegistered)
```

### Application Layer Test
```python
def test_register_customer_command():
    command = RegisterCustomer(
        external_id="EXT-1",
        email="jane@example.com",
        first_name="Jane",
        last_name="Doe",
    )
    customer_id = current_domain.process(command, asynchronous=False)
    customer = current_domain.repository_for(Customer).get(customer_id)
    assert customer.email.address == "jane@example.com"
```

### Integration Layer Test (API)
```python
def test_register_customer_api(client):
    response = client.post("/customers", json={
        "external_id": "EXT-1",
        "email": "jane@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
    })
    assert response.status_code == 201
    assert "customer_id" in response.json()
```

## Pytest Markers

| Marker | Description |
|--------|-------------|
| `domain` | Domain layer tests (auto-applied) |
| `application` | Application layer tests (auto-applied) |
| `integration` | Integration tests (auto-applied) |
| `slow` | Slow tests (auto-applied to integration tests that are not marked `fast`) |
| `bdd` | Behavior-driven tests (auto-applied under `bdd/`) |
| `fast` | Keeps an integration test from getting the automatic `slow` marker |
| `engine` | Drives a full Protean Engine. Runs locally only: CI deselects it with `-m "not engine"` because it is unreliable against CI's Redis |

Protean's pytest plugin registers `domain`, `application`, `integration`, `slow` and `bdd`. `pyproject.toml` registers `fast`, `bdd` and `engine`. The suite runs with `--strict-markers`, so pytest rejects any marker that is not registered.

## Key Notes

- Tests use `PROTEAN_ENV=test` which keeps `event_processing = "sync"`. Projectors fire during the UoW commit, so assertions are deterministic. `--protean-env memory` runs the same tests on in-memory adapters
- Each test under a domain package gets a clean slate: the autouse `_ctx` fixture resets that domain's stores after the test. In `tests/integration/`, request the `<domain>_ctx` fixture for each domain the test writes to
- DB schema is created once per session, not per test
- Integration tests in `tests/integration/` have their own conftest. It sets up identity, catalogue and loyalty, each with its own `<domain>_ctx` fixture (not auto-used) that a test requests by name
- Coverage minimum: 85% overall (`fail_under = 85` in pyproject.toml)
