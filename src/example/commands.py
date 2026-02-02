"""Commands for the Example aggregate."""

from protean.fields import Identifier, String

from shopstream.domain import customer


@customer.command(part_of="Example")
class CreateExample:
    """Command to create a new Example."""

    name = String(required=True, max_length=100)
    description = String(max_length=500)


@customer.command(part_of="Example")
class ActivateExample:
    """Command to activate an Example."""

    example_id = Identifier(required=True)


@customer.command(part_of="Example")
class ArchiveExample:
    """Command to archive an Example."""

    example_id = Identifier(required=True)
