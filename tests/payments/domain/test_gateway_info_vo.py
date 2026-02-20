"""Tests for GatewayInfo value object."""

from payments.payment.payment import GatewayInfo


class TestGatewayInfo:
    def test_basic_construction(self):
        gi = GatewayInfo(gateway_name="FakeGateway")
        assert gi.gateway_name == "FakeGateway"

    def test_full_construction(self):
        gi = GatewayInfo(
            gateway_name="FakeGateway",
            gateway_transaction_id="txn-123",
            gateway_status="succeeded",
            gateway_response="Charge successful",
        )
        assert gi.gateway_transaction_id == "txn-123"
        assert gi.gateway_status == "succeeded"
        assert gi.gateway_response == "Charge successful"

    def test_optional_fields(self):
        gi = GatewayInfo(gateway_name="StripeGateway")
        assert gi.gateway_transaction_id is None
        assert gi.gateway_status is None
