"""Application tests for carrier adapter integration."""

from fulfillment.carrier import get_carrier, reset_carrier
from fulfillment.carrier.fake_adapter import FakeCarrier


class TestFakeCarrierIntegration:
    def setup_method(self):
        reset_carrier()

    def test_get_carrier_returns_fake_carrier(self):
        carrier = get_carrier()
        assert isinstance(carrier, FakeCarrier)

    def test_create_shipment_success(self):
        carrier = get_carrier()
        result = carrier.create_shipment(
            order_id="ord-001",
            carrier="FakeCarrier",
            service_level="Standard",
        )
        assert result["shipment_id"] is not None
        assert result["tracking_number"] is not None
        assert result["tracking_number"].startswith("FAKE-")
        assert result["label_url"] is not None
        assert result["estimated_delivery"] is not None
        assert "error" not in result

    def test_create_shipment_failure(self):
        carrier = get_carrier()
        carrier.configure(should_succeed=False, failure_reason="Carrier down")
        result = carrier.create_shipment(
            order_id="ord-001",
            carrier="FakeCarrier",
            service_level="Express",
        )
        assert result["shipment_id"] is None
        assert result["error"] == "Carrier down"

    def test_get_tracking_success(self):
        carrier = get_carrier()
        result = carrier.get_tracking("FAKE-ABC123")
        assert result["status"] == "in_transit"
        assert result["location"] is not None
        assert len(result["events"]) == 2

    def test_get_tracking_failure(self):
        carrier = get_carrier()
        carrier.configure(should_succeed=False)
        result = carrier.get_tracking("FAKE-ABC123")
        assert result["status"] == "unknown"
        assert result["error"] is not None

    def test_cancel_shipment_success(self):
        carrier = get_carrier()
        result = carrier.cancel_shipment("FAKE-ABC123")
        assert result["cancelled"] is True

    def test_cancel_shipment_failure(self):
        carrier = get_carrier()
        carrier.configure(should_succeed=False, failure_reason="Already shipped")
        result = carrier.cancel_shipment("FAKE-ABC123")
        assert result["cancelled"] is False
        assert result["reason"] == "Already shipped"

    def test_verify_webhook_signature(self):
        carrier = get_carrier()
        assert carrier.verify_webhook_signature("any-payload", "any-signature") is True

    def test_express_delivery_estimate(self):
        carrier = get_carrier()
        result = carrier.create_shipment(
            order_id="ord-002",
            carrier="FakeCarrier",
            service_level="Express",
        )
        assert result["estimated_delivery"] is not None

    def test_overnight_delivery_estimate(self):
        carrier = get_carrier()
        result = carrier.create_shipment(
            order_id="ord-003",
            carrier="FakeCarrier",
            service_level="Overnight",
        )
        assert result["estimated_delivery"] is not None

    def test_configure_resets_behavior(self):
        carrier = get_carrier()
        carrier.configure(should_succeed=False)
        result = carrier.create_shipment(order_id="ord-001", carrier="FC", service_level="Standard")
        assert result["shipment_id"] is None

        carrier.configure(should_succeed=True)
        result = carrier.create_shipment(order_id="ord-001", carrier="FC", service_level="Standard")
        assert result["shipment_id"] is not None
