"""Logging configuration for ShopStream Catalogue domain.

Delegates to Protean's built-in structured logging.
"""

from protean.utils.logging import (
    add_context,
    clear_context,
    configure_for_testing,
    configure_logging,
    get_logger,
    log_method_call,
)

__all__ = [
    "add_context",
    "clear_context",
    "configure_for_testing",
    "configure_logging",
    "get_logger",
    "log_method_call",
]
