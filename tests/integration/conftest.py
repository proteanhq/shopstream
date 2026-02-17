"""Fixtures for cross-domain integration tests.

These tests verify that events from both the Identity and Catalogue domains
are correctly written to the outbox table for subsequent publishing to
Redis Streams by the Engine's OutboxProcessor.
"""

import pytest
from protean.integrations.pytest import DomainFixture


@pytest.fixture(scope="session")
def identity_bed():
    from identity.domain import identity

    bed = DomainFixture(identity)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture(scope="session")
def catalogue_bed():
    from catalogue.domain import catalogue

    bed = DomainFixture(catalogue)
    bed.setup()
    yield bed
    bed.teardown()


@pytest.fixture
def identity_ctx(identity_bed):
    """Push identity domain context for a test, with cleanup."""
    with identity_bed.domain_context() as domain:
        yield domain


@pytest.fixture
def catalogue_ctx(catalogue_bed):
    """Push catalogue domain context for a test, with cleanup."""
    with catalogue_bed.domain_context() as domain:
        yield domain
