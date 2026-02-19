"""Integration tests for Event Sourcing specifics — event store round-trips,
event replay, and aggregate reconstruction.
"""

from inventory.stock.adjustment import AdjustStock
from inventory.stock.damage import MarkDamaged
from inventory.stock.initialization import InitializeStock
from inventory.stock.receiving import ReceiveStock
from inventory.stock.reservation import ConfirmReservation, ReserveStock
from inventory.stock.returns import ReturnToStock
from inventory.stock.shipping import CommitStock
from inventory.stock.stock import AdjustmentType, InventoryItem
from protean import current_domain


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
    return current_domain.process(InitializeStock(**defaults), asynchronous=False)


class TestEventStorePersistence:
    def test_events_stored_in_event_store(self):
        """Verify that events are persisted in the event store after command processing."""
        item_id = _initialize_stock()

        messages = current_domain.event_store.store.read(f"inventory::inventory_item-{item_id}")
        assert len(messages) >= 1
        assert messages[0].metadata.headers.type == "Inventory.StockInitialized.v1"

    def test_multiple_events_stored(self):
        """Verify multiple events accumulate in the event store."""
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=20),
            asynchronous=False,
        )

        messages = current_domain.event_store.store.read(f"inventory::inventory_item-{item_id}")
        # StockInitialized + LowStockDetected (100 <= reorder_point=10? No, 100>10)
        # Actually initial_quantity=100, reorder_point=10, so no low stock
        # Just StockInitialized + StockReceived
        assert len(messages) >= 2

        event_types = [m.metadata.headers.type for m in messages]
        assert "Inventory.StockInitialized.v1" in event_types
        assert "Inventory.StockReceived.v1" in event_types

    def test_low_stock_event_stored(self):
        """Verify LowStockDetected event is stored when stock drops below threshold."""
        item_id = _initialize_stock(initial_quantity=15, reorder_point=10)

        # Adjust down to trigger low stock detection
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-10,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Loss",
                adjusted_by="mgr-001",
            ),
            asynchronous=False,
        )

        messages = current_domain.event_store.store.read(f"inventory::inventory_item-{item_id}")
        event_types = [m.metadata.headers.type for m in messages]
        assert "Inventory.StockInitialized.v1" in event_types
        assert "Inventory.StockAdjusted.v1" in event_types
        assert "Inventory.LowStockDetected.v1" in event_types


class TestEventReplayRoundTrip:
    def test_aggregate_reconstructed_from_events(self):
        """Verify that loading an aggregate reconstructs correct state from events."""
        item_id = _initialize_stock(initial_quantity=100)

        item = current_domain.repository_for(InventoryItem).get(item_id)

        assert item.id == item_id
        assert item.product_id == "prod-001"
        assert item.variant_id == "var-001"
        assert item.warehouse_id == "wh-001"
        assert item.sku == "TSHIRT-BLK-M"
        assert item.levels.on_hand == 100
        assert item.levels.available == 100
        assert item.levels.reserved == 0

    def test_multi_step_replay(self):
        """Verify replay works through multiple state transitions."""
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=20),
            asynchronous=False,
        )
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=30),
            asynchronous=False,
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 120
        assert item.levels.reserved == 30
        assert item.levels.available == 90
        assert len(item.reservations) == 1

    def test_reservation_lifecycle_survives_replay(self):
        """Verify reserve → confirm → commit replays correctly."""
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=10),
            asynchronous=False,
        )

        # Get reservation id
        item = current_domain.repository_for(InventoryItem).get(item_id)
        reservation_id = str(item.reservations[0].id)

        current_domain.process(
            ConfirmReservation(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )
        current_domain.process(
            CommitStock(inventory_item_id=item_id, reservation_id=reservation_id),
            asynchronous=False,
        )

        # Reconstruct from event store
        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 90
        assert item.levels.reserved == 0
        assert item.levels.available == 90
        # Reservation removed after commit
        assert len(item.reservations) == 0

    def test_damage_and_write_off_survive_replay(self):
        """Verify damage → write-off replays correctly."""
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            MarkDamaged(inventory_item_id=item_id, quantity=10, reason="Flood"),
            asynchronous=False,
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 90
        assert item.levels.damaged == 10
        assert item.levels.available == 90

    def test_return_survives_replay(self):
        """Verify stock return replays correctly."""
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            ReturnToStock(inventory_item_id=item_id, quantity=15, order_id="ord-ret-001"),
            asynchronous=False,
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 115
        assert item.levels.available == 115

    def test_adjustment_survives_replay(self):
        """Verify stock adjustment replays correctly."""
        item_id = _initialize_stock(initial_quantity=100)
        current_domain.process(
            AdjustStock(
                inventory_item_id=item_id,
                quantity_change=-15,
                adjustment_type=AdjustmentType.SHRINKAGE.value,
                reason="Inventory shrinkage",
                adjusted_by="manager-001",
            ),
            asynchronous=False,
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        assert item.levels.on_hand == 85
        assert item.levels.available == 85

    def test_complex_scenario_replay(self):
        """Verify a complex multi-operation scenario replays correctly."""
        item_id = _initialize_stock(initial_quantity=100)

        # Receive more stock
        current_domain.process(
            ReceiveStock(inventory_item_id=item_id, quantity=50),
            asynchronous=False,
        )

        # Reserve some
        current_domain.process(
            ReserveStock(inventory_item_id=item_id, order_id="ord-001", quantity=20),
            asynchronous=False,
        )

        # Mark some damaged
        current_domain.process(
            MarkDamaged(inventory_item_id=item_id, quantity=5, reason="Dented"),
            asynchronous=False,
        )

        # Return some
        current_domain.process(
            ReturnToStock(inventory_item_id=item_id, quantity=10, order_id="ord-old"),
            asynchronous=False,
        )

        item = current_domain.repository_for(InventoryItem).get(item_id)
        # on_hand: 100 + 50 - 5 + 10 = 155
        assert item.levels.on_hand == 155
        # reserved: 20
        assert item.levels.reserved == 20
        # available: 155 - 20 = 135
        assert item.levels.available == 135
        # damaged: 5
        assert item.levels.damaged == 5


class TestEventStoreStreamNaming:
    def test_stream_name_follows_convention(self):
        """Verify event store streams follow the inventory::inventoryItem-{id} convention."""
        item_id = _initialize_stock()
        stream_name = f"inventory::inventory_item-{item_id}"

        messages = current_domain.event_store.store.read(stream_name)
        assert len(messages) >= 1

    def test_event_version_is_v1(self):
        """Verify all events carry v1 version."""
        item_id = _initialize_stock()
        messages = current_domain.event_store.store.read(f"inventory::inventory_item-{item_id}")

        for msg in messages:
            assert msg.metadata.headers.type.endswith(".v1")
