"""Inventory bounded context — Stock Management and Warehouse Operations.

Handles inventory tracking (event-sourced), stock reservations, adjustments,
damage tracking, and warehouse management (CQRS).
"""

import structlog
from protean.domain import Domain

inventory = Domain(name="inventory")

logger = structlog.get_logger(__name__)
