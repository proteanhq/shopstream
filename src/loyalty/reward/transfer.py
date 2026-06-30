"""TransferPoints — a domain service moving points between two reward accounts.

Domain services encapsulate business logic that spans more than one aggregate. This
callable service operates on two RewardAccount aggregates and enforces cross-aggregate
invariants: both accounts must be active (pre) and the total points across both accounts
must be conserved by the transfer (post).
"""

from protean import invariant
from protean.exceptions import ValidationError

from loyalty.domain import loyalty
from loyalty.reward.reward_account import AccountStatus, RewardAccount


@loyalty.domain_service(part_of=[RewardAccount, RewardAccount])
class TransferPoints:
    def __init__(self, source, target):
        super().__init__(source, target)
        # Underscore-prefixed so the invariant wrapper does not treat them as
        # public service methods.
        self._source = source
        self._target = target
        self._total_before = source.points_balance + target.points_balance

    @invariant.pre
    def both_accounts_must_be_active(self):
        for account in (self._source, self._target):
            if account.status != AccountStatus.ACTIVE.value:
                raise ValidationError({"_service": ["Both accounts must be active to transfer points"]})

    @invariant.post
    def points_are_conserved(self):
        total_after = self._source.points_balance + self._target.points_balance
        if total_after != self._total_before:
            raise ValidationError({"_service": ["Points must be conserved across a transfer"]})

    def __call__(self, amount):
        if amount <= 0:
            raise ValidationError({"amount": ["Transfer amount must be positive"]})
        # Over-transfer is caught by RewardAccount's balance_never_negative invariant.
        self._source.redeem_points(amount, reason="transfer_out")
        self._target.earn_points(amount, reason="transfer_in")
