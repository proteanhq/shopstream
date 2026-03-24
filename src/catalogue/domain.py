"""Domain initialization and configuration."""

from protean.domain import Domain

from shared.enrichment import enrich_command, enrich_event

# Domain Composition Root
catalogue = Domain(name="catalogue")

# Message enrichment — adds request context (request_id, user_id) to all messages
catalogue.register_command_enricher(enrich_command)
catalogue.register_event_enricher(enrich_event)
