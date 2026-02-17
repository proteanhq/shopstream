import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def catalogue_bed():
    from catalogue.domain import catalogue

    bed = DomainFixture(catalogue)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(autouse=True)
def _ctx(catalogue_bed):
    with catalogue_bed.domain_context():
        yield
