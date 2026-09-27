"""Application tests for the `Auditable` audit fields on RewardAccount.

The framework stamps `created_at` / `updated_at` from the loyalty domain clock on
save, and the `stamp_actor` aggregate enricher fills `created_by` / `updated_by` from
`g.actor_id`, falling back to `"system"`. The per-test domain context gives each
test a fresh `g`, so an actor bound here does not leak into the next test.
"""

from datetime import UTC, datetime, timedelta

from protean import current_domain, g

from loyalty.domain import loyalty
from loyalty.redemption.redemption import Redemption
from loyalty.reward.enrollment import EnrollRewardAccount
from loyalty.reward.points import EarnPoints
from loyalty.reward.reward_account import RewardAccount

T1 = datetime(2030, 6, 1, 12, 0, tzinfo=UTC)
T2 = T1 + timedelta(hours=3)


def _enroll(customer_id="cust-audit"):
    return current_domain.process(EnrollRewardAccount(customer_id=customer_id), asynchronous=False)


def _load(account_id):
    return current_domain.repository_for(RewardAccount).get(account_id)


class TestAuditTimestamps:
    def test_first_save_stamps_both_timestamps_from_the_clock(self, frozen_clock):
        frozen_clock(loyalty, T1)

        account = _load(_enroll())

        assert account.created_at.astimezone(UTC) == T1
        assert account.updated_at.astimezone(UTC) == T1

    def test_later_save_moves_updated_at_and_keeps_created_at(self, frozen_clock):
        clock = frozen_clock(loyalty, T1)
        account_id = _enroll()

        clock.set(T2)
        current_domain.process(EarnPoints(account_id=account_id, amount=50), asynchronous=False)

        account = _load(account_id)
        assert account.points_balance == 50
        assert account.created_at.astimezone(UTC) == T1
        assert account.updated_at.astimezone(UTC) == T2

    def test_direct_repository_add_is_stamped(self, frozen_clock):
        frozen_clock(loyalty, T1)
        account = RewardAccount.enroll(customer_id="cust-audit-direct")
        assert account.created_at is None

        current_domain.repository_for(RewardAccount).add(account)

        stored = _load(account.id)
        assert stored.created_at.astimezone(UTC) == T1
        assert stored.updated_at.astimezone(UTC) == T1
        assert stored.created_by == "system"
        assert stored.updated_by == "system"


class TestAuditActor:
    def test_save_without_an_actor_records_system(self):
        account = _load(_enroll())

        assert account.created_by == "system"
        assert account.updated_by == "system"

    def test_save_records_the_bound_actor(self):
        g.actor_id = "alice"
        account = _load(_enroll())

        assert account.created_by == "alice"
        assert account.updated_by == "alice"

    def test_later_actor_changes_updated_by_only(self):
        g.actor_id = "alice"
        account_id = _enroll()
        g.actor_id = "bob"
        current_domain.process(EarnPoints(account_id=account_id, amount=10), asynchronous=False)

        account = _load(account_id)
        assert account.created_by == "alice"
        assert account.updated_by == "bob"

    def test_aggregate_without_audit_fields_saves_untouched(self):
        g.actor_id = "alice"
        redemption = Redemption(account_id="acc-audit", points=100, reward_code="GIFT10")
        current_domain.repository_for(Redemption).add(redemption)

        stored = current_domain.repository_for(Redemption).get(redemption.id)
        assert stored.points == 100
        assert not hasattr(stored, "created_by")
        assert not hasattr(stored, "updated_by")
