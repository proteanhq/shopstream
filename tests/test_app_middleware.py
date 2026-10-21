"""The API's user-context middleware stays quiet on paths mapped to no domain."""

import warnings

from fastapi.testclient import TestClient

from app import app


def test_unmapped_path_emits_no_domain_context_warning():
    client = TestClient(app)

    with warnings.catch_warnings(record=True) as caught:
        # Overrides the pyproject.toml ignore filter, which would hide the warning
        warnings.simplefilter("always")
        response = client.get("/docs", headers={"X-User-Id": "user-1", "X-Actor-Id": "actor-1"})

    assert response.status_code == 200
    messages = [str(w.message) for w in caught]
    assert not [m for m in messages if "Working outside of domain context" in m]
