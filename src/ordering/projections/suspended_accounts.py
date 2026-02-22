"""Suspended accounts projection — tracks customers blocked from ordering.

Populated by the Identity → Ordering cross-domain event handler when
AccountSuspended/AccountReactivated events are received. The CreateOrder
handler queries this projection to block orders from suspended customers.
"""

from protean.fields import DateTime, Identifier, String

from ordering.domain import ordering


@ordering.projection
class SuspendedAccount:
    customer_id = Identifier(identifier=True, required=True)
    reason = String()
    suspended_at = DateTime()
