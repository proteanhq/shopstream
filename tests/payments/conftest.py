import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def payments_bed():
    from payments.domain import payments

    bed = DomainFixture(payments)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(autouse=True)
def _ctx(payments_bed):
    with payments_bed.domain_context():
        yield
