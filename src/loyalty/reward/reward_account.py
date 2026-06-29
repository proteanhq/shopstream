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

    Codes are generated rather than left optional because Protean 0.16 runs per-field
    validators against ``None`` for optional fields (proteanhq/protean#1025), which would
    spuriously reject an unset validated field. Generating a valid code keeps the field
    ``required`` and always non-empty.
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
    def enroll(cls, customer_id, member_code=None):
        return cls(
            customer_id=customer_id,
            member_code=member_code or generate_member_code(),
        )

    def issue_card(self, card_number):
        if self.card is not None:
            raise ValidationError({"card": ["Account already has a membership card"]})
        self.card = MembershipCard(card_number=card_number, issued_on=date.today())
        self.touch()

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
        if amount <= 0:
            raise ValidationError({"amount": ["Amount must be positive"]})
        self.points_balance += amount
        self.lifetime_points += amount
        self._record_entry("earn", amount, reason)
        self.touch()

    def redeem_points(self, amount, reason="redemption"):
        if amount <= 0:
            raise ValidationError({"amount": ["Amount must be positive"]})
        # Over-redemption is caught by the balance_never_negative post-invariant.
        self.points_balance -= amount
        self._record_entry("redeem", amount, reason)
        self.touch()

    def close(self):
        self.status = AccountStatus.CLOSED.value
