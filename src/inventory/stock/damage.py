"""Damage tracking — commands and handler."""

from protean import handle
from protean.fields import Identifier, Integer, String
from protean.utils.globals import current_domain

from inventory.domain import inventory
from inventory.stock.stock import InventoryItem


@inventory.command(part_of="InventoryItem")
class MarkDamaged:
    """Flag stock as damaged."""

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    reason = String(required=True)


@inventory.command(part_of="InventoryItem")
class WriteOffDamaged:
    """Write off damaged stock."""

    inventory_item_id = Identifier(required=True)
    quantity = Integer(required=True)
    approved_by = String(required=True)


@inventory.command_handler(part_of=InventoryItem)
class DamageHandler:
    @handle(MarkDamaged)
    def mark_damaged(self, command):
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)
        item.mark_damaged(
            quantity=command.quantity,
            reason=command.reason,
        )
        repo.add(item)

    @handle(WriteOffDamaged)
    def write_off_damaged(self, command):
        repo = current_domain.repository_for(InventoryItem)
        item = repo.get(command.inventory_item_id)
        item.write_off_damaged(
            quantity=command.quantity,
            approved_by=command.approved_by,
        )
        repo.add(item)
