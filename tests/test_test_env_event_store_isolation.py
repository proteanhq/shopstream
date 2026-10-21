"""Under `PROTEAN_ENV=test`, every context's event store is the test database, not the dev one.

Protean's test fixtures truncate the event store between tests. With no `TEST_MESSAGE_DB_URL` set,
the test env puts every context on `message_store_test`, so a local test run never empties the
dev stack's `message_store`. The env var still overrides it, which is how CI picks its own port.

Each test loads the `domain.toml` files directly, so the result does not depend on which env this
pytest run uses.
"""

from pathlib import Path

import pytest
from protean.domain.config import Config2

SRC = Path(__file__).resolve().parent.parent / "src"
# Every context with a domain.toml, so a new context without the overlay fails here too.
CONTEXTS = sorted(path.parent.name for path in SRC.glob("*/domain.toml"))
TEST_STORE = "postgresql://message_store:message_store@localhost:15433/message_store_test"
DEV_STORE = "postgresql://message_store:message_store@localhost:15433/message_store"


def _config(context: str, monkeypatch: pytest.MonkeyPatch, env: str | None) -> Config2:
    for var in ("MESSAGE_DB_URL", "TEST_MESSAGE_DB_URL"):
        monkeypatch.delenv(var, raising=False)
    if env is None:
        monkeypatch.delenv("PROTEAN_ENV", raising=False)
    else:
        monkeypatch.setenv("PROTEAN_ENV", env)
    return Config2.load_from_path(str(SRC / context))


@pytest.mark.parametrize("context", CONTEXTS)
def test_test_env_event_store_defaults_to_the_test_database(context, monkeypatch):
    store = _config(context, monkeypatch, "test")["event_store"]

    assert (store["provider"], store["database_uri"]) == ("message_db", TEST_STORE)


@pytest.mark.parametrize("context", CONTEXTS)
def test_dev_env_event_store_stays_on_the_dev_database(context, monkeypatch):
    store = _config(context, monkeypatch, None)["event_store"]

    assert store["database_uri"] == DEV_STORE


def test_every_context_is_checked():
    assert len(CONTEXTS) >= 9


@pytest.mark.parametrize("context", CONTEXTS)
def test_env_var_overrides_the_test_database(context, monkeypatch):
    monkeypatch.setenv("PROTEAN_ENV", "test")
    monkeypatch.setenv("TEST_MESSAGE_DB_URL", "postgresql://message_store:message_store@ci-db:5433/ci_store")

    store = Config2.load_from_path(str(SRC / context))["event_store"]

    assert store["database_uri"] == "postgresql://message_store:message_store@ci-db:5433/ci_store"
