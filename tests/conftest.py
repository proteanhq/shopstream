from pathlib import Path

import pytest


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their directory location."""
    for item in items:
        test_path = Path(item.fspath)

        if "/domain/" in str(test_path):
            item.add_marker(pytest.mark.domain)
        elif "/application/" in str(test_path):
            item.add_marker(pytest.mark.application)
        elif "/integration/" in str(test_path):
            item.add_marker(pytest.mark.integration)
            if not any(m.name == "fast" for m in item.iter_markers()):
                item.add_marker(pytest.mark.slow)

        if "/bdd/" in str(test_path):
            item.add_marker(pytest.mark.bdd)
