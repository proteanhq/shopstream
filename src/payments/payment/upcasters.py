"""Upcasters that move Payment events from float money to ``Decimal`` money.

v1 of these events stored ``amount`` as a float. v2 declares it as
``Decimal(precision=19, scale=4)``, so each upcaster rewrites the stored float
as a 4-place string, rounded half-even.
"""

from typing import Any

from protean.core.upcaster import BaseUpcaster

from payments.domain import payments
from payments.payment.events import PaymentInitiated, PaymentSucceeded, RefundCompleted, RefundRequested
from shared.money import money_fields_as_text


@payments.upcaster(event_type=PaymentInitiated, from_version=1, to_version=2)
class UpcastPaymentInitiatedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "amount")


@payments.upcaster(event_type=PaymentSucceeded, from_version=1, to_version=2)
class UpcastPaymentSucceededV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "amount")


@payments.upcaster(event_type=RefundRequested, from_version=1, to_version=2)
class UpcastRefundRequestedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "amount")


@payments.upcaster(event_type=RefundCompleted, from_version=1, to_version=2)
class UpcastRefundCompletedV1ToV2(BaseUpcaster):
    def upcast(self, data: dict[str, Any]) -> dict[str, Any]:
        return money_fields_as_text(data, "amount")
