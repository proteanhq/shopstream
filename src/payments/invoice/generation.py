"""Invoice generation — command and handler."""

from protean import handle
from protean.fields import Float, Identifier, List, ValueObject
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.invoice.invoice import Invoice, InvoiceLineItemInput


@payments.command(part_of="Invoice")
class GenerateInvoice:
    """Generate a new invoice for an order."""

    order_id = Identifier(required=True)
    customer_id = Identifier(required=True)
    # Typed line items derived from the InvoiceLineItem entity via
    # value_object_from_entity — no more untyped List(Dict()).
    line_items = List(content_type=ValueObject(InvoiceLineItemInput), required=True)
    tax = Float(default=0.0)


@payments.command_handler(part_of=Invoice)
class GenerateInvoiceHandler:
    @handle(GenerateInvoice)
    def generate_invoice(self, command):
        invoice = Invoice.create(
            order_id=command.order_id,
            customer_id=command.customer_id,
            line_items_data=command.line_items,
            tax=command.tax or 0.0,
        )
        current_domain.repository_for(Invoice).add(invoice)
        return str(invoice.id)
