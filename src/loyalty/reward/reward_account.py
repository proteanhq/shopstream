"""RewardAccount aggregate — a customer's loyalty points account.

Exercises several Protean capabilities not used elsewhere in ShopStream:
  * an **abstract base aggregate** (`Auditable`) shared via inheritance,
  * a **non-Enum `choices`** list on `tier`,
  * an **`@invariant.pre`** state guard (closed accounts are immutable) alongside an
    **`@invariant.post`** business rule (balance never negative),
  * a **`HasOne`** association (the membership card),
  * **composed custom field validators** (built-in `RegexValidator` + a custom callable
    class) on `member_code`.
"""

import secrets
import string
from datetime import UTC, date, datetime
from enum import Enum

from protean import invariant
from protean.exceptions import ValidationError
from protean.fields import Date, DateTime, HasMany, HasOne, Integer, Reference, String
from protean.fields.validators import RegexValidator

from loyalty.domain import loyalty

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_member_code(length=8):
    """Generate a valid member code (uppercase alphanumeric, no 3-in-a-row repeat).

    Every account is assigned its own member code, so ``member_code`` is required and
    always generated when not supplied. (The optional, who-referred-me ``referral_code``
    field exercises the optional-field + validators path.)
    """
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
        if not any(code[i] == code[i + 1] == code[i + 2] for i in range(length - 2)):
            return code


@loyalty.aggregate(abstract=True)
class Auditable:
    """Abstract base contributing audit timestamps to concrete aggregates."""

    created_at = DateTime(default=lambda: datetime.now(UTC))
    updated_at = DateTime(default=lambda: datetime.now(UTC))

    def touch(self):
        self.updated_at = datetime.now(UTC)


class AccountStatus(Enum):
    ACTIVE = "Active"
    FROZEN = "Frozen"
    CLOSED = "Closed"


# Tier names are a plain list (non-Enum) `choices` — distinct from the Status/Enum
# choices used elsewhere in ShopStream.
TIERS = ["bronze", "silver", "gold", "platinum"]

# Lifetime-points thresholds that unlock each tier. Earning points can promote an account
# (highest threshold reached wins); tiers never downgrade on earn.
TIER_THRESHOLDS = [
    ("platinum", 20_000),
    ("gold", 5_000),
    ("silver", 1_000),
    ("bronze", 0),
]


def tier_for_lifetime_points(lifetime_points):
    """Return the highest tier whose threshold the lifetime points have reached."""
    for tier, threshold in TIER_THRESHOLDS:
        if lifetime_points >= threshold:
            return tier
    return "bronze"


class NoTripleRepeatValidator:
    """Custom field validator: reject codes that repeat one character 3+ times in a row.

    Demonstrates a user-defined callable validator composed alongside the built-in
    RegexValidator on a single field.
    """

    message = "Member code cannot repeat a character 3 or more times consecutively"

    def __call__(self, value):
        if value is None:
            return
        text = str(value)
        for i in range(len(text) - 2):
            if text[i] == text[i + 1] == text[i + 2]:
                raise ValidationError(self.message)


@loyalty.entity(part_of="RewardAccount")
class MembershipCard:
    """The physical/virtual loyalty card — a 1:1 (HasOne) child of the account."""

    card_number = String(required=True, max_length=20)
    issued_on = Date(required=True)
    status = String(choices=["active", "suspended", "expired"], default="active")


@loyalty.entity(part_of="RewardAccount")
class PointsLedgerEntry:
    """An append-only points movement — a 1:N (HasMany) child of the account.

    Declares the parent link explicitly via `Reference` (rather than relying on the
    implicit reference HasMany would auto-create) to exercise the Reference field.
    """

    reward_account = Reference("RewardAccount")
    entry_type = String(
        choices=["earn", "redeem", "transfer_in", "transfer_out", "adjust"],
        required=True,
    )
    amount = Integer(required=True)
    balance_after = Integer(required=True)
    reason = String(max_length=255)
    occurred_at = DateTime(required=True)


@loyalty.aggregate
class RewardAccount(Auditable):
    customer_id = String(required=True, max_length=255)
    status = String(choices=AccountStatus, default=AccountStatus.ACTIVE.value)
    tier = String(choices=TIERS, default="bronze")
    points_balance = Integer(default=0)
    lifetime_points = Integer(default=0)
    membership_since = Date(default=date.today)
    # member_code carries composed custom validators (built-in RegexValidator + a custom
    # callable). It is required (always generated) — see generate_member_code / #1025.
    member_code = String(
        required=True,
        max_length=12,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9]{6,12}$",
                message="Member code must be 6-12 uppercase letters/digits",
            ),
            NoTripleRepeatValidator(),
        ],
    )
    # Optional validated field — exercises validators on an optional field (validators are
    # skipped when the value is None; proteanhq/protean#1025, fixed on main).
    referral_code = String(
        max_length=12,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9]{6,12}$",
                message="Referral code must be 6-12 uppercase letters/digits",
            )
        ],
    )
    card = HasOne("MembershipCard")
    entries = HasMany("PointsLedgerEntry")

    @invariant.post
    def balance_never_negative(self):
        if self.points_balance < 0:
            raise ValidationError({"points_balance": ["Points balance cannot be negative"]})

    @invariant.pre
    def closed_accounts_are_immutable(self):
        # Runs before each field assignment, against the pre-mutation state — so the
        # close() transition itself (Active/Frozen -> Closed) passes, but any later
        # mutation of an already-closed account is rejected.
        if self.status == AccountStatus.CLOSED.value:
            raise ValidationError({"_account": ["A closed reward account cannot be modified"]})

    @classmethod
    def enroll(cls, customer_id, member_code=None, referral_code=None):
        from loyalty.reward.events import RewardAccountEnrolled

        account = cls(
            customer_id=customer_id,
            member_code=member_code or generate_member_code(),
            referral_code=referral_code,
        )
        account.raise_(
            RewardAccountEnrolled(
                account_id=account.id,
                customer_id=account.customer_id,
                member_code=account.member_code,
                tier=account.tier,
                enrolled_at=datetime.now(UTC),
            )
        )
        return account

    def issue_card(self, card_number):
        from loyalty.reward.events import MembershipCardIssued

        if self.card is not None:
            raise ValidationError({"card": ["Account already has a membership card"]})
        issued_on = date.today()
        self.card = MembershipCard(card_number=card_number, issued_on=issued_on)
        self.touch()
        self.raise_(
            MembershipCardIssued(
                account_id=self.id,
                card_number=card_number,
                issued_on=issued_on.isoformat(),
            )
        )

    def _record_entry(self, entry_type, amount, reason=None):
        self.add_entries(
            PointsLedgerEntry(
                entry_type=entry_type,
                amount=amount,
                balance_after=self.points_balance,
                reason=reason,
                occurred_at=datetime.now(UTC),
            )
        )

    def earn_points(self, amount, reason="order"):
        from loyalty.reward.events import PointsEarned

        if amount <= 0:
            raise ValidationError({"amount": ["Amount must be positive"]})
        self.points_balance += amount
        self.lifetime_points += amount
        self._record_entry("earn", amount, reason)
        self.touch()
        self.raise_(
            PointsEarned(
                account_id=self.id,
                customer_id=self.customer_id,
                amount=amount,
                balance_after=self.points_balance,
                reason=reason,
                occurred_at=datetime.now(UTC),
            )
        )
        self._maybe_upgrade_tier()

    def _maybe_upgrade_tier(self):
        """Promote the account if lifetime points have crossed a tier threshold."""
        from loyalty.reward.events import TierUpgraded

        earned_tier = tier_for_lifetime_points(self.lifetime_points)
        if TIERS.index(earned_tier) <= TIERS.index(self.tier):
            return  # already at or above the earned tier — never downgrade
        old_tier = self.tier
        self.tier = earned_tier
        self.touch()
        self.raise_(
            TierUpgraded(
                account_id=self.id,
                customer_id=self.customer_id,
                old_tier=old_tier,
                new_tier=earned_tier,
                lifetime_points=self.lifetime_points,
                occurred_at=datetime.now(UTC),
            )
        )

    def redeem_points(self, amount, reason="redemption"):
        from loyalty.reward.events import PointsRedeemed

        if amount <= 0:
            raise ValidationError({"amount": ["Amount must be positive"]})
        # Over-redemption is caught by the balance_never_negative post-invariant.
        self.points_balance -= amount
        self._record_entry("redeem", amount, reason)
        self.touch()
        self.raise_(
            PointsRedeemed(
                account_id=self.id,
                customer_id=self.customer_id,
                amount=amount,
                balance_after=self.points_balance,
                reason=reason,
                occurred_at=datetime.now(UTC),
            )
        )

    def claw_back_points(self, amount, reason="refund_clawback"):
        """Reverse points after a refund — deduct up to the available balance.

        Unlike redemption, a clawback is **clamped** to the current balance (it never drives the
        balance negative or raises): a refunded order should not push an account into debt. Records
        an ``adjust`` ledger entry (the audit/adjustment movement type) and reuses ``PointsRedeemed``
        so downstream consumers treat it like any other deduction. A no-op when there is nothing to
        claw back, which makes at-least-once redelivery safe-ish.
        """
        from loyalty.reward.events import PointsRedeemed

        if amount <= 0:
            return
        clawed = min(amount, self.points_balance)
        if clawed == 0:
            return
        self.points_balance -= clawed
        self._record_entry("adjust", clawed, reason)
        self.touch()
        self.raise_(
            PointsRedeemed(
                account_id=self.id,
                customer_id=self.customer_id,
                amount=clawed,
                balance_after=self.points_balance,
                reason=reason,
                occurred_at=datetime.now(UTC),
            )
        )

    def close(self):
        from loyalty.reward.events import RewardAccountClosed

        self.status = AccountStatus.CLOSED.value
        self.raise_(RewardAccountClosed(account_id=self.id, closed_at=datetime.now(UTC)))
