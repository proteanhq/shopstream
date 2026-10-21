"""No event in the money-carrying event modules declares a float field.

A float event field writes binary floats such as ``3.3000000000000003`` to the
event store and the shared bus. Money on these events is
``Decimal(precision=19, scale=4)`` instead, so a new float field here is a
regression.
"""

import inspect
import typing
from decimal import Decimal

import pytest
from protean.utils.reflection import declared_fields

import catalogue.product.events
import ordering.order.events
import payments.invoice.events
import payments.payment.events

_MODULES = [catalogue.product.events, ordering.order.events, payments.invoice.events, payments.payment.events]


def _events(module):
    return [
        cls
        for _, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__ and getattr(cls, "element_type", None) is not None
    ]


def _types(field):
    python_type = field._python_type
    return set(typing.get_args(python_type)) or {python_type}


@pytest.mark.parametrize("module", _MODULES, ids=lambda module: module.__name__)
def test_no_event_field_is_a_float(module):
    events = _events(module)
    assert events, f"no events found in {module.__name__}"

    float_fields = [
        f"{event.__name__}.{name}"
        for event in events
        for name, field in declared_fields(event).items()
        if float in _types(field)
    ]

    assert float_fields == []


_C = catalogue.product.events
_O = ordering.order.events
_P = payments.payment.events

# Every money field the event modules carry. OrderCreated.items and
# ItemAdded.unit_price hold money as 4-place strings inside a dict and a
# String field, so they are not listed.
_MONEY_FIELDS = [
    (_C.VariantAdded, "price_amount"),
    (_C.VariantPriceChanged, "previous_price"),
    (_C.VariantPriceChanged, "new_price"),
    (_C.TierPriceSet, "price"),
    *[(_O.OrderCreated, name) for name in ("subtotal", "shipping_cost", "tax_total", "discount_total", "grand_total")],
    *[
        (event, name)
        for event in (_O.ItemAdded, _O.ItemRemoved, _O.ItemQuantityUpdated)
        for name in ("new_subtotal", "new_grand_total")
    ],
    (_O.PaymentSucceeded, "amount"),
    (_O.OrderRefunded, "refund_amount"),
    *[
        (event, "amount")
        for event in (_P.PaymentInitiated, _P.PaymentSucceeded, _P.RefundRequested, _P.RefundCompleted)
    ],
    (payments.invoice.events.InvoiceGenerated, "total"),
]


@pytest.mark.parametrize(
    ("event", "field_name"),
    _MONEY_FIELDS,
    ids=[f"{event.__name__}.{name}" for event, name in _MONEY_FIELDS],
)
def test_money_fields_are_numeric_19_4(event, field_name):
    field = declared_fields(event)[field_name]
    assert _types(field) - {type(None)} == {Decimal}
    assert (field.precision, field.scale) == (19, 4)
