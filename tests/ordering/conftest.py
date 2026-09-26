import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def ordering_bed():
    from ordering.domain import ordering

    bed = DomainFixture(ordering)
    bed.setup()
    yield bed
    bed.teardown()


# The domain context is entered and left for each test. Protean's generated
# conftest (`bootstrap_domain`) holds one context for the whole session instead.
# We differ on purpose: nine domains share one pytest session, so each package's
# tests need their own domain active. `domain_context()` also resets providers,
# brokers and the event store after each test.
@pytest.fixture(autouse=True)
def _ctx(ordering_bed):
    with ordering_bed.domain_context():
        yield
