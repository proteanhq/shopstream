"""Domain tests for RewardAccount tier progression and the published producer events."""

from loyalty.reward.events import PointsEarned, PointsRedeemed, TierUpgraded
from loyalty.reward.reward_account import RewardAccount, tier_for_lifetime_points


def _account(customer_id="cust-tier"):
    return RewardAccount.enroll(customer_id=customer_id)


class TestTierThresholds:
    def test_tier_for_lifetime_points_boundaries(self):
        assert tier_for_lifetime_points(0) == "bronze"
        assert tier_for_lifetime_points(999) == "bronze"
        assert tier_for_lifetime_points(1_000) == "silver"
        assert tier_for_lifetime_points(5_000) == "gold"
        assert tier_for_lifetime_points(20_000) == "platinum"
        assert tier_for_lifetime_points(50_000) == "platinum"


class TestTierProgression:
    def test_small_earn_stays_bronze_no_upgrade_event(self):
        account = _account()
        account.earn_points(100)
        assert account.tier == "bronze"
        assert not any(isinstance(e, TierUpgraded) for e in account._events)

    def test_crossing_threshold_upgrades_and_raises_event(self):
        account = _account()
        account.earn_points(1_500)
        assert account.tier == "silver"
        upgrades = [e for e in account._events if isinstance(e, TierUpgraded)]
        assert len(upgrades) == 1
        assert upgrades[0].old_tier == "bronze"
        assert upgrades[0].new_tier == "silver"
        assert upgrades[0].lifetime_points == 1_500
        assert upgrades[0].customer_id == "cust-tier"

    def test_single_earn_can_jump_multiple_tiers(self):
        account = _account()
        account.earn_points(6_000)  # straight to gold
        assert account.tier == "gold"
        upgrades = [e for e in account._events if isinstance(e, TierUpgraded)]
        assert len(upgrades) == 1
        assert upgrades[0].new_tier == "gold"

    def test_tier_never_downgrades_on_redeem(self):
        account = _account()
        account.earn_points(1_500)  # silver
        account.redeem_points(1_400)  # balance drops, lifetime unchanged
        assert account.tier == "silver"

    def test_no_duplicate_upgrade_once_at_tier(self):
        account = _account()
        account.earn_points(1_200)  # silver
        account.earn_points(100)  # still silver, no new upgrade
        upgrades = [e for e in account._events if isinstance(e, TierUpgraded)]
        assert len(upgrades) == 1


class TestProducerEventsCarryCustomerId:
    def test_points_earned_carries_customer_id(self):
        account = _account("cust-x")
        account.earn_points(50)
        earned = [e for e in account._events if isinstance(e, PointsEarned)]
        assert earned and earned[-1].customer_id == "cust-x"

    def test_points_redeemed_carries_customer_id(self):
        account = _account("cust-y")
        account.earn_points(50)
        account.redeem_points(20)
        redeemed = [e for e in account._events if isinstance(e, PointsRedeemed)]
        assert redeemed and redeemed[-1].customer_id == "cust-y"
