"""Commands and handler for the Redemption aggregate.

`RequestRedemption` kicks off the flow (typically from the API); the remaining commands are
dispatched by the `RedemptionSaga` as it advances or compensates the redemption. The
`IssueRedemptionVoucher` handler is where the external voucher port is consulted — success
issues the voucher, failure records the failure (which the saga compensates).
"""

from protean import handle
from protean.fields import Identifier, Integer, String
from protean.utils.globals import current_domain

from loyalty.domain import loyalty
from loyalty.redemption.redemption import Redemption
from loyalty.redemption.voucher import VoucherUnavailable, issue_voucher_code


@loyalty.command(part_of="Redemption")
class RequestRedemption:
    account_id: str = String(required=True, max_length=255)
    points: int = Integer(required=True)
    reward_code: str = String(required=True, max_length=40)


@loyalty.command(part_of="Redemption")
class ReserveRedemptionPoints:
    redemption_id: str = Identifier(required=True)


@loyalty.command(part_of="Redemption")
class IssueRedemptionVoucher:
    redemption_id: str = Identifier(required=True)


@loyalty.command(part_of="Redemption")
class CompleteRedemption:
    redemption_id: str = Identifier(required=True)


@loyalty.command(part_of="Redemption")
class CompensateRedemption:
    redemption_id: str = Identifier(required=True)
    refunded_points: int = Integer(required=True)
    reason: str = String(max_length=255, default="voucher unavailable")


@loyalty.command_handler(part_of=Redemption)
class RedemptionHandler:
    @handle(RequestRedemption)
    def request(self, command: RequestRedemption) -> str:
        redemption = Redemption.request(
            account_id=command.account_id,
            points=command.points,
            reward_code=command.reward_code,
        )
        current_domain.repository_for(Redemption).add(redemption)
        return redemption.id

    @handle(ReserveRedemptionPoints)
    def reserve(self, command: ReserveRedemptionPoints) -> None:
        repo = current_domain.repository_for(Redemption)
        redemption = repo.get(command.redemption_id)
        redemption.reserve_points()
        repo.add(redemption)

    @handle(IssueRedemptionVoucher)
    def issue(self, command: IssueRedemptionVoucher) -> None:
        repo = current_domain.repository_for(Redemption)
        redemption = repo.get(command.redemption_id)
        try:
            voucher_code = issue_voucher_code(redemption.reward_code)
            redemption.issue_voucher(voucher_code)
        except VoucherUnavailable as exc:
            redemption.fail_voucher(str(exc))
        repo.add(redemption)

    @handle(CompleteRedemption)
    def complete(self, command: CompleteRedemption) -> None:
        repo = current_domain.repository_for(Redemption)
        redemption = repo.get(command.redemption_id)
        redemption.complete()
        repo.add(redemption)

    @handle(CompensateRedemption)
    def compensate(self, command: CompensateRedemption) -> None:
        repo = current_domain.repository_for(Redemption)
        redemption = repo.get(command.redemption_id)
        redemption.compensate(command.refunded_points, command.reason)
        repo.add(redemption)
