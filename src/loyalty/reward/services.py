"""LoyaltyService — an application service (DDD orchestration, non-CQRS).

Application services are invoked directly (not via domain.process) and return values
synchronously. The @use_case decorator wraps each method in a UnitOfWork. This service
orchestrates the TransferPoints domain service across two aggregates and persists both
in a single transaction.
"""

from protean import use_case
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.reward.reward_account import RewardAccount
from loyalty.reward.transfer import TransferPoints


@loyalty.application_service(part_of=RewardAccount)
class LoyaltyService:
    @use_case
    def transfer_points(self, source_id, target_id, amount):
        repo = current_domain.repository_for(RewardAccount)
        source = repo.get(source_id)
        target = repo.get(target_id)

        TransferPoints(source, target)(amount)

        repo.add(source)
        repo.add(target)
        return {
            "source_balance": source.points_balance,
            "target_balance": target.points_balance,
        }
