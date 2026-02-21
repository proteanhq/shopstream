"""Fulfillment bounded context — Warehouse Operations and Delivery Logistics.

Handles order fulfillment from warehouse picking through carrier handoff and
delivery confirmation. Uses CQRS because workflows are linear and external
carriers own tracking state.
"""

from protean.domain import Domain

fulfillment = Domain(name="fulfillment")
