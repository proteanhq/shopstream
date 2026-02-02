"""Events emitted by the Example aggregate."""

from datetime import datetime

from protean.fields import DateTime, Identifier, String

from shopstream.domain import customer


@customer.event(part_of="Example")
class ExampleCreated:
    """Event emitted when an Example is created."""

    example_id = Identifier(required=True)
    name = String(required=True, max_length=100)
    description = String(max_length=500)
    created_at = DateTime(required=True)


@customer.event(part_of="Example")
class ExampleActivated:
    """Event emitted when an Example is activated."""

    example_id = Identifier(required=True)
    activated_at = DateTime(default=lambda: datetime.now())


@customer.event(part_of="Example")
class ExampleArchived:
    """Event emitted when an Example is archived."""

    example_id = Identifier(required=True)
    archived_at = DateTime(default=lambda: datetime.now())
