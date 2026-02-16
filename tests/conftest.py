import os
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="test",
        help="Config environment to run tests on",
    )


def pytest_sessionstart(session):
    """Pytest hook to run before collecting tests.

    Fetch and activate the domain by pushing the associated domain_context. The activated domain can then be referred to elsewhere as `current_domain`
    """
    os.environ["PROTEAN_ENV"] = session.config.option.env

    from identity.domain import identity

    identity.init()
    identity.domain_context().push()


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their directory location."""
    for item in items:
        # Get the test file path relative to the tests directory
        test_path = Path(item.fspath)

        # Mark tests based on their directory
        if "/domain/" in str(test_path):
            item.add_marker(pytest.mark.domain)
        elif "/application/" in str(test_path):
            item.add_marker(pytest.mark.application)
        elif "/integration/" in str(test_path):
            item.add_marker(pytest.mark.integration)
            # Integration tests are often slower
            if not any(m.name == "fast" for m in item.iter_markers()):
                item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session", autouse=True)
def setup_db(request):
    from identity.domain import identity
    from identity.utils.db import drop_db, setup_db

    setup_db(identity)

    yield

    drop_db(identity)


@pytest.fixture(autouse=True)
def run_around_tests():
    """Fixture to automatically cleanup infrastructure after every test"""
    yield

    from protean import current_domain

    # Clear all databases
    for _, provider in current_domain.providers.items():
        provider._data_reset()

    # Drain event stores
    current_domain.event_store.store._data_reset()
