"""Fulfillment bounded context — Warehouse Operations and Delivery Logistics.

Handles order fulfillment from warehouse picking through carrier handoff and
delivery confirmation. Uses CQRS because workflows are linear and external
carriers own tracking state.
"""

from protean.domain import Domain

from shared.enrichment import enrich_command, enrich_event

fulfillment = Domain(name="fulfillment")

# Message enrichment — adds request context (request_id, user_id) to all messages
fulfillment.register_command_enricher(enrich_command)
fulfillment.register_event_enricher(enrich_event)
