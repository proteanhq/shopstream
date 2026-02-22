"""Notifications bounded context — Cross-domain event consumer for multi-channel dispatch.

Consumes events from all other domains (Identity, Ordering, Payments,
Fulfillment, Inventory, Reviews) and dispatches notifications via Email,
SMS, Push, and Slack channels. Manages customer notification preferences
and tracks delivery status for audit and retry.
"""

import structlog
from protean.domain import Domain

notifications = Domain(name="notifications")

logger = structlog.get_logger(__name__)
