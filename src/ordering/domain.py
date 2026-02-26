"""Ordering bounded context — Order Management and Shopping Cart.

Handles order lifecycle (event-sourced), shopping cart management (CQRS),
and the checkout flow that converts carts to orders.
"""

import structlog
from protean.domain import Domain

from shared.enrichment import enrich_command, enrich_event

ordering = Domain(name="ordering")

# Message enrichment — adds request context (request_id, user_id) to all messages
ordering.register_command_enricher(enrich_command)
ordering.register_event_enricher(enrich_event)

logger = structlog.get_logger(__name__)
