"""Repository for the Example aggregate."""

from shopstream.domain import customer

from .aggregate import Example


@customer.repository(part_of=Example)
class ExampleRepository:
    """Repository for Example aggregate.

    The base repository provides standard CRUD operations.
    Add custom query methods here as needed.
    """

    def find_by_name(self, name: str) -> Example | None:
        """Find an Example by name."""
        return self._dao.find_by(name=name).first

    def find_active(self) -> list[Example]:
        """Find all active Examples."""
        return self._dao.filter(status="ACTIVE").all()

    def find_by_status(self, status: str) -> list[Example]:
        """Find Examples by status."""
        return self._dao.filter(status=status).all()
