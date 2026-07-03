"""Model-based check: InventoryItem vs an independent plain-Python model (P2).

WHAT THIS CHECKS
    A Hypothesis state machine drives random *valid* command sequences at one
    event-sourced `InventoryItem` (receive / reserve / release / confirm / adjust)
    and, after every step, asserts the aggregate's observable stock position
    matches a hand-written model that tracks the same thing in plain Python.

WHY THIS IS A TYPE-A ORACLE (see VERIFICATION_STRATEGY.md section 2)
    The expected state comes from an INDEPENDENT reimplementation, not from
    folding Protean's own events. Random sequencing explores interleavings a
    hand-written example would never try; on disagreement Hypothesis shrinks to
    the shortest failing sequence. A convergence check (projection == fold(events))
    could not catch a bug in the aggregate's own state machine — this can.

SCOPE / SPEED
    Drives the aggregate directly (method calls apply events in-memory via
    `@apply`), not the full command→persist→project→replay path: the projector
    fan-out per command makes that path minutes-slow, and the state-machine
    correctness this targets lives in the aggregate. One event-sourced aggregate
    (Stock / InventoryItem), per the ticket. Runs on the in-memory adapters.

RUN:
    .venv/bin/python -m pytest \
        verification/model/test_inventory_model.py --protean-env memory -q
"""

from __future__ import annotations

import uuid

import pytest
from hypothesis import settings
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, precondition, rule
from hypothesis.strategies import integers

ACTIVE = "Active"
CONFIRMED = "Confirmed"
RELEASED = "Released"
HELD = {ACTIVE, CONFIRMED}  # statuses that still hold stock


class _Model:
    """Independent, plain-Python truth for one item's stock position."""

    def __init__(self):
        self.on_hand = 0
        self.reservations: dict[str, list] = {}  # rid -> [quantity, status]

    @property
    def reserved(self) -> int:
        return sum(qty for qty, status in self.reservations.values() if status in HELD)

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


class InventoryStateMachine(RuleBasedStateMachine):
    reservations = Bundle("reservations")

    def __init__(self):
        super().__init__()
        from inventory.stock.stock import InventoryItem

        self.item = InventoryItem.create(
            product_id=str(uuid.uuid4()),
            variant_id=str(uuid.uuid4()),
            warehouse_id=str(uuid.uuid4()),
            sku=f"SKU-{uuid.uuid4().hex[:8]}",
            initial_quantity=0,
            reorder_point=0,
        )
        self.model = _Model()

    def _status(self, rid) -> str:
        return self.model.reservations.get(rid, [0, RELEASED])[1]

    # --- rules ---------------------------------------------------------------
    @rule(quantity=integers(min_value=1, max_value=50))
    def receive_stock(self, quantity):
        self.item.receive_stock(quantity=quantity)
        self.model.on_hand += quantity

    @precondition(lambda self: self.model.available > 0)
    @rule(target=reservations, order=integers(min_value=0, max_value=10**9), want=integers(min_value=1, max_value=50))
    def reserve(self, order, want):
        quantity = min(want, self.model.available)  # keep the sequence valid
        self.item.reserve(order_id=str(order), quantity=quantity)
        rid = str(self.item.reservations[-1].id)
        self.model.reservations[rid] = [quantity, ACTIVE]
        return rid

    @rule(rid=reservations)
    def release(self, rid):
        if self._status(rid) != ACTIVE:
            return  # only Active reservations can be released — keep it valid
        self.item.release_reservation(reservation_id=rid, reason="test")
        self.model.reservations[rid][1] = RELEASED

    @rule(rid=reservations)
    def confirm(self, rid):
        if self._status(rid) != ACTIVE:
            return
        self.item.confirm_reservation(reservation_id=rid)
        self.model.reservations[rid][1] = CONFIRMED

    @rule(delta=integers(min_value=-50, max_value=50))
    def adjust_stock(self, delta):
        if delta == 0 or self.model.on_hand + delta < 0:
            return  # aggregate forbids negative on_hand
        self.item.adjust_stock(
            quantity_change=delta,
            adjustment_type="Correction",
            reason="test",
            adjusted_by="tester",
        )
        self.model.on_hand += delta

    # --- the oracle: real aggregate must equal the independent model ---------
    @invariant()
    def matches_model(self):
        levels = self.item.levels
        # An all-default StockLevels (every field 0) round-trips to None
        # (proteanhq/protean#1078); the aggregate itself treats that as zeros
        # (`self.levels.x if self.levels else 0`), so mirror that here.
        on_hand = levels.on_hand if levels else 0
        reserved = levels.reserved if levels else 0
        available = levels.available if levels else 0
        assert on_hand == self.model.on_hand, f"on_hand {on_hand} != {self.model.on_hand}"
        assert reserved == self.model.reserved, f"reserved {reserved} != {self.model.reserved}"
        assert available == self.model.available, f"available {available} != {self.model.available}"
        # internal consistency the aggregate must always preserve
        assert available == on_hand - reserved


@pytest.mark.usefixtures("inventory_ctx")
def test_inventory_item_matches_independent_model():
    from hypothesis.stateful import run_state_machine_as_test

    # Enough random sequences to explore interleavings a hand-written test would
    # miss, bounded to stay quick in the memory CI job.
    run_state_machine_as_test(
        InventoryStateMachine,
        settings=settings(max_examples=150, stateful_step_count=25, deadline=None),
    )
