"""Custom repository for RewardAccount.

Protean provides a default repository for every aggregate; this custom one adds
domain-specific queries via the underlying DAO (`self._dao`), exercising Q objects,
F expressions, lookups (gte/in), ordering, and limits — none of which are used by the
other ShopStream domains (they all rely on default repositories).
"""

from protean import Q
from protean.utils.query import F

from loyalty.domain import loyalty
from loyalty.reward.reward_account import RewardAccount


@loyalty.repository(part_of=RewardAccount)
class RewardAccountRepository:
    def top_savers(self, limit=3):
        """Active accounts with the highest balances (order_by + limit)."""
        return self._dao.query.filter(status="Active").order_by("-points_balance").limit(limit).all().items

    def never_redeemed(self):
        """Accounts whose balance still equals lifetime points (F field comparison)."""
        return self._dao.query.filter(points_balance=F("lifetime_points")).all().items

    def eligible_for_promo(self, tiers, min_balance):
        """Accounts in any of `tiers` OR with at least `min_balance` points.

        Combines a Q-object OR with the ``in`` and ``gte`` lookups.
        """
        criteria = Q(tier__in=tiers) | Q(points_balance__gte=min_balance)
        return self._dao.query.filter(criteria).all().items
