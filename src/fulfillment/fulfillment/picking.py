"""Fulfillment picking — commands and handler.

Handles the warehouse picking phase: assigning a picker, recording individual
item picks, and completing the pick list.
"""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.command(part_of="Fulfillment")
class AssignPicker:
    """Assign a warehouse picker to begin the picking process."""

    fulfillment_id = Identifier(required=True)
    picker_name = String(required=True, max_length=100)


@fulfillment.command(part_of="Fulfillment")
class RecordItemPicked:
    """Record that a single item has been picked from its location."""

    fulfillment_id = Identifier(required=True)
    item_id = Identifier(required=True)
    pick_location = String(required=True, max_length=100)


@fulfillment.command(part_of="Fulfillment")
class CompletePickList:
    """Complete the pick list — all items must have been picked."""

    fulfillment_id = Identifier(required=True)


@fulfillment.command_handler(part_of=Fulfillment)
class PickingHandler:
    @handle(AssignPicker)
    def assign_picker(self, command):
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        ff.assign_picker(command.picker_name)
        repo.add(ff)

    @handle(RecordItemPicked)
    def record_item_picked(self, command):
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        ff.record_item_picked(command.item_id, command.pick_location)
        repo.add(ff)

    @handle(CompletePickList)
    def complete_pick_list(self, command):
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        ff.complete_pick_list()
        repo.add(ff)
