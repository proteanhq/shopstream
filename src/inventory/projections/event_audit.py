"""Event audit trail — a domain-wide read model capturing *every* InventoryItem event.

Unlike StockMovementLog (a projector with a hand-written ``@on`` method per event type
that shapes a domain-specific description), this audit trail is populated by an
**in-domain event handler** using the ``@handle("$any")`` wildcard. A single handler
method records a uniform audit row for any event raised by the InventoryItem
aggregate — including events added in the future without touching this file.

It captures the causation/correlation chain from event metadata, making it a handy
observability surface for tracing how one command fanned out into events.

Two Protean capabilities are exercised here:
  * an in-domain ``@<domain>.event_handler`` (the only other one in ShopStream lives in
    the notifications domain), and
  * the ``@handle("$any")`` wildcard target.

Note: the ``$any`` wildcard is supported by event handlers (and command handlers) but
NOT by projectors, which require every handler to target a concrete event class — hence
this is an ``@event_handler`` writing the read model directly rather than an
``@projector``.

The wildcard handler also runs under ``event_processing="sync"``;
``tests/inventory/integration/test_event_audit_projection.py`` guards that.
"""

import uuid
from datetime import UTC, datetime

from protean.core.event import BaseEvent
from protean.fields import DateTime, Identifier, String
from protean.utils.globals import current_domain
from protean.utils.mixins import handle

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem


@inventory.projection(externally_populated=True)
class EventAudit:
    audit_id: str = Identifier(identifier=True, required=True)
    inventory_item_id: str | None = Identifier()
    event_type: str = String(required=True)  # short class name, e.g. "StockReserved"
    qualified_type: str | None = String()  # metadata type, e.g. "inventory.StockReserved.v1"
    stream: str | None = String()
    correlation_id: str | None = String()
    causation_id: str | None = String()
    recorded_at: datetime = DateTime(required=True)


@inventory.event_handler(part_of=InventoryItem)
class EventAuditHandler:
    """Records a uniform audit row for every InventoryItem event via the wildcard."""

    @handle("$any")
    def on_any_event(self, event: BaseEvent) -> None:
        metadata = getattr(event, "_metadata", None)
        headers = getattr(metadata, "headers", None)
        domain_meta = getattr(metadata, "domain", None)

        current_domain.repository_for(EventAudit).add(
            EventAudit(
                audit_id=str(uuid.uuid4()),
                inventory_item_id=str(getattr(event, "inventory_item_id", "") or ""),
                event_type=type(event).__name__,
                qualified_type=getattr(headers, "type", None),
                stream=getattr(headers, "stream", None),
                correlation_id=getattr(domain_meta, "correlation_id", None),
                causation_id=getattr(domain_meta, "causation_id", None),
                recorded_at=getattr(headers, "time", None) or datetime.now(UTC),
            )
        )
