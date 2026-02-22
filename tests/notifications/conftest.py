import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def notifications_bed():
    from notifications.domain import notifications

    bed = DomainFixture(notifications)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(autouse=True)
def _ctx(notifications_bed):
    with notifications_bed.domain_context():
        yield
