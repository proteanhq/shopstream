"""Upcaster that moves InvoiceGenerated from a float total to a ``Decimal`` total.

v1 stored ``total`` as a float. v2 declares it as
``Decimal(precision=19, scale=4)``, so the upcaster rewrites the stored float
as a 4-place string, rounded half-even.
"""

from typing import Any

from protean.core.upcaster import BaseUpcaster

from payments.domain import payments
from payments.invoice.events import InvoiceGenerated
from shared.money import money_fields_as_text


@payments.upcaster(event_type=InvoiceGenerated, from_version=1, to_version=2)
class UpcastInvoiceGeneratedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "total")
