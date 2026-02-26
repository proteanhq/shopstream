"""Notifications bounded context — Cross-domain event consumer for multi-channel dispatch.

Consumes events from all other domains (Identity, Ordering, Payments,
Fulfillment, Inventory, Reviews) and dispatches notifications via Email,
SMS, Push, and Slack channels. Manages customer notification preferences
and tracks delivery status for audit and retry.
"""

import structlog
from protean.domain import Domain

from shared.enrichment import enrich_command, enrich_event

notifications = Domain(name="notifications")

# Message enrichment — adds request context (request_id, user_id) to all messages
notifications.register_command_enricher(enrich_command)
notifications.register_event_enricher(enrich_event)

logger = structlog.get_logger(__name__)
