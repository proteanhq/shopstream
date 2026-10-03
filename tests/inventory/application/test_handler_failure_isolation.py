"""Handler failure isolation under synchronous event dispatch.

Protean 0.17 changed what happens when an event handler fails while events are
dispatched synchronously (``event_processing = "sync"``, which the memory and
test profiles use):

- A failing handler class no longer stops the other classes queued for the same
  event (proteanhq/protean#1411). ``StockReceived`` has six projectors in
  inventory, so these tests make some of them fail and check the rest.
- A failing ``@handle`` method no longer stops its sibling methods for the same
  event (proteanhq/protean#1406). No ShopStream class has two methods for one
  event, so those tests build a throwaway domain.

Each test also pins what the caller of ``current_domain.process(...)`` gets back.
Sync dispatch runs inside the command's ``UnitOfWork.commit()``, after the
aggregate is saved. The commit sorts a handler failure by type:

- ``ExpectedVersionError`` and ``ConfigurationError`` reach the caller as
  themselves.
- A ``ValueError`` and a SQLAlchemy ``StaleDataError`` come back as a new
  ``ExpectedVersionError``.
- Any other ``Exception``, or an ``ExceptionGroup`` of several, is wrapped in a
  ``TransactionError`` with the original on ``__cause__``.
- A ``BaseException`` that is not an ``Exception`` passes through untouched.

Do not raise ``ValueError`` from a fake handler here. The commit reports it as
``ExpectedVersionError``, and version retry runs the committed command again
(proteanhq/protean#1682, pinned by
``verification/regression/test_protean_regressions.py::test_1682_value_error_from_a_sync_handler_is_not_a_version_conflict``).
"""

from collections.abc import Callable

import pytest
from protean import Domain, current_domain, handle
from protean.exceptions import ExpectedVersionError, TransactionError
from protean.fields import Identifier, String

from inventory.projections.event_audit import EventAudit, EventAuditHandler
from inventory.projections.inventory_level import InventoryLevel, InventoryLevelProjector
from inventory.projections.inventory_valuation import InventoryValuation, InventoryValuationProjector
from inventory.projections.low_stock_report import LowStockReport, LowStockReportProjector
from inventory.projections.product_availability import ProductAvailability, ProductAvailabilityProjector
from inventory.projections.stock_movement_log import StockMovementLog, StockMovementLogProjector
from inventory.projections.warehouse_stock import WarehouseStock, WarehouseStockProjector
from inventory.stock.adjustment import AdjustStock
from inventory.stock.events import StockReceived
from inventory.stock.initialization import InitializeStock
from inventory.stock.receiving import ReceiveStock
from inventory.stock.stock import InventoryItem

STOCK_RECEIVED_PROJECTORS = (
    InventoryLevelProjector,
    WarehouseStockProjector,
    InventoryValuationProjector,
    StockMovementLogProjector,
    ProductAvailabilityProjector,
    LowStockReportProjector,
)
# Every class the domain queues for StockReceived: the six projectors plus the
# `$any` audit handler.
STOCK_RECEIVED_HANDLERS = (*STOCK_RECEIVED_PROJECTORS, EventAuditHandler)

ON_HAND_BEFORE = 50
RECEIVED = 30
ON_HAND_AFTER = ON_HAND_BEFORE + RECEIVED


def _initialize_stock(**overrides):
    defaults = {
        "product_id": "prod-001",
        "variant_id": "var-001",
        "warehouse_id": "wh-001",
        "sku": "TSHIRT-BLK-M",
        "initial_quantity": 100,
        "reorder_point": 10,
        "reorder_quantity": 50,
    }
    defaults.update(overrides)
    command = InitializeStock(**defaults)
    return current_domain.process(command, asynchronous=False)


def _seed_low_stock_item():
    """Create an item with 50 on hand that sits on the low-stock report.

    Initialized at 60 with a reorder point of 50, then written down by 10, so the
    adjustment raises ``LowStockDetected``. A receipt of 30 lifts it above the
    reorder point, which removes the report row. That gives the
    ``LowStockReport`` projector a visible effect for ``StockReceived``.
    """
    item_id = _initialize_stock(initial_quantity=ON_HAND_BEFORE + 10, reorder_point=ON_HAND_BEFORE)
    current_domain.process(
        AdjustStock(
            inventory_item_id=item_id,
            quantity_change=-10,
            adjustment_type="Shrinkage",
            reason="Cycle count",
            adjusted_by="tester",
        ),
        asynchronous=False,
    )
    assert current_domain.repository_for(LowStockReport).get_or_none(item_id) is not None, (
        "precondition: the item is on the low-stock report"
    )
    for projector_cls in STOCK_RECEIVED_PROJECTORS:
        assert not _receipt_applied(projector_cls, item_id), f"precondition: {projector_cls.__name__} not yet updated"
    assert _audited_receipts(item_id) == 0, "precondition: no StockReceived audit row yet"
    return item_id


def _receive(item_id):
    return current_domain.process(
        ReceiveStock(inventory_item_id=item_id, quantity=RECEIVED),
        asynchronous=False,
    )


def _on_hand(read_model_cls, key):
    row = current_domain.repository_for(read_model_cls).get_or_none(key)
    assert row is not None, f"{read_model_cls.__name__} row {key} is missing"
    return row.on_hand


def _receipt_applied(projector_cls, item_id) -> bool:
    """Return whether ``projector_cls``'s read model shows the receipt of 30."""
    if projector_cls is InventoryLevelProjector:
        return _on_hand(InventoryLevel, item_id) == ON_HAND_AFTER
    if projector_cls is WarehouseStockProjector:
        return _on_hand(WarehouseStock, item_id) == ON_HAND_AFTER
    if projector_cls is InventoryValuationProjector:
        return _on_hand(InventoryValuation, item_id) == ON_HAND_AFTER
    if projector_cls is StockMovementLogProjector:
        rows = current_domain.repository_for(StockMovementLog).query.filter(inventory_item_id=item_id).all().items
        assert len(rows) > 0, f"no movement-log rows for {item_id}"
        received = [row for row in rows if row.event_type == "StockReceived"]
        return len(received) == 1 and received[0].quantity_change == RECEIVED
    if projector_cls is ProductAvailabilityProjector:
        row = current_domain.repository_for(ProductAvailability).get_or_none("prod-001::var-001")
        assert row is not None, "ProductAvailability row prod-001::var-001 is missing"
        return row.total_on_hand == ON_HAND_AFTER
    if projector_cls is LowStockReportProjector:
        return current_domain.repository_for(LowStockReport).get_or_none(item_id) is None
    raise AssertionError(f"no read-model check for {projector_cls.__name__}")


def _audited_receipts(item_id) -> int:
    rows = current_domain.repository_for(EventAudit).query.filter(inventory_item_id=item_id).all().items
    return len([row for row in rows if row.event_type == "StockReceived"])


def _stock_received_method(projector_cls) -> Callable:
    methods = projector_cls._handlers.get(StockReceived.__type__)
    assert methods and len(methods) == 1, f"{projector_cls.__name__} has no single StockReceived method"
    return next(iter(methods))


def _replace_stock_received(monkeypatch, projector_cls, fake) -> list:
    """Swap ``projector_cls``'s ``StockReceived`` method for ``fake``; return its call log.

    The class keeps its methods in ``_handlers``, wrapped when the class was
    registered, so patching the class attribute would change nothing. Wrapping
    the fake with ``@handle`` keeps the version-retry wrapper the real method has.
    """
    calls: list[str] = []

    def recorded(self, event):
        calls.append(event.inventory_item_id)
        return fake(self, event)

    _stock_received_method(projector_cls)
    monkeypatch.setitem(projector_cls._handlers, StockReceived.__type__, {handle(StockReceived)(recorded)})
    return calls


def _raise(exc: Exception):
    def fake(self, event):
        raise exc

    return fake


def _queue_stock_received_in_order(monkeypatch, order: list[type]) -> list[list[type]]:
    """Make the domain queue the ``StockReceived`` handler classes in ``order``.

    The domain returns the classes as a set, so the order they run in changes
    between runs. A test that fixes the order can put a failing projector ahead
    of the others, where stopping at the first failure would skip them. Returns
    a log with one entry per ``StockReceived`` dispatch.
    """
    queued: list[list[type]] = []
    domain = current_domain._get_current_object()
    original_handlers_for = domain.handlers_for

    def handlers_in_order(event):
        handlers = original_handlers_for(event)
        if not isinstance(event, StockReceived):
            return handlers
        assert set(handlers) == set(order), "the StockReceived handler classes changed"
        queued.append(list(order))
        return list(order)

    monkeypatch.setattr(domain, "handlers_for", handlers_in_order)
    return queued


def _failing_first(*failing: type) -> list[type]:
    return [*failing, *(cls for cls in STOCK_RECEIVED_HANDLERS if cls not in failing)]


def _assert_item_on_hand(item_id, expected):
    assert current_domain.repository_for(InventoryItem).get(item_id).levels.on_hand == expected


class TestOneProjectorFails:
    def test_other_projectors_still_update(self, monkeypatch):
        item_id = _seed_low_stock_item()
        failure = RuntimeError("inventory level projector is down")
        calls = _replace_stock_received(monkeypatch, InventoryLevelProjector, _raise(failure))
        queued = _queue_stock_received_in_order(monkeypatch, _failing_first(InventoryLevelProjector))

        with pytest.raises(TransactionError) as excinfo:
            _receive(item_id)

        assert len(queued) == 1
        assert excinfo.value.__cause__ is failure
        assert excinfo.value.extra_info["original_exception"] == "RuntimeError"
        assert calls == [item_id]
        assert not _receipt_applied(InventoryLevelProjector, item_id)
        for projector_cls in STOCK_RECEIVED_PROJECTORS:
            if projector_cls is not InventoryLevelProjector:
                assert _receipt_applied(projector_cls, item_id), f"{projector_cls.__name__} did not run"
        assert _audited_receipts(item_id) == 1
        # The aggregate was saved before dispatch, once.
        _assert_item_on_hand(item_id, ON_HAND_AFTER)


class TestTwoProjectorsFail:
    def test_caller_gets_both_failures_in_a_group(self, monkeypatch):
        item_id = _seed_low_stock_item()
        warehouse_failure = RuntimeError("warehouse stock projector is down")
        movement_failure = KeyError("movement log projector is down")
        warehouse_calls = _replace_stock_received(monkeypatch, WarehouseStockProjector, _raise(warehouse_failure))
        movement_calls = _replace_stock_received(monkeypatch, StockMovementLogProjector, _raise(movement_failure))
        queued = _queue_stock_received_in_order(
            monkeypatch, _failing_first(WarehouseStockProjector, StockMovementLogProjector)
        )

        with pytest.raises(TransactionError) as excinfo:
            _receive(item_id)

        assert len(queued) == 1
        group = excinfo.value.__cause__
        assert isinstance(group, ExceptionGroup)
        assert len(group.exceptions) == 2
        assert {id(exc) for exc in group.exceptions} == {id(warehouse_failure), id(movement_failure)}
        assert warehouse_calls == [item_id]
        assert movement_calls == [item_id]
        failing = {WarehouseStockProjector, StockMovementLogProjector}
        for projector_cls in STOCK_RECEIVED_PROJECTORS:
            if projector_cls not in failing:
                assert _receipt_applied(projector_cls, item_id), f"{projector_cls.__name__} did not run"
        assert _audited_receipts(item_id) == 1
        _assert_item_on_hand(item_id, ON_HAND_AFTER)


class TestExpectedVersionErrorOnce:
    def test_version_retry_reruns_the_projector(self, monkeypatch):
        item_id = _seed_low_stock_item()
        original = _stock_received_method(InventoryValuationProjector).__wrapped__
        conflicts: list[ExpectedVersionError] = []

        def conflict_once(self, event):
            if not conflicts:
                conflicts.append(ExpectedVersionError("simulated version conflict"))
                raise conflicts[0]
            return original(self, event)

        calls = _replace_stock_received(monkeypatch, InventoryValuationProjector, conflict_once)

        _receive(item_id)

        assert len(conflicts) == 1
        assert calls == [item_id, item_id]
        for projector_cls in STOCK_RECEIVED_PROJECTORS:
            assert _receipt_applied(projector_cls, item_id), f"{projector_cls.__name__} did not apply the receipt"
        _assert_item_on_hand(item_id, ON_HAND_AFTER)


class TestExpectedVersionErrorEveryTime:
    def test_caller_gets_expected_version_error_and_later_projectors_do_not_run(self, monkeypatch):
        item_id = _seed_low_stock_item()
        failing = InventoryValuationProjector
        version_retry = current_domain.config["server"]["version_retry"]
        max_retries = version_retry["max_retries"]
        monkeypatch.setitem(version_retry, "base_delay_seconds", 0.001)
        calls = _replace_stock_received(
            monkeypatch, failing, _raise(ExpectedVersionError("simulated version conflict"))
        )

        # The failing projector sits in the middle, so some classes are queued
        # before it and some after.
        others = sorted((cls for cls in STOCK_RECEIVED_HANDLERS if cls is not failing), key=lambda cls: cls.__name__)
        order = [*others[:3], failing, *others[3:]]
        before, after = order[:3], order[4:]
        queued = _queue_stock_received_in_order(monkeypatch, order)

        ran: list[type] = []
        for handler_cls in order:
            dispatch = handler_cls._handle

            def spy(cls, item, _dispatch=dispatch):
                if isinstance(item, StockReceived):
                    ran.append(cls)
                return _dispatch(item)

            monkeypatch.setattr(handler_cls, "_handle", classmethod(spy))

        with pytest.raises(ExpectedVersionError) as excinfo:
            _receive(item_id)

        assert type(excinfo.value) is ExpectedVersionError
        # The receipt was committed before dispatch, yet the command handler's own
        # version retry runs ReceiveStock again on each attempt, so StockReceived
        # is dispatched max_retries + 1 times. This is a Protean bug, not yet filed
        # upstream. The correct behaviour (the command runs once) is pinned as a
        # strict xfail in verification/regression/test_protean_regressions.py::
        # test_committed_command_is_not_rerun_when_a_sync_handler_raises_expected_version_error.
        # When Protean fixes it, this count drops to 1 and this test fails.
        assert len(queued) == max_retries + 1
        # Each dispatch runs the classes queued before the failing projector, then
        # the failing one, and stops there.
        assert ran == [*before, failing] * len(queued)
        assert not set(after) & set(ran)
        # Each time, the projector's own version retry used up max_retries.
        assert len(calls) == (max_retries + 1) * len(queued)


def _parcel_domain(calls: list[str], failures: list[Exception]) -> tuple[Domain, type]:
    """Build a domain whose one event handler has two methods for the same event.

    The methods fail in the order they run: the first method to run raises
    ``failures[0]``, the second raises ``failures[1]``. The handler keeps its
    methods in a set, so which method runs first changes between runs. Failing by
    position instead of by name means a one-failure test always fails the method
    that runs first, the case where stopping early would skip its sibling.

    Returns the domain and its ``LabelParcel`` command class.
    """
    # In-memory adapters and sync processing, set here so the domain behaves the
    # same under every --protean-env.
    domain = Domain(
        name="HandlerIsolationProbe",
        config={
            "databases": {"default": {"provider": "memory"}},
            "event_store": {"provider": "memory"},
            "brokers": {"default": {"provider": "inline"}},
            "command_processing": "sync",
            "event_processing": "sync",
        },
    )

    @domain.aggregate
    class Parcel:
        label = String(required=True)

    @domain.event(part_of=Parcel)
    class ParcelLabelled:
        parcel_id = Identifier(required=True)
        label = String(required=True)

    @domain.command(part_of=Parcel)
    class LabelParcel:
        label = String(required=True)

    @domain.command_handler(part_of=Parcel)
    class ParcelCommandHandler:
        @handle(LabelParcel)
        def label_parcel(self, command):
            parcel = Parcel(label=command.label)
            parcel.raise_(ParcelLabelled(parcel_id=parcel.id, label=parcel.label))
            current_domain.repository_for(Parcel).add(parcel)
            return parcel.id

    def react(name):
        position = len(calls)
        calls.append(name)
        if position < len(failures):
            raise failures[position]

    @domain.event_handler(part_of=Parcel)
    class ParcelLabelledHandler:
        @handle(ParcelLabelled)
        def notify_warehouse(self, event):
            react("notify_warehouse")

        @handle(ParcelLabelled)
        def notify_customer(self, event):
            react("notify_customer")

    domain.init(traverse=False)
    return domain, LabelParcel


class TestTwoMethodsForOneEvent:
    def test_sibling_method_runs_when_one_fails(self):
        calls: list[str] = []
        failure = RuntimeError("first notification failed")
        domain, label_parcel = _parcel_domain(calls, [failure])

        with domain.domain_context(), pytest.raises(TransactionError) as excinfo:
            domain.process(label_parcel(label="fragile"), asynchronous=False)

        assert excinfo.value.__cause__ is failure
        assert sorted(calls) == ["notify_customer", "notify_warehouse"]

    def test_both_failures_reach_the_caller_in_a_group(self):
        calls: list[str] = []
        first_failure = RuntimeError("first notification failed")
        second_failure = KeyError("second notification failed")
        domain, label_parcel = _parcel_domain(calls, [first_failure, second_failure])

        with domain.domain_context(), pytest.raises(TransactionError) as excinfo:
            domain.process(label_parcel(label="fragile"), asynchronous=False)

        group = excinfo.value.__cause__
        assert isinstance(group, ExceptionGroup)
        assert len(group.exceptions) == 2
        assert {id(exc) for exc in group.exceptions} == {id(first_failure), id(second_failure)}
        assert sorted(calls) == ["notify_customer", "notify_warehouse"]
