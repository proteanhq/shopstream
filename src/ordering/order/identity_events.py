"""Inbound cross-domain event handler — Ordering reacts to Identity events.

Listens for AccountSuspended and AccountReactivated events from the Identity
domain to maintain a SuspendedAccounts projection. The CreateOrder handler
checks this projection before allowing order creation for a customer.

Cross-domain events are imported from shared.events.identity and registered
as external events via ordering.register_external_event().
"""

import structlog
from protean.exceptions import ObjectNotFoundError
from protean.utils.globals import current_domain
from protean.utils.mixins import handle
from shared.events.identity import AccountReactivated, AccountSuspended

from ordering.domain import ordering
from ordering.order.order import Order
from ordering.projections.suspended_accounts import SuspendedAccount

logger = structlog.get_logger(__name__)

# Register external events so Protean can deserialize them
ordering.register_external_event(AccountSuspended, "Identity.AccountSuspended.v1")
ordering.register_external_event(AccountReactivated, "Identity.AccountReactivated.v1")


@ordering.event_handler(part_of=Order, stream_category="identity::customer")
class IdentityOrderEventHandler:
    """Reacts to Identity domain events to track suspended accounts."""

    @handle(AccountSuspended)
    def on_account_suspended(self, event: AccountSuspended) -> None:
        """Record that a customer account is suspended."""
        logger.info(
            "Recording account suspension for order blocking",
            customer_id=str(event.customer_id),
            reason=event.reason,
        )
        repo = current_domain.repository_for(SuspendedAccount)
        try:
            repo.get(str(event.customer_id))
            # Already tracked
        except ObjectNotFoundError:
            repo.add(
                SuspendedAccount(
                    customer_id=str(event.customer_id),
                    reason=event.reason,
                    suspended_at=event.suspended_at,
                )
            )

    @handle(AccountReactivated)
    def on_account_reactivated(self, event: AccountReactivated) -> None:
        """Remove the suspension record when an account is reactivated."""
        logger.info(
            "Removing account suspension record",
            customer_id=str(event.customer_id),
        )
        repo = current_domain.repository_for(SuspendedAccount)
        try:
            record = repo.get(str(event.customer_id))
            repo._dao.delete(record)
        except ObjectNotFoundError:
            pass  # Already removed or never existed
