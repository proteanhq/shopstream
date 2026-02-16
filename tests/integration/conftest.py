"""Fixtures for cross-domain integration tests.

These tests verify that events from both the Identity and Catalogue domains
are correctly written to the outbox table for subsequent publishing to
Redis Streams by the Engine's OutboxProcessor.
"""

import os

import pytest


@pytest.fixture(scope="session")
def _identity_domain(request):
    """Initialize the identity domain once per session."""
    os.environ["PROTEAN_ENV"] = request.config.option.env

    from identity.domain import identity

    identity.init()
    return identity


@pytest.fixture(scope="session")
def _catalogue_domain(request):
    """Initialize the catalogue domain once per session."""
    os.environ["PROTEAN_ENV"] = request.config.option.env

    from catalogue.domain import catalogue

    catalogue.init()
    return catalogue


@pytest.fixture(scope="session", autouse=True)
def setup_databases(_identity_domain, _catalogue_domain):
    """Create database schemas for both domains."""
    from catalogue.utils.db import drop_db as drop_catalogue_db
    from catalogue.utils.db import setup_db as setup_catalogue_db
    from identity.utils.db import drop_db as drop_identity_db
    from identity.utils.db import setup_db as setup_identity_db

    setup_identity_db(_identity_domain)
    setup_catalogue_db(_catalogue_domain)

    yield

    drop_identity_db(_identity_domain)
    drop_catalogue_db(_catalogue_domain)


@pytest.fixture
def identity_ctx(_identity_domain):
    """Push identity domain context for a test, with cleanup."""
    ctx = _identity_domain.domain_context()
    ctx.push()

    yield _identity_domain

    from protean import current_domain

    for _, provider in current_domain.providers.items():
        provider._data_reset()

    for _, broker in current_domain.brokers.items():
        broker._data_reset()

    current_domain.event_store.store._data_reset()
    ctx.pop()


@pytest.fixture
def catalogue_ctx(_catalogue_domain):
    """Push catalogue domain context for a test, with cleanup."""
    ctx = _catalogue_domain.domain_context()
    ctx.push()

    yield _catalogue_domain

    from protean import current_domain

    for _, provider in current_domain.providers.items():
        provider._data_reset()

    for _, broker in current_domain.brokers.items():
        broker._data_reset()

    current_domain.event_store.store._data_reset()
    ctx.pop()
