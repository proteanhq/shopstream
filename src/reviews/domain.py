"""Reviews & Ratings bounded context — Product Reviews, Ratings, and Moderation.

Handles review lifecycle (CQRS), voting, moderation, seller replies,
and rating aggregation. Integrates with Ordering domain for verified
purchase tracking via cross-domain events.
"""

import structlog
from protean.domain import Domain

from shared.enrichment import enrich_command, enrich_event

reviews = Domain(name="reviews")

# Message enrichment — adds request context (request_id, user_id) to all messages
reviews.register_command_enricher(enrich_command)
reviews.register_event_enricher(enrich_event)

logger = structlog.get_logger(__name__)
