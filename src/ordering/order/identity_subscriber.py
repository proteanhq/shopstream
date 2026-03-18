"""Inbound cross-domain subscriber — Ordering reacts to Identity events.

Listens for AccountSuspended and AccountReactivated events from the Identity
domain's external bus to maintain a SuspendedAccounts projection. The
CreateOrder handler checks this projection before allowing order creation
for a customer.

Uses the subscriber (ACL) pattern: receives raw dict payloads from the global
broker, filters by event type, and translates into projection updates.
No dependency on shared event classes or register_external_event.
"""

import structlog
from protean.exceptions import ObjectNotFoundError
from protean.utils.globals import current_domain

from ordering.domain import ordering
from ordering.projections.suspended_accounts import SuspendedAccount

logger = structlog.get_logger(__name__)


@ordering.subscriber(broker="global", stream="identity::customer")
class IdentityEventsSubscriber:
    """Reacts to Identity domain events to track suspended accounts.

    ACL pattern: receives raw broker message dict, extracts event type from
    metadata.headers.type, and updates the SuspendedAccount projection.
    Ignores all event types not relevant to the Ordering domain.
    """

    def __call__(self, payload: dict) -> None:
        event_type = payload.get("metadata", {}).get("headers", {}).get("type", "")
        data = payload.get("data", {})

        if "AccountSuspended" in event_type:
            self._on_account_suspended(data)
        elif "AccountReactivated" in event_type:
            self._on_account_reactivated(data)

    def _on_account_suspended(self, data: dict) -> None:
        """Record that a customer account is suspended."""
        customer_id = str(data.get("customer_id", ""))
        reason = data.get("reason", "")
        suspended_at = data.get("suspended_at")

        logger.info(
            "Recording account suspension for order blocking",
            customer_id=customer_id,
            reason=reason,
        )
        repo = current_domain.repository_for(SuspendedAccount)
        try:
            repo.get(customer_id)
            # Already tracked
        except ObjectNotFoundError:
            repo.add(
                SuspendedAccount(
                    customer_id=customer_id,
                    reason=reason,
                    suspended_at=suspended_at,
                )
            )

    def _on_account_reactivated(self, data: dict) -> None:
        """Remove the suspension record when an account is reactivated."""
        customer_id = str(data.get("customer_id", ""))

        logger.info(
            "Removing account suspension record",
            customer_id=customer_id,
        )
        repo = current_domain.repository_for(SuspendedAccount)
        try:
            repo.get(customer_id)
            repo.query.filter(customer_id=customer_id).delete()
        except ObjectNotFoundError:
            pass  # Already removed or never existed
