import os

import pytest


@pytest.fixture(scope="session")
def _identity_domain(request):
    """Initialize the identity domain once per session."""
    os.environ["PROTEAN_ENV"] = request.config.option.env

    from identity.domain import identity

    identity.init()
    return identity


@pytest.fixture(scope="session", autouse=True)
def setup_db(_identity_domain):
    from identity.utils.db import drop_db, setup_db

    setup_db(_identity_domain)

    yield

    drop_db(_identity_domain)


@pytest.fixture(autouse=True)
def run_around_tests(_identity_domain):
    """Push domain context before each test, cleanup after."""
    ctx = _identity_domain.domain_context()
    ctx.push()

    yield

    from protean import current_domain

    for _, provider in current_domain.providers.items():
        provider._data_reset()

    for _, broker in current_domain.brokers.items():
        broker._data_reset()

    current_domain.event_store.store._data_reset()
    ctx.pop()
