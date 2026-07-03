"""Test setup for the verification suite.

The verification tree holds the heavier correctness checks (it is separate from
the per-domain tests/ tree, which stays simple and is what people read to learn
Protean). Each check sets up only the domain(s) it needs.

Run with the in-memory adapters (no Docker required):

    .venv/bin/python -m pytest verification/ --protean-env memory -q
"""

import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def reviews_bed():
    from reviews.domain import reviews

    bed = DomainFixture(reviews)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture()
def reviews_ctx(reviews_bed):
    with reviews_bed.domain_context():
        yield


@pytest.fixture(scope="session")
def loyalty_bed():
    from loyalty.domain import loyalty

    bed = DomainFixture(loyalty)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture()
def loyalty_ctx(loyalty_bed):
    with loyalty_bed.domain_context():
        yield


@pytest.fixture(scope="session")
def inventory_bed():
    from inventory.domain import inventory

    bed = DomainFixture(inventory)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture()
def inventory_ctx(inventory_bed):
    with inventory_bed.domain_context():
        yield


@pytest.fixture(scope="session")
def ordering_bed():
    from ordering.domain import ordering

    bed = DomainFixture(ordering)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture()
def ordering_ctx(ordering_bed):
    with ordering_bed.domain_context():
        yield


@pytest.fixture(scope="session")
def payments_bed():
    from payments.domain import payments

    bed = DomainFixture(payments)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture()
def payments_ctx(payments_bed):
    with payments_bed.domain_context():
        yield
