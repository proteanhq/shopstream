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
