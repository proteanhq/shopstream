# Test Structure

This project follows a layered test architecture aligned with Domain-Driven Design principles:

## Test Categories

### Domain Tests (`tests/shopstream/domain/`)
- **Coverage Target: 100%**
- Pure business logic tests
- No external dependencies
- Tests for:
  - Aggregates
  - Entities
  - Value Objects
  - Domain Services
  - Domain Events/Commands

### Application Tests (`tests/shopstream/application/`)
- **Coverage Target: 100%**
- Application layer logic tests
- May use in-memory adapters
- Tests for:
  - Command Handlers
  - Event Handlers
  - Application Services
  - Projectors
  - Repository abstractions

### Integration Tests (`tests/shopstream/integration/`)
- **Coverage Target: 90%**
- Tests with real external dependencies
- Tests for:
  - API endpoints
  - Database operations
  - Message broker integration
  - External service subscribers
  - End-to-end scenarios

## Running Tests

### By Category
```bash
# Run domain tests (100% coverage required)
make test-domain

# Run application tests (100% coverage required)
make test-application

# Run integration tests (90% coverage required)
make test-integration

# Run fast tests (excludes slow integration tests)
make test-fast
```

### With Coverage Reports
```bash
# Full coverage report
make test-cov

# Category-specific coverage
make test-cov-domain
make test-cov-application
make test-cov-integration
```

### By Markers
```bash
# Run only domain tests
uv run pytest -m domain

# Skip tests that drive a full Protean Engine (CI does this)
uv run pytest -m "not engine"

# Exclude slow tests
uv run pytest -m "not slow"
```

## Test Organization

Tests are automatically marked based on their location:
- Files in `domain/` are marked with `@pytest.mark.domain`
- Files in `application/` are marked with `@pytest.mark.application`
- Files in `integration/` are marked with `@pytest.mark.integration`, plus `@pytest.mark.slow` unless the test carries `@pytest.mark.fast`

Files in `bdd/` are also marked with `@pytest.mark.bdd`.

Additional markers can be added manually:
- `@pytest.mark.slow` for long-running tests
- `@pytest.mark.fast` to keep an integration test from getting the automatic `slow` marker
- `@pytest.mark.engine` for tests that drive a full Protean Engine (CI deselects them)

The suite runs with `--strict-markers`, so pytest rejects any marker that is not registered.

## Writing Tests

### Domain Tests Example
```python
# tests/shopstream/domain/test_aggregate.py
def test_business_rule():
    """Test pure business logic without external dependencies."""
    aggregate = MyAggregate(...)
    result = aggregate.perform_action()
    assert result.is_valid()
```

### Application Tests Example
```python
# tests/shopstream/application/test_command_handler.py
def test_command_handling():
    """Test command handling with in-memory repository."""
    handler = CommandHandler()
    command = CreateCommand(...)
    result = handler.handle(command)
    assert result.success
```

### Integration Tests Example
```python
# tests/shopstream/integration/test_database.py
def test_database_persistence():
    """Test with real database connection."""
    repository = SqlRepository()
    entity = Entity(...)
    repository.save(entity)
    retrieved = repository.get(entity.id)
    assert retrieved == entity
```

## Coverage Requirements

The project enforces different coverage thresholds:
- **Domain**: 100% - Critical business logic must be fully tested
- **Application**: 100% - All handlers and services must be tested
- **Integration**: 90% - Most integration points should be tested
- **Overall**: 85% - Minimum acceptable project coverage

Coverage reports are generated in:
- `htmlcov/` - HTML reports
- `coverage.xml` - XML report for CI/CD
- Terminal output with missing lines

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Naming**: Use descriptive test names that explain what is being tested
3. **Arrange-Act-Assert**: Follow the AAA pattern
4. **Mock External Dependencies**: In domain and application tests
5. **Use Fixtures**: Share common test setup using pytest fixtures
6. **Test Edge Cases**: Include boundary conditions and error scenarios
7. **Performance Tests**: Mark slow tests appropriately
