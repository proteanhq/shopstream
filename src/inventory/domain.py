"""Inventory bounded context — Stock Management and Warehouse Operations.

Handles inventory tracking (event-sourced), stock reservations, adjustments,
damage tracking, and warehouse management (CQRS).
"""

import structlog
from protean.domain import Domain

from shared.enrichment import enrich_command, enrich_event

inventory = Domain(name="inventory")

# Message enrichment — adds request context (request_id, user_id) to all messages
inventory.register_command_enricher(enrich_command)
inventory.register_event_enricher(enrich_event)

logger = structlog.get_logger(__name__)
