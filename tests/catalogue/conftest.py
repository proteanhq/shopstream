import os

import pytest


@pytest.fixture(scope="session")
def _catalogue_domain(request):
    """Initialize the catalogue domain once per session."""
    os.environ["PROTEAN_ENV"] = request.config.option.env

    from catalogue.domain import catalogue

    catalogue.init()
    return catalogue


@pytest.fixture(scope="session", autouse=True)
def setup_db(_catalogue_domain):
    from catalogue.domain import catalogue
    from catalogue.utils.db import drop_db, setup_db

    setup_db(catalogue)

    yield

    drop_db(catalogue)


@pytest.fixture(autouse=True)
def run_around_tests(_catalogue_domain):
    """Push domain context before each test, cleanup after."""
    ctx = _catalogue_domain.domain_context()
    ctx.push()

    yield

    from protean import current_domain

    for _, provider in current_domain.providers.items():
        provider._data_reset()

    current_domain.event_store.store._data_reset()
    ctx.pop()
