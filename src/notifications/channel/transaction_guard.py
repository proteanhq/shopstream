"""Guard that a channel send never runs inside an open database transaction."""

from protean.utils.globals import current_uow


class SendInsideTransactionError(RuntimeError):
    """A channel adapter was called while a unit of work held a database session."""


def open_session_providers() -> list[str]:
    """Return the providers the active unit of work has opened a session on.

    Every ``@handle`` method runs inside a ``UnitOfWork``, so ``current_uow``
    is set during any handler. The unit of work opens its session, and on
    Postgres its transaction and pooled connection, only at the first
    repository access. An empty list means no transaction is open.
    Protean has no public accessor for this, so this reads the private
    ``_sessions`` map, the same way Protean's own tests do.
    """
    if not current_uow:
        return []
    return sorted(current_uow._sessions)


def ensure_no_open_transaction(channel: str) -> None:
    """Raise if the active unit of work has opened a database session."""
    providers = open_session_providers()
    if providers:
        raise SendInsideTransactionError(f"{channel} send ran inside an open transaction (providers: {providers})")
