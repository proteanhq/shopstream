"""Guard that Redis reports the PointsLeaderboard cache TTL in seconds.

Protean's `RedisCache.get_ttl()` used to return milliseconds. Under `--protean-env
test` the loyalty cache is in memory, so this test builds its own Redis cache from
`REDIS_URL` with the `[caches.loyalty]` TTL and writes a leaderboard entry through
it, the same `add()` call the projector makes.
"""

import os
import uuid

import pytest
from protean.adapters.cache.redis import RedisCache
from protean.utils.globals import current_domain

from loyalty.projections.points_leaderboard import PointsLeaderboard

LOYALTY_CACHE_TTL = 3600


@pytest.fixture
def redis_cache():
    if os.environ.get("PROTEAN_ENV") == "memory":
        pytest.skip("needs a real Redis; the memory env has none")

    cache = RedisCache(
        "loyalty",
        current_domain,
        {
            "provider": "redis",
            "URI": os.environ.get("REDIS_URL", "redis://127.0.0.1:16379/8"),
            "TTL": LOYALTY_CACHE_TTL,
        },
    )
    try:
        cache.ping()
    except Exception as exc:
        cache.close()
        pytest.skip(f"Redis is unreachable: {exc}")

    yield cache
    cache.close()


def test_leaderboard_entry_ttl_is_reported_in_seconds(redis_cache):
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
    assert LOYALTY_CACHE_TTL - 100 <= ttl <= LOYALTY_CACHE_TTL
