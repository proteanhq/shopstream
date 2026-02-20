"""Tests for gateway port/adapter integration."""

import pytest
from payments.gateway import get_gateway, reset_gateway, set_gateway
from payments.gateway.fake_adapter import FakeGateway
from payments.gateway.port import ChargeResult, RefundResult
from payments.gateway.stripe_adapter import StripeGateway


class TestFakeGateway:
    def test_default_charge_succeeds(self):
        gateway = FakeGateway()
        result = gateway.create_charge(
            amount=59.99,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key="test-1",
        )
        assert isinstance(result, ChargeResult)
        assert result.success is True
        assert result.gateway_transaction_id is not None
        assert result.gateway_status == "succeeded"

    def test_configured_charge_fails(self):
        gateway = FakeGateway()
        gateway.configure(should_succeed=False, failure_reason="Insufficient funds")
        result = gateway.create_charge(
            amount=59.99,
            currency="USD",
            payment_method_type="credit_card",
            last4="4242",
            idempotency_key="test-2",
        )
        assert result.success is False
        assert result.failure_reason == "Insufficient funds"

    def test_default_refund_succeeds(self):
        gateway = FakeGateway()
        result = gateway.create_refund(
            gateway_transaction_id="txn-123",
            amount=30.00,
            reason="Defective",
        )
        assert isinstance(result, RefundResult)
        assert result.success is True
        assert result.gateway_refund_id is not None

    def test_configured_refund_fails(self):
        gateway = FakeGateway()
        gateway.configure(should_succeed=False, failure_reason="Refund limit exceeded")
        result = gateway.create_refund(
            gateway_transaction_id="txn-123",
            amount=30.00,
            reason="Test",
        )
        assert result.success is False

    def test_webhook_signature_verification(self):
        gateway = FakeGateway()
        assert gateway.verify_webhook_signature("payload", "test-signature") is True
        assert gateway.verify_webhook_signature("payload", "wrong-signature") is False

    def test_call_logging(self):
        gateway = FakeGateway()
        gateway.create_charge(
            amount=10.00,
            currency="USD",
            payment_method_type="credit_card",
            last4="1234",
            idempotency_key="test-log",
        )
        assert len(gateway.calls) == 1
        assert gateway.calls[0]["method"] == "create_charge"
        assert gateway.calls[0]["amount"] == 10.00


class TestGatewayFactory:
    def test_get_gateway_returns_fake_by_default(self):
        reset_gateway()
        gateway = get_gateway()
        assert isinstance(gateway, FakeGateway)

    def test_set_gateway_overrides(self):
        custom = FakeGateway()
        custom.configure(should_succeed=False)
        set_gateway(custom)
        gateway = get_gateway()
        assert gateway.should_succeed is False
        reset_gateway()

    def test_reset_gateway(self):
        custom = FakeGateway()
        custom.configure(should_succeed=False)
        set_gateway(custom)
        reset_gateway()
        gateway = get_gateway()
        assert gateway.should_succeed is True


class TestStripeGateway:
    def test_constructor_stores_credentials(self):
        gateway = StripeGateway(api_key="sk_test_123", webhook_secret="whsec_456")
        assert gateway.api_key == "sk_test_123"
        assert gateway.webhook_secret == "whsec_456"

    def test_create_charge_not_implemented(self):
        gateway = StripeGateway(api_key="sk_test_123", webhook_secret="whsec_456")
        with pytest.raises(NotImplementedError):
            gateway.create_charge(
                amount=59.99,
                currency="USD",
                payment_method_type="credit_card",
                last4="4242",
                idempotency_key="test-stripe-1",
            )

    def test_create_refund_not_implemented(self):
        gateway = StripeGateway(api_key="sk_test_123", webhook_secret="whsec_456")
        with pytest.raises(NotImplementedError):
            gateway.create_refund(
                gateway_transaction_id="txn-123",
                amount=30.00,
                reason="Test",
            )

    def test_verify_webhook_not_implemented(self):
        gateway = StripeGateway(api_key="sk_test_123", webhook_secret="whsec_456")
        with pytest.raises(NotImplementedError):
            gateway.verify_webhook_signature("payload", "sig")
