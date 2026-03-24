"""Domain initialization and configuration."""

from protean.domain import Domain

from shared.enrichment import enrich_command, enrich_event

# Domain Composition Root
identity = Domain(name="identity")

# Message enrichment — adds request context (request_id, user_id) to all messages
identity.register_command_enricher(enrich_command)
identity.register_event_enricher(enrich_event)
