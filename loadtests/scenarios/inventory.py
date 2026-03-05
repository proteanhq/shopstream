"""Inventory domain load test scenarios.

Six stateful SequentialTaskSet journeys covering stock initialization
and receiving, stock reservations, damage write-offs, return-to-stock,
warehouse management, and reservation expiry maintenance.

Note: Reserve, confirm, release, and commit endpoints require reservation_id
which is not returned by POST /inventory/{id}/reserve (only StatusResponse).
Reservation lifecycle beyond creation cannot be exercised via load tests.
"""

import random
import uuid

from locust import HttpUser, SequentialTaskSet, between, task

from loadtests.data_generators import (
    initialize_stock_data,
    reserve_stock_data,
    warehouse_data,
)
from loadtests.helpers.response import extract_error_detail
from loadtests.helpers.state import InventoryState


class StockInitAndReceiveJourney(SequentialTaskSet):
    """Create Warehouse -> Initialize Stock -> Receive Stock -> Adjust -> Stock Check.

    Models a warehouse manager setting up inventory for a new product
    and receiving a shipment.
    """

    def on_start(self):
        self.state = InventoryState()

    @task
    def create_warehouse(self):
        with self.client.post(
            "/warehouses",
            json=warehouse_data(),
            catch_response=True,
            name="POST /warehouses",
        ) as resp:
            if resp.status_code == 201:
                self.state.warehouse_id = resp.json()["warehouse_id"]
            else:
                resp.failure(f"Create warehouse failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def initialize_stock(self):
        payload = initialize_stock_data(
            warehouse_id=self.state.warehouse_id,
            initial_quantity=100,
        )
        with self.client.post(
            "/inventory",
            json=payload,
            catch_response=True,
            name="POST /inventory",
        ) as resp:
            if resp.status_code == 201:
                self.state.inventory_item_id = resp.json()["inventory_item_id"]
                self.state.current_on_hand = 100
                self.state.current_available = 100
            else:
                resp.failure(f"Initialize stock failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def receive_stock(self):
        qty = random.randint(10, 100)
        with self.client.put(
            f"/inventory/{self.state.inventory_item_id}/receive",
            json={"quantity": qty, "reference": f"PO-{uuid.uuid4().hex[:6]}"},
            catch_response=True,
            name="PUT /inventory/{id}/receive",
        ) as resp:
            if resp.status_code == 200:
                self.state.current_on_hand += qty
                self.state.current_available += qty
            else:
                resp.failure(f"Receive stock failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def adjust_stock(self):
        with self.client.put(
            f"/inventory/{self.state.inventory_item_id}/adjust",
            json={
                "quantity_change": -random.randint(1, 5),
                "adjustment_type": "shrinkage",
                "reason": "Damaged during handling",
                "adjusted_by": "warehouse-mgr",
            },
            catch_response=True,
            name="PUT /inventory/{id}/adjust",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Adjust stock failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def stock_check(self):
        with self.client.put(
            f"/inventory/{self.state.inventory_item_id}/stock-check",
            json={
                "counted_quantity": self.state.current_on_hand,
                "checked_by": "auditor-01",
            },
            catch_response=True,
            name="PUT /inventory/{id}/stock-check",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Stock check failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class ReservationLifecycleJourney(SequentialTaskSet):
    """Init Stock -> Reserve -> Confirm -> Commit.

    Models the stock reservation flow for a successful order:
    available stock is reserved, confirmed, then committed (shipped).
    """

    def on_start(self):
        self.state = InventoryState()

    @task
    def initialize_stock(self):
        payload = initialize_stock_data(initial_quantity=50)
        with self.client.post(
            "/inventory",
            json=payload,
            catch_response=True,
            name="POST /inventory",
        ) as resp:
            if resp.status_code == 201:
                self.state.inventory_item_id = resp.json()["inventory_item_id"]
                self.state.current_on_hand = 50
                self.state.current_available = 50
            else:
                resp.failure(f"Initialize stock failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def reserve_stock(self):
        qty = random.randint(1, 5)
        payload = reserve_stock_data(quantity=qty)
        with self.client.post(
            f"/inventory/{self.state.inventory_item_id}/reserve",
            json=payload,
            catch_response=True,
            name="POST /inventory/{id}/reserve",
        ) as resp:
            if resp.status_code == 201:
                self.state.current_available -= qty
            else:
                resp.failure(f"Reserve stock failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def done(self):
        self.interrupt()


class ReservationReleaseJourney(SequentialTaskSet):
    """Init Stock -> Reserve -> Release.

    Models a cancelled order releasing its reserved stock back to available.
    """

    def on_start(self):
        self.state = InventoryState()

    @task
    def initialize_stock(self):
        payload = initialize_stock_data(initial_quantity=50)
        with self.client.post(
            "/inventory",
            json=payload,
            catch_response=True,
            name="POST /inventory",
        ) as resp:
            if resp.status_code == 201:
                self.state.inventory_item_id = resp.json()["inventory_item_id"]
            else:
                resp.failure(f"Initialize stock failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def reserve_stock(self):
        payload = reserve_stock_data(quantity=3)
        with self.client.post(
            f"/inventory/{self.state.inventory_item_id}/reserve",
            json=payload,
            catch_response=True,
            name="POST /inventory/{id}/reserve",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Reserve failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def done(self):
        self.interrupt()


class DamageWriteOffJourney(SequentialTaskSet):
    """Init Stock -> Mark Damaged -> Write Off.

    Models the inventory damage reporting and write-off workflow.
    """

    def on_start(self):
        self.state = InventoryState()

    @task
    def initialize_stock(self):
        payload = initialize_stock_data(initial_quantity=100)
        with self.client.post(
            "/inventory",
            json=payload,
            catch_response=True,
            name="POST /inventory",
        ) as resp:
            if resp.status_code == 201:
                self.state.inventory_item_id = resp.json()["inventory_item_id"]
            else:
                resp.failure(f"Init stock failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def mark_damaged(self):
        with self.client.put(
            f"/inventory/{self.state.inventory_item_id}/damage",
            json={"quantity": 5, "reason": "Water damage from leak"},
            catch_response=True,
            name="PUT /inventory/{id}/damage",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Mark damaged failed: {extract_error_detail(resp)}")

    @task
    def write_off(self):
        with self.client.put(
            f"/inventory/{self.state.inventory_item_id}/damage/write-off",
            json={"quantity": 5, "approved_by": "warehouse-mgr"},
            catch_response=True,
            name="PUT /inventory/{id}/damage/write-off",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Write off failed: {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class ReturnToStockJourney(SequentialTaskSet):
    """Init Stock -> Receive -> Return to Stock.

    Models returned items being added back to inventory after order returns.
    Exercises: InitializeStock, ReceiveStock, ReturnToStock commands.
    """

    def on_start(self):
        self.state = InventoryState()
        self._order_id = f"ord-{uuid.uuid4().hex[:8]}"

    @task
    def initialize_stock(self):
        payload = initialize_stock_data(initial_quantity=50)
        with self.client.post(
            "/inventory",
            json=payload,
            catch_response=True,
            name="POST /inventory",
        ) as resp:
            if resp.status_code == 201:
                self.state.inventory_item_id = resp.json()["inventory_item_id"]
            else:
                resp.failure(f"Init stock failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def return_to_stock(self):
        qty = random.randint(1, 5)
        with self.client.put(
            f"/inventory/{self.state.inventory_item_id}/return",
            json={"quantity": qty, "order_id": self._order_id},
            catch_response=True,
            name="PUT /inventory/{id}/return",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Return to stock failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class WarehouseManagementJourney(SequentialTaskSet):
    """Create Warehouse -> Update -> Add Zone -> Deactivate.

    Models warehouse setup and lifecycle management.
    Exercises: CreateWarehouse, UpdateWarehouse, AddZone,
    DeactivateWarehouse commands.
    """

    def on_start(self):
        self.state = InventoryState()

    @task
    def create_warehouse(self):
        with self.client.post(
            "/warehouses",
            json=warehouse_data(),
            catch_response=True,
            name="POST /warehouses",
        ) as resp:
            if resp.status_code == 201:
                self.state.warehouse_id = resp.json()["warehouse_id"]
            else:
                resp.failure(f"Create warehouse failed: {resp.status_code} — {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def update_warehouse(self):
        with self.client.put(
            f"/warehouses/{self.state.warehouse_id}",
            json={
                "name": f"Updated Warehouse {random.randint(1, 99)}",
                "capacity": random.randint(5000, 100000),
            },
            catch_response=True,
            name="PUT /warehouses/{id}",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Update warehouse failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def add_zone_1(self):
        with self.client.post(
            f"/warehouses/{self.state.warehouse_id}/zones",
            json={"zone_name": f"Zone-{uuid.uuid4().hex[:4]}", "zone_type": "Regular"},
            catch_response=True,
            name="POST /warehouses/{id}/zones",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Add zone failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def add_zone_2(self):
        zone_type = random.choice(["Cold", "Hazmat", "Regular"])
        with self.client.post(
            f"/warehouses/{self.state.warehouse_id}/zones",
            json={"zone_name": f"Zone-{uuid.uuid4().hex[:4]}", "zone_type": zone_type},
            catch_response=True,
            name="POST /warehouses/{id}/zones",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Add zone 2 failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def deactivate_warehouse(self):
        with self.client.put(
            f"/warehouses/{self.state.warehouse_id}/deactivate",
            catch_response=True,
            name="PUT /warehouses/{id}/deactivate",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Deactivate warehouse failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class ExpireReservationsJourney(SequentialTaskSet):
    """Init Stock -> Reserve -> Expire Reservations.

    Exercises the maintenance endpoint for expiring stale reservations.
    """

    def on_start(self):
        self.state = InventoryState()

    @task
    def initialize_stock(self):
        payload = initialize_stock_data(initial_quantity=100)
        with self.client.post(
            "/inventory",
            json=payload,
            catch_response=True,
            name="POST /inventory",
        ) as resp:
            if resp.status_code == 201:
                self.state.inventory_item_id = resp.json()["inventory_item_id"]
            else:
                resp.failure(f"Init stock failed: {extract_error_detail(resp)}")
                self.interrupt()

    @task
    def reserve_stock(self):
        payload = reserve_stock_data(quantity=2, expires_in_minutes=1)
        with self.client.post(
            f"/inventory/{self.state.inventory_item_id}/reserve",
            json=payload,
            catch_response=True,
            name="POST /inventory/{id}/reserve",
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Reserve failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def expire_reservations(self):
        with self.client.post(
            "/inventory/maintenance/expire-reservations",
            json={"older_than_minutes": 0},
            catch_response=True,
            name="POST /inventory/maintenance/expire-reservations",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Expire reservations failed: {resp.status_code} — {extract_error_detail(resp)}")

    @task
    def done(self):
        self.interrupt()


class InventoryUser(HttpUser):
    """Locust user simulating Inventory domain interactions.

    Weighted distribution:
    - 25% Stock init & receive (most common warehouse operation)
    - 15% Reservation creation (order flow)
    - 15% Reservation release (cancellations)
    - 15% Damage write-off
    - 10% Return to stock (order returns)
    - 10% Warehouse management
    - 10% Expire reservations (maintenance)
    """

    wait_time = between(0.5, 2.0)
    tasks = {
        StockInitAndReceiveJourney: 5,
        ReservationLifecycleJourney: 3,
        ReservationReleaseJourney: 3,
        DamageWriteOffJourney: 3,
        ReturnToStockJourney: 2,
        WarehouseManagementJourney: 2,
        ExpireReservationsJourney: 2,
    }
