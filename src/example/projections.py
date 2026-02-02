"""Projector for updating ExampleSummary projection."""

from datetime import datetime

from protean import on
from protean.fields import DateTime, Identifier, Integer, String

from shopstream.domain import customer
from shopstream.example.events import ExampleActivated, ExampleArchived, ExampleCreated


@customer.projection
class ExampleSummary:
    """Read-optimized projection of Example aggregates."""

    example_id = Identifier(required=True)
    name = String(required=True, max_length=100)
    status = String(required=True)
    created_at = DateTime(required=True)
    updated_at = DateTime(required=True)

    # Computed/denormalized fields for fast querying
    days_since_creation = Integer()
    is_active = Integer()  # 1 or 0 for efficient filtering

    class Meta:
        # Customize projection behavior
        stream_name = "example"


@customer.projector(projector_for=ExampleSummary, aggregates=["Example"])
class ExampleProjector:
    """Update ExampleSummary projection based on Example events."""

    @on(ExampleCreated)
    def on_example_created(self, event: ExampleCreated) -> None:
        """Create a new projection when Example is created."""
        days_since = 0  # Just created
        is_active = 0  # Starts as DRAFT, not active

        projection = ExampleSummary(
            example_id=event.example_id,
            name=event.name,
            status="DRAFT",
            created_at=event.created_at,
            updated_at=event.created_at,
            days_since_creation=days_since,
            is_active=is_active,
        )

        repo = customer.repository_for(ExampleSummary)
        repo.add(projection)

    @on(ExampleActivated)
    def on_example_activated(self, event: ExampleActivated) -> None:
        """Update projection when Example is activated."""
        repo = customer.repository_for(ExampleSummary)
        projection = repo.get(event.example_id)

        if projection:
            projection.status = "ACTIVE"
            projection.is_active = 1
            projection.updated_at = event.activated_at

            # Recalculate days since creation
            days_since = (datetime.now() - projection.created_at).days
            projection.days_since_creation = days_since

            repo.add(projection)

    @on(ExampleArchived)
    def on_example_archived(self, event: ExampleArchived) -> None:
        """Update projection when Example is archived."""
        repo = customer.repository_for(ExampleSummary)
        projection = repo.get(event.example_id)

        if projection:
            projection.status = "ARCHIVED"
            projection.is_active = 0
            projection.updated_at = event.archived_at

            # Recalculate days since creation
            days_since = (datetime.now() - projection.created_at).days
            projection.days_since_creation = days_since

            repo.add(projection)
