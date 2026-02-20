"""Invoice generation — command and handler."""

import json

from protean import handle
from protean.fields import Float, Identifier, Text
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.invoice.invoice import Invoice


@payments.command(part_of="Invoice")
class GenerateInvoice:
    """Generate a new invoice for an order."""

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    line_items = Text(required=True)  # JSON: list of {description, quantity, unit_price}
    tax = Float(default=0.0)


@payments.command_handler(part_of=Invoice)
class GenerateInvoiceHandler:
    @handle(GenerateInvoice)
    def generate_invoice(self, command):
        line_items_data = json.loads(command.line_items) if isinstance(command.line_items, str) else command.line_items

        invoice = Invoice.create(
            order_id=command.order_id,
            customer_id=command.customer_id,
            line_items_data=line_items_data,
            tax=command.tax or 0.0,
        )
        current_domain.repository_for(Invoice).add(invoice)
        return str(invoice.id)
