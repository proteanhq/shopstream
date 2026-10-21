"""Guard that Redis reports the PointsLeaderboard cache TTL in seconds.

Protean's `RedisCache.get_ttl()` used to return milliseconds. Under `--protean-env
test` the loyalty cache is in memory, so this test builds its own Redis cache with
the `[test.caches.loyalty]` URI (the test DB 10, not the dev cache DB 9) and the
`[caches.loyalty]` TTL, and writes a leaderboard entry through it, the
same `add()` call the projector makes. `REDIS_CACHE_URL`, then `REDIS_URL`, override
the URI, so CI's real-stores leg points it at the run's Redis.
"""

import os
import uuid

import pytest
from protean.adapters.cache.redis import RedisCache
from protean.utils.globals import current_domain

from loyalty.projections.points_leaderboard import PointsLeaderboard


@pytest.fixture
def redis_cache():
    if os.environ.get("PROTEAN_ENV") == "memory":
        pytest.skip("needs a real Redis; the memory env has none")

    settings = current_domain.config["caches"]["loyalty"]
    url_from_env = os.environ.get("REDIS_CACHE_URL") or os.environ.get("REDIS_URL")
    cache = RedisCache(
        "loyalty",
        current_domain,
        {"provider": "redis", "URI": url_from_env or settings["URI"], "TTL": settings["TTL"]},
    )
    try:
        cache.ping()
    except Exception as exc:
        cache.close()
        # A Redis URL set in the environment means this run has a Redis, so an
        # unreachable one is a broken setup and must not hide the guard as a skip.
        if url_from_env:
            raise
        pytest.skip(f"Redis is unreachable: {exc}")

    yield cache
    cache.close()


def test_leaderboard_entry_ttl_is_reported_in_seconds(redis_cache):
    configured_ttl = redis_cache.conn_info["TTL"]
    assert configured_ttl == 3600

    # A unique key, removed afterwards: in CI `REDIS_URL` is a database other
    # domains use, so the test must never flush it.
    account_id = f"ttl-guard-{uuid.uuid4()}"
    entry = PointsLeaderboard(account_id=account_id, customer_id="cust-ttl", points_balance=10)
    key = f"points_leaderboard:::{account_id}"

    redis_cache.add(entry)
    try:
        ttl = redis_cache.get_ttl(key)
    finally:
        redis_cache.remove_by_key(key)

    assert ttl is not None
    # Milliseconds would read about 3,600,000; a wrong scale the other way about 3.6.
    assert configured_ttl - 100 <= ttl <= configured_ttl
