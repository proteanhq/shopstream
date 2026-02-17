import pytest
from protean.integrations.pytest import DomainFixture


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
