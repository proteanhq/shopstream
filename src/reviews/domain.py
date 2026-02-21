"""Reviews & Ratings bounded context — Product Reviews, Ratings, and Moderation.

Handles review lifecycle (CQRS), voting, moderation, seller replies,
and rating aggregation. Integrates with Ordering domain for verified
purchase tracking via cross-domain events.
"""

import structlog
from protean.domain import Domain

reviews = Domain(name="reviews")

logger = structlog.get_logger(__name__)
