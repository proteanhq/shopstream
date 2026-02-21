"""Fulfillment packing — commands and handler.

Handles the packing phase: recording packed items and generating shipping labels.
"""

import json

from protean import handle
from protean.fields import Identifier, String, Text
from protean.utils.globals import current_domain

from fulfillment.domain import fulfillment
from fulfillment.fulfillment.fulfillment import Fulfillment


@fulfillment.command(part_of="Fulfillment")
class RecordPacking:
    """Record that items have been packed into shipping packages."""

    fulfillment_id = Identifier(required=True)
    packed_by = String(required=True, max_length=100)
    packages = Text(required=True)  # JSON list of package dicts


@fulfillment.command(part_of="Fulfillment")
class GenerateShippingLabel:
    """Record that a shipping label has been generated."""

    fulfillment_id = Identifier(required=True)
    label_url = String(required=True, max_length=500)
    carrier = String(required=True, max_length=100)
    service_level = String(required=True, max_length=50)


@fulfillment.command_handler(part_of=Fulfillment)
class PackingHandler:
    @handle(RecordPacking)
    def record_packing(self, command):
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        packages_data = json.loads(command.packages) if isinstance(command.packages, str) else command.packages
        ff.record_packing(command.packed_by, packages_data)
        repo.add(ff)

    @handle(GenerateShippingLabel)
    def generate_shipping_label(self, command):
        repo = current_domain.repository_for(Fulfillment)
        ff = repo.get(command.fulfillment_id)
        ff.generate_shipping_label(
            label_url=command.label_url,
            carrier=command.carrier,
            service_level=command.service_level,
        )
        repo.add(ff)
