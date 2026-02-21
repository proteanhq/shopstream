"""Tests for the carrier adapter abstraction."""

from fulfillment.carrier.fake_adapter import FakeCarrier


class TestFakeCarrier:
    def test_create_shipment_success(self):
        carrier = FakeCarrier()
        result = carrier.create_shipment("ord-001", "FedEx", "Standard")
        assert result["shipment_id"] is not None
        assert result["tracking_number"] is not None
        assert result["label_url"] is not None
        assert "error" not in result

    def test_create_shipment_failure(self):
        carrier = FakeCarrier()
        carrier.configure(should_succeed=False, failure_reason="Service unavailable")
        result = carrier.create_shipment("ord-001", "FedEx", "Standard")
        assert result["shipment_id"] is None
        assert result["error"] == "Service unavailable"

    def test_get_tracking_success(self):
        carrier = FakeCarrier()
        result = carrier.get_tracking("FAKE-123456")
        assert result["status"] == "in_transit"
        assert len(result["events"]) == 2

    def test_get_tracking_failure(self):
        carrier = FakeCarrier()
        carrier.configure(should_succeed=False)
        result = carrier.get_tracking("FAKE-123456")
        assert result["status"] == "unknown"

    def test_cancel_shipment_success(self):
        carrier = FakeCarrier()
        result = carrier.cancel_shipment("FAKE-123456")
        assert result["cancelled"] is True

    def test_cancel_shipment_failure(self):
        carrier = FakeCarrier()
        carrier.configure(should_succeed=False)
        result = carrier.cancel_shipment("FAKE-123456")
        assert result["cancelled"] is False

    def test_verify_webhook_always_true(self):
        carrier = FakeCarrier()
        assert carrier.verify_webhook_signature("payload", "") is True
        assert carrier.verify_webhook_signature("payload", "any-sig") is True

    def test_configure_changes_behavior(self):
        carrier = FakeCarrier()
        assert carrier.should_succeed is True
        carrier.configure(should_succeed=False, failure_reason="Custom error")
        assert carrier.should_succeed is False
        assert carrier.failure_reason == "Custom error"

    def test_tracking_number_format(self):
        carrier = FakeCarrier()
        result = carrier.create_shipment("ord-001", "FedEx", "Standard")
        assert result["tracking_number"].startswith("FAKE-")

    def test_label_url_format(self):
        carrier = FakeCarrier()
        result = carrier.create_shipment("ord-001", "FedEx", "Standard")
        assert result["label_url"].startswith("https://")
        assert result["label_url"].endswith(".pdf")
