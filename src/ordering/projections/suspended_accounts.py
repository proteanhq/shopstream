"""Suspended accounts projection — tracks customers blocked from ordering.

Populated by the Identity → Ordering cross-domain event handler when
AccountSuspended/AccountReactivated events are received. The CreateOrder
handler queries this projection to block orders from suspended customers.
"""

from datetime import datetime

from protean.fields import DateTime, Identifier, String

from ordering.domain import ordering


@ordering.projection(externally_populated=True)
class SuspendedAccount:
    customer_id: str = Identifier(identifier=True, required=True)
    reason: str | None = String()
    suspended_at: datetime | None = DateTime()
