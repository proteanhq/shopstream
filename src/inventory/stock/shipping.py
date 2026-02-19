"""Stock commitment (shipping) — command and handler."""

from protean import handle
from protean.fields import Identifier
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem


@inventory.command(part_of="InventoryItem")
class CommitStock:
    """Commit reserved stock when an order ships."""

    inventory_item_id = Identifier(required=True)
    reservation_id = Identifier(required=True)


@inventory.command_handler(part_of=InventoryItem)
class CommitStockHandler:
    @handle(CommitStock)
    def commit_stock(self, command):
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)
        item.commit_stock(reservation_id=command.reservation_id)
        repo.add(item)
