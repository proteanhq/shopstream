"""Shared message enrichment — adds request context to all commands and events.

Enrichers read from Protean's thread-local `g` object (populated by
DomainContextMiddleware and UserContextMiddleware) and return metadata
extensions for distributed tracing and audit. When no request context is
present (e.g. background engine processing), enrichers return an empty
dict (no-op).
"""

from protean import g


def enrich_command(_command):
    """Add request context to command metadata.extensions."""
    extensions = {}
    if hasattr(g, "request_correlation_id") and g.request_correlation_id:
        extensions["request_id"] = g.request_correlation_id
    if hasattr(g, "user_id") and g.user_id:
        extensions["user_id"] = g.user_id
    return extensions


def enrich_event(_event, _aggregate):
    """Add request context to event metadata.extensions."""
    extensions = {}
    if hasattr(g, "request_correlation_id") and g.request_correlation_id:
        extensions["request_id"] = g.request_correlation_id
    if hasattr(g, "user_id") and g.user_id:
        extensions["user_id"] = g.user_id
    return extensions
