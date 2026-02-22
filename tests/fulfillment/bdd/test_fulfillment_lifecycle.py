"""BDD tests for fulfillment lifecycle."""

from fulfillment.fulfillment.fulfillment import Fulfillment
from protean.exceptions import ValidationError
from pytest_bdd import parsers, scenarios, when

scenarios("features/fulfillment_lifecycle.feature")


@when(
    parsers.cfparse('a fulfillment is created for order "{order_id}" with {count:d} items'),
    target_fixture="ff",
)
def create_fulfillment(order_id, count):
    items_data = [
        {
            "order_item_id": f"oi-{i}",
            "product_id": f"prod-{i}",
            "sku": f"SKU-{i:03d}",
            "quantity": 1,
        }
        for i in range(1, count + 1)
    ]
    return Fulfillment.create(
        order_id=order_id,
        customer_id="cust-bdd-lc",
        items_data=items_data,
    )


@when(
    parsers.cfparse('picker "{picker_name}" is assigned to the fulfillment'),
    target_fixture="ff",
)
def assign_picker(ff, picker_name):
    ff.assign_picker(picker_name)
    return ff


@when("all items are picked from their locations", target_fixture="ff")
def pick_all_items(ff):
    for i, item in enumerate(ff.items):
        ff.record_item_picked(str(item.id), f"A-{i + 1}")
    return ff


@when("the pick list is completed", target_fixture="ff")
def complete_pick_list(ff):
    ff.complete_pick_list()
    return ff


@when(
    parsers.cfparse('the items are packed by "{packed_by}" into {count:d} packages'),
    target_fixture="ff",
)
def record_packing(ff, packed_by, count):
    packages_data = [{"weight": 1.5} for _ in range(count)]
    ff.record_packing(packed_by, packages_data)
    return ff


@when(
    parsers.cfparse('a shipping label is generated for carrier "{carrier}" with service "{service_level}"'),
    target_fixture="ff",
)
def generate_shipping_label(ff, carrier, service_level):
    ff.generate_shipping_label(
        "https://carrier.example.com/labels/lbl-bdd",
        carrier,
        service_level,
    )
    return ff


@when(
    parsers.cfparse('the shipment is handed off with tracking number "{tracking_number}"'),
    target_fixture="ff",
)
def record_handoff(ff, tracking_number):
    ff.record_handoff(tracking_number)
    return ff


@when(
    parsers.cfparse('a tracking event "{status}" is recorded at "{location}"'),
    target_fixture="ff",
)
def add_tracking_event(ff, status, location):
    ff.add_tracking_event(status, location, f"Tracking: {status}")
    return ff


@when("delivery is confirmed", target_fixture="ff")
def confirm_delivery(ff):
    ff.record_delivery()
    return ff


@when(
    parsers.cfparse('packing is attempted by "{packed_by}"'),
    target_fixture="ff",
)
def attempt_packing(ff, packed_by, error):
    try:
        ff.record_packing(packed_by, [{"weight": 1.0}])
    except ValidationError as exc:
        error["exc"] = exc
    return ff


@when("the pick list completion is attempted", target_fixture="ff")
def attempt_pick_list_completion(ff, error):
    try:
        ff.complete_pick_list()
    except ValidationError as exc:
        error["exc"] = exc
    return ff


@when(
    parsers.cfparse('label generation is attempted for carrier "{carrier}" with service "{service_level}"'),
    target_fixture="ff",
)
def attempt_label_generation(ff, carrier, service_level, error):
    try:
        ff.generate_shipping_label(
            "https://carrier.example.com/labels/lbl-fail",
            carrier,
            service_level,
        )
    except ValidationError as exc:
        error["exc"] = exc
    return ff


@when(
    parsers.cfparse('assigning picker "{picker_name}" is attempted'),
    target_fixture="ff",
)
def attempt_assign_picker(ff, picker_name, error):
    try:
        ff.assign_picker(picker_name)
    except ValidationError as exc:
        error["exc"] = exc
    return ff
