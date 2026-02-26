"""BDD tests for order fulfillment."""

from pytest_bdd import parsers, scenarios, when

from ordering.order.fulfillment import RecordShipment

scenarios("features/order_fulfillment.feature")


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------
@when("the order is marked as processing", target_fixture="order")
def _(order, mark_processing):
    return order.process(mark_processing)


@when(
    parsers.cfparse('the order is shipped with carrier "{carrier}" tracking "{tracking}"'),
    target_fixture="order",
)
def _(order, order_id, carrier, tracking):
    return order.process(
        RecordShipment(
            order_id=order_id,
            shipment_id="ship-001",
            carrier=carrier,
            tracking_number=tracking,
        )
    )


@when("the order is delivered", target_fixture="order")
def _(order, deliver_order):
    return order.process(deliver_order)
