import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def reviews_bed():
    from reviews.domain import reviews

    bed = DomainFixture(reviews)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(autouse=True)
def _ctx(reviews_bed):
    with reviews_bed.domain_context():
        yield
