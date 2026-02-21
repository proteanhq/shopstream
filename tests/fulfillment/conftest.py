import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def fulfillment_bed():
    from fulfillment.domain import fulfillment

    bed = DomainFixture(fulfillment)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(autouse=True)
def _ctx(fulfillment_bed):
    with fulfillment_bed.domain_context():
        yield
