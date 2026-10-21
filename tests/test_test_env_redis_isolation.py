"""Under `PROTEAN_ENV=test`, every context's Redis brokers use the test DBs, not the dev DBs.

A broker reset in a test flushes the whole Redis DB the broker points at. With no `REDIS_URL` or
`REDIS_EXTERNAL_URL` set, the test env puts every internal broker on DB 10 and the shared bus on
DB 14, so a local test run never flushes a dev engine's streams (DBs 0 to 8 and 15). The env vars
still override both, which is how CI picks its own DBs.

Each test loads the `domain.toml` files directly, so the result does not depend on which env this
pytest run uses.
"""

from pathlib import Path

import pytest
from protean.domain.config import Config2

SRC = Path(__file__).resolve().parent.parent / "src"
CONTEXTS = [
    "catalogue",
    "fulfillment",
    "identity",
    "inventory",
    "loyalty",
    "notifications",
    "ordering",
    "payments",
    "reviews",
]
TEST_INTERNAL = "redis://127.0.0.1:16379/10"
TEST_BUS = "redis://127.0.0.1:16379/14"


def _config(context: str, monkeypatch: pytest.MonkeyPatch, env: str | None) -> Config2:
    for var in ("REDIS_URL", "REDIS_EXTERNAL_URL", "REDIS_CACHE_URL"):
        monkeypatch.delenv(var, raising=False)
    if env is None:
        monkeypatch.delenv("PROTEAN_ENV", raising=False)
    else:
        monkeypatch.setenv("PROTEAN_ENV", env)
    return Config2.load_from_path(str(SRC / context))


@pytest.mark.parametrize("context", CONTEXTS)
def test_test_env_brokers_default_to_the_test_dbs(context, monkeypatch):
    brokers = _config(context, monkeypatch, "test")["brokers"]

    assert (brokers["default"]["provider"], brokers["default"]["URI"]) == ("redis", TEST_INTERNAL)
    assert (brokers["global"]["provider"], brokers["global"]["URI"]) == ("redis", TEST_BUS)


@pytest.mark.parametrize("context", CONTEXTS)
def test_dev_env_brokers_stay_off_the_test_dbs(context, monkeypatch):
    brokers = _config(context, monkeypatch, None)["brokers"]

    assert brokers["default"]["URI"] != TEST_INTERNAL
    assert brokers["global"]["URI"] != TEST_BUS


def test_env_vars_override_the_test_dbs(monkeypatch):
    monkeypatch.setenv("PROTEAN_ENV", "test")
    monkeypatch.setenv("REDIS_URL", "redis://ci-redis:6379/0")
    monkeypatch.setenv("REDIS_EXTERNAL_URL", "redis://ci-redis:6379/15")

    brokers = Config2.load_from_path(str(SRC / "ordering"))["brokers"]

    assert brokers["default"]["URI"] == "redis://ci-redis:6379/0"
    assert brokers["global"]["URI"] == "redis://ci-redis:6379/15"


def test_test_env_loyalty_cache_uri_is_off_the_dev_cache_db(monkeypatch):
    # The cache TTL test builds a real Redis cache from this URI under the test env.
    cache = _config("loyalty", monkeypatch, "test")["caches"]["loyalty"]

    assert cache["URI"] == TEST_INTERNAL
