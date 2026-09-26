"""Logging setup for the API process.

Kept out of `app.py` so tests can call it without importing `app`, which
initialises all nine domains.
"""

from protean import Domain

from identity.domain import identity


def configure_api_logging(domain: Domain = identity) -> None:
    """Set up the API process's logging from `domain`'s [logging] config.

    The level comes from identity's [logging] table in domain.toml, or
    Protean's default when the table is absent. PROTEAN_LOG_LEVEL takes
    precedence over it.
    """
    domain.configure_logging()
