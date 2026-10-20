"""Invoice voiding — command and handler."""

from protean import handle
from protean.fields import Identifier, String
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.invoice.invoice import Invoice


@payments.command(part_of="Invoice")
class VoidInvoice:
    """Void an existing invoice."""

    invoice_id: str = Identifier(required=True)
    reason: str = String(required=True, max_length=500)


@payments.command_handler(part_of=Invoice)
class VoidInvoiceHandler:
    @handle(VoidInvoice)
    def void_invoice(self, command: VoidInvoice) -> None:
        repo = current_domain.repository_for(Invoice)
        invoice = repo.get(command.invoice_id)
        invoice.void(reason=command.reason)
        repo.add(invoice)
