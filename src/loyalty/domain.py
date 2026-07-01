"""Loyalty & Rewards bounded context.

A showcase domain that exercises Protean capabilities not naturally exercised by the
other seven ShopStream contexts: domain services (cross-aggregate), application services
(@use_case), custom repositories, custom field validators, HasOne/Reference associations,
cache-backed projections, a custom database model (hand-written SQLAlchemy for a projection),
a second persistence provider (a SQLite reporting store alongside the default Postgres),
non-Enum choices, event-sourced fact_events + snapshots, a second process-manager saga, and
pattern-B (direct-to-aggregate) subscribers.

Customers earn points on completed orders, hold a membership card, redeem points, and can
transfer points between accounts. Promotional campaigns are event-sourced.
"""

from protean.domain import Domain

from shared.enrichment import enrich_command, enrich_event

loyalty = Domain(name="loyalty")

# Message enrichment — adds request context (request_id, user_id) to all messages
loyalty.register_command_enricher(enrich_command)
loyalty.register_event_enricher(enrich_event)
