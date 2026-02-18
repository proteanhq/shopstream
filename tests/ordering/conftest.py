import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def ordering_bed():
    from ordering.domain import ordering

    bed = DomainFixture(ordering)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(autouse=True)
def _ctx(ordering_bed):
    with ordering_bed.domain_context():
        yield
