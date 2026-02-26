"""Payments & Billing bounded context — Payment Processing and Invoicing.

Handles payment lifecycle (event-sourced), refunds, invoice generation (CQRS),
and gateway abstraction for payment processing.
"""

import structlog
from protean.domain import Domain

from shared.enrichment import enrich_command, enrich_event

payments = Domain(name="payments")

# Message enrichment — adds request context (request_id, user_id) to all messages
payments.register_command_enricher(enrich_command)
payments.register_event_enricher(enrich_event)

logger = structlog.get_logger(__name__)
