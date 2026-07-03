"""P16 - saga liveness + compensation (the OrderCheckoutSaga failure path).

WHAT THIS CHECKS
    ShopStream's checkout is coordinated by `OrderCheckoutSaga`, an event-sourced
    process manager on the `ordering::order` stream. When payment fails
    MAX_PAYMENT_RETRIES (3) times, the saga must:
      1. reach a terminal state (liveness - it never gets stuck mid-flight), and
      2. compensate: cancel the order AND release the inventory reservation it
         was holding (cross-domain, via the external bus).

    Property P16: every saga reaches a terminal state; a failure triggers
    compensation. This is the end-to-end async version - the pure-unit saga logic
    is covered by tests/ordering/domain/test_checkout_saga.py (which mocks the
    command dispatch); here the REAL order is cancelled and the REAL reservation
    is released through the running engines.

WHY THIS NEEDS THE ASYNC ENGINE (not the sync test suite)
    The saga is a multi-step PM whose transitions fan out across the ordering,
    inventory and payments engines and the external Redis bus (DB 15). Under
    `event_processing="sync"` it hits proteanhq/protean#1048 (a multi-step PM
    re-enters before its start transition persists and stops after the first
    step), so it cannot cascade to cancellation. This check therefore drives the
    REAL stack over HTTP and reads terminal state back. It is `@pytest.mark.engine`
    (local-only, deselected in CI via `-m "not engine"`, same as the DLQ test) -
    the engine's poll loops are unreliable in CI against Redis (proteanhq/protean
    #1055).

RUN (needs the running stack, base env):
    make docker-up && make setup-db && make truncate-db
    make api                                   # :8000
    make engine-ordering & make engine-inventory & make engine-payments &
    PYTHONPATH=src .venv/bin/python -m pytest verification/resilience/ -m engine -q

    (No `--protean-env`: the in-process reservation/PM reads must use the base
    env so they hit the same `_local` databases the engines write to.)
"""

from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = "http://localhost:8000"
# Engine health endpoints (per each domain.toml `health_port`).
ENGINE_HEALTH = {"ordering": 8083, "inventory": 8084, "payments": 8085}
MAX_PAYMENT_RETRIES = 3  # mirrors src/ordering/checkout/saga.py:MAX_PAYMENT_RETRIES

_ADDRESS = {
    "street": "1 Saga Way",
    "city": "Springfield",
    "state": "IL",
    "postal_code": "62701",
    "country": "US",
}


def _stack_ready() -> tuple[bool, str]:
    """The async stack (api + ordering/inventory/payments engines) must be up, and
    we must be in the base (async, `_local`) env so in-process reads match it."""
    if os.environ.get("PROTEAN_ENV") in ("test", "memory"):
        return False, "needs the base (async) env; run without --protean-env test/memory"
    try:
        if requests.get(f"{BASE_URL}/health", timeout=2).status_code != 200:
            return False, "api not healthy on :8000"
    except requests.RequestException:
        return False, "api not reachable on :8000 (start `make api`)"
    for name, port in ENGINE_HEALTH.items():
        try:
            requests.get(f"http://127.0.0.1:{port}/", timeout=2)
        except requests.RequestException:
            return False, f"{name} engine not reachable on :{port} (start `make engine-{name}`)"
    return True, ""


_ready, _why = _stack_ready()
pytestmark = [
    pytest.mark.engine,
    pytest.mark.slow,
    pytest.mark.skipif(not _ready, reason=f"async saga stack not available: {_why}"),
]


# --- HTTP driver: force a 3x payment failure through the real saga -----------


class _Client:
    def __init__(self):
        self.s = requests.Session()

    def call(self, method: str, path: str, **kw):
        r = self.s.request(method, BASE_URL + path, timeout=10, **kw)
        assert r.status_code < 500, f"{method} {path} -> {r.status_code}: {r.text[:200]}"
        return r

    def order_status(self, order_id: str) -> str | None:
        r = self.s.get(f"{BASE_URL}/orders/{order_id}", timeout=10)
        return r.json().get("status") if r.status_code == 200 else None

    def poll_status(self, order_id: str, want: str, timeout: float = 30, interval: float = 0.5) -> str | None:
        """Bounded liveness wait — returns the reached status, or the last-seen
        status if `want` is not reached within `timeout` (the stuck-saga signal)."""
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            last = self.order_status(order_id)
            if last == want:
                return last
            time.sleep(interval)
        return last


def _drive_forced_failure_checkout(c: _Client) -> dict:
    """Cart -> checkout -> confirm -> reserve -> fail payment x3. Returns ids."""
    sfx = uuid.uuid4().hex[:8]
    product_id, variant_id, customer_id = f"prod-{sfx}", f"var-{sfx}", f"cust-{sfx}"

    warehouse_id = c.call(
        "POST", "/warehouses", json={"name": "Saga WH", "address": _ADDRESS, "capacity": 10000}
    ).json()["warehouse_id"]
    item_id = c.call(
        "POST",
        "/inventory",
        json={
            "product_id": product_id,
            "variant_id": variant_id,
            "warehouse_id": warehouse_id,
            "sku": f"SKU-{sfx}",
            "initial_quantity": 50,
        },
    ).json()["inventory_item_id"]

    cart_id = c.call("POST", "/carts", json={"customer_id": customer_id}).json()["cart_id"]
    c.call("POST", f"/carts/{cart_id}/items", json={"product_id": product_id, "variant_id": variant_id, "quantity": 1})
    order_id = c.call(
        "POST",
        f"/carts/{cart_id}/checkout",
        json={"shipping": _ADDRESS, "billing": _ADDRESS, "payment_method": "credit_card"},
    ).json()["order_id"]

    c.call("PUT", f"/orders/{order_id}/confirm")  # OrderConfirmed -> saga starts
    # Reserve stock: StockReserved -> (bus) -> saga dispatches RecordPaymentPending.
    c.call(
        "POST", f"/inventory/{item_id}/reserve", json={"order_id": order_id, "quantity": 1, "expires_in_minutes": 15}
    )
    assert c.poll_status(order_id, "Payment_Pending") == "Payment_Pending", (
        "saga did not reach Payment_Pending after reservation"
    )

    def _fail_payment():
        payment_id = c.call(
            "POST",
            "/payments",
            json={
                "order_id": order_id,
                "customer_id": customer_id,
                "amount": 49.99,
                "currency": "USD",
                "payment_method_type": "credit_card",
                "last4": "4242",
                "idempotency_key": f"idem-{uuid.uuid4().hex[:12]}",
            },
        ).json()["payment_id"]
        c.call(
            "POST",
            "/payments/webhook",
            headers={"X-Gateway-Signature": "test-signature"},
            json={
                "payment_id": payment_id,
                "gateway_transaction_id": f"gtx-{uuid.uuid4().hex[:12]}",
                "gateway_status": "failed",
                "failure_reason": "Card declined",
            },
        )

    # Failure 1 (order is already Payment_Pending from the reservation).
    _fail_payment()
    # Failures 2..N: each failure returns the order to Confirmed; re-drive
    # payment/pending, then fail again, until the saga exhausts its retries.
    for n in range(2, MAX_PAYMENT_RETRIES + 1):
        assert c.poll_status(order_id, "Confirmed") == "Confirmed", (
            f"order did not return to Confirmed before retry {n}"
        )
        c.call(
            "PUT",
            f"/orders/{order_id}/payment/pending",
            json={"payment_id": f"retry-{n}", "payment_method": "credit_card"},
        )
        assert c.poll_status(order_id, "Payment_Pending") == "Payment_Pending", (
            f"order did not re-enter Payment_Pending on retry {n}"
        )
        _fail_payment()

    return {"order_id": order_id, "item_id": item_id, "customer_id": customer_id}


@pytest.fixture(scope="module")
def cancelled_checkout() -> dict:
    """Drive one forced-failure checkout to completion; shared by the assertions."""
    return _drive_forced_failure_checkout(_Client())


# --- assertions --------------------------------------------------------------


def test_saga_cancels_order_on_max_payment_failures(cancelled_checkout):
    """Liveness + compensation (order side): after 3 payment failures the saga
    must drive the order to a terminal CANCELLED state within a bounded wait.
    The bounded poll IS the stuck-saga detector - if the order never reaches
    Cancelled, we fail with the last-seen (stuck) status."""
    c = _Client()
    order_id = cancelled_checkout["order_id"]

    status = c.poll_status(order_id, "Cancelled", timeout=40)
    assert status == "Cancelled", (
        f"saga did not reach terminal CANCELLED within timeout; stuck at {status!r}. "
        "The checkout saga failed to compensate after exhausting payment retries."
    )

    order = c.call("GET", f"/orders/{order_id}").json()
    # Cancellation came from the saga's System-initiated CancelOrder, not a user.
    assert order.get("cancelled_by") == "System"
    assert "Payment failed" in (order.get("cancellation_reason") or "")


def test_compensation_releases_inventory_reservation(cancelled_checkout):
    """Cross-domain compensation: OrderCancelled -> (bus) -> inventory releases
    the reservation the checkout was holding. Read the reservation state in
    process from the same `_local` DB the inventory engine writes to."""
    from inventory.domain import inventory

    inventory.init()
    order_id = cancelled_checkout["order_id"]
    item_id = cancelled_checkout["item_id"]

    with inventory.domain_context():
        from inventory.stock.stock import InventoryItem

        statuses = None
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            item = inventory.repository_for(InventoryItem).get(item_id)
            statuses = [r.status for r in item.reservations if str(r.order_id) == order_id]
            if statuses and all(s == "Released" for s in statuses):
                break
            time.sleep(0.5)

    assert statuses, f"no reservation found for order {order_id}"
    assert all(s == "Released" for s in statuses), (
        f"reservation(s) not released after cancellation: {statuses}. Compensation "
        "did not cascade from OrderCancelled to the inventory reservation."
    )


def test_saga_process_manager_reaches_terminal_complete_state(cancelled_checkout):
    """Stuck-saga detector at the source: read the saga's own event-sourced PM
    stream and assert its last transition is terminal (is_complete) and the state
    is `failed` - proving the PM itself finalized, not just the order projection."""
    from ordering.domain import ordering

    ordering.init()
    order_id = cancelled_checkout["order_id"]
    stream = f"ordering::order_checkout_saga-{order_id}"

    with ordering.domain_context():
        last_state, is_complete = None, False
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            messages = ordering.event_store.store.read(stream)
            if messages:
                payload = messages[-1].data or {}
                last_state = (payload.get("state") or {}).get("status")
                is_complete = bool(payload.get("is_complete"))
                if is_complete:
                    break
            time.sleep(0.5)

    assert is_complete, (
        f"OrderCheckoutSaga for {order_id} never reached a terminal (is_complete) "
        f"transition; last state={last_state!r}. The saga is stuck."
    )
    assert last_state == "failed", f"expected saga to end in 'failed', got {last_state!r}"
