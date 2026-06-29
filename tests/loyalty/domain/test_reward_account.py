"""Domain tests for the RewardAccount aggregate (pure behavior, no DB)."""

import pytest
from protean.exceptions import ValidationError

from loyalty.reward.reward_account import AccountStatus, RewardAccount


class TestRewardAccountBehavior:
    def test_enroll_creates_active_bronze_account(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        assert account.customer_id == "cust-1"
        assert account.status == AccountStatus.ACTIVE.value
        assert account.tier == "bronze"
        assert account.points_balance == 0
        assert account.lifetime_points == 0

    def test_inherits_audit_fields_from_abstract_base(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        assert account.created_at is not None
        assert account.updated_at is not None

    def test_earn_points_increases_balance_and_records_ledger_entry(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        account.earn_points(150)
        assert account.points_balance == 150
        assert account.lifetime_points == 150
        assert len(account.entries) == 1
        assert account.entries[0].entry_type == "earn"
        assert account.entries[0].balance_after == 150

    def test_redeem_points_decreases_balance_only(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        account.earn_points(150)
        account.redeem_points(40)
        assert account.points_balance == 110
        assert account.lifetime_points == 150  # lifetime is not reduced
        assert {e.entry_type for e in account.entries} == {"earn", "redeem"}

    def test_issue_card_attaches_hasone_membership_card(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        account.issue_card(card_number="LOY-0001")
        assert account.card is not None
        assert account.card.card_number == "LOY-0001"
        assert account.card.status == "active"


class TestRewardAccountRules:
    def test_redeem_more_than_balance_is_rejected(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        account.earn_points(30)
        with pytest.raises(ValidationError, match="cannot be negative"):
            account.redeem_points(50)

    def test_invalid_tier_choice_is_rejected(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        with pytest.raises(ValidationError):
            account.tier = "diamond"  # not in the non-Enum choices list

    def test_cannot_issue_two_cards(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        account.issue_card(card_number="LOY-0001")
        with pytest.raises(ValidationError, match="already has a membership card"):
            account.issue_card(card_number="LOY-0002")

    def test_closed_account_is_immutable_via_pre_invariant(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        account.earn_points(100)
        account.close()
        assert account.status == AccountStatus.CLOSED.value
        with pytest.raises(ValidationError, match="closed reward account"):
            account.earn_points(10)


class TestMemberCodeValidators:
    def test_valid_member_code_accepted(self):
        account = RewardAccount.enroll(customer_id="cust-1", member_code="WELCOME10")
        assert account.member_code == "WELCOME10"

    def test_auto_generated_member_code_is_valid(self):
        account = RewardAccount.enroll(customer_id="cust-1")
        assert 6 <= len(account.member_code) <= 12
        assert account.member_code.isupper()

    def test_regex_validator_rejects_lowercase(self):
        with pytest.raises(ValidationError):
            RewardAccount.enroll(customer_id="cust-1", member_code="welcome10")

    def test_custom_validator_rejects_triple_repeat(self):
        # Passes the regex (uppercase alnum) but trips the custom NoTripleRepeat rule.
        with pytest.raises(ValidationError, match="3 or more times"):
            RewardAccount.enroll(customer_id="cust-1", member_code="AAAB12")
