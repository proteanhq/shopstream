"""Queries for the PaymentStatusView projection."""

from protean import read
from protean.fields import Identifier
from protean.utils.globals import current_domain

from payments.domain import payments
from payments.projections.payment_status import PaymentStatusView


@payments.query(part_of=PaymentStatusView)
class GetPaymentStatus:
    payment_id = Identifier(required=True)


@payments.query_handler(part_of=PaymentStatusView)
class PaymentStatusQueryHandler:
    @read(GetPaymentStatus)
    def get_payment_status(self, query):
        return current_domain.view_for(PaymentStatusView).get(query.payment_id)
