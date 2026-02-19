import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def inventory_bed():
    from inventory.domain import inventory

    bed = DomainFixture(inventory)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(autouse=True)
def _ctx(inventory_bed):
    with inventory_bed.domain_context():
        yield
