import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def loyalty_bed():
    from loyalty.domain import loyalty

    bed = DomainFixture(loyalty)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(autouse=True)
def _ctx(loyalty_bed):
    with loyalty_bed.domain_context():
        yield
