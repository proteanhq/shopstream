"""PointsLeaderboard — a CACHE-backed projection of live points balances.

Exercises a cache-backed projection (`cache="loyalty"`, backed by Redis in real envs
and an in-memory cache in tests) — distinct from the database-backed projections used
everywhere else in ShopStream. Cache-backed projections are written via `current_domain.cache_for(...).add(instance)`
and read via `cache_for(...).get(key)` (or `view_for(...)`), NOT `repository_for(...)` —
that routes to a database provider and fails for a cache projection (provider is None).
"""

from protean.core.projector import on
from protean.fields import Identifier, Integer, String
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.reward.events import (
    PointsEarned,
    PointsRedeemed,
    RewardAccountEnrolled,
)
from loyalty.reward.reward_account import RewardAccount


@loyalty.projection(cache="loyalty")
class PointsLeaderboard:
    account_id = Identifier(identifier=True, required=True)
    customer_id = String(required=True)
    tier = String()
    points_balance = Integer(default=0)


@loyalty.projector(projector_for=PointsLeaderboard, aggregates=[RewardAccount])
class PointsLeaderboardProjector:
    @on(RewardAccountEnrolled)
    def on_enrolled(self, event):
        current_domain.cache_for(PointsLeaderboard).add(
            PointsLeaderboard(
                account_id=event.account_id,
                customer_id=event.customer_id,
                tier=event.tier,
                points_balance=0,
            )
        )

    @on(PointsEarned)
    def on_earned(self, event):
        self._set_balance(event.account_id, event.balance_after)

    @on(PointsRedeemed)
    def on_redeemed(self, event):
        self._set_balance(event.account_id, event.balance_after)

    def _set_balance(self, account_id, balance):
        # Read the existing entry through view_for (which builds the cache key),
        # then re-write the updated record through the cache provider.
        entry = current_domain.view_for(PointsLeaderboard).get(account_id)
        entry.points_balance = balance
        current_domain.cache_for(PointsLeaderboard).add(entry)
