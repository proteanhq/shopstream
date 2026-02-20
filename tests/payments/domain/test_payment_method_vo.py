"""Tests for PaymentMethod value object."""

from payments.payment.payment import PaymentMethod


class TestPaymentMethod:
    def test_credit_card(self):
        pm = PaymentMethod(method_type="credit_card", last4="4242")
        assert pm.method_type == "credit_card"
        assert pm.last4 == "4242"

    def test_debit_card(self):
        pm = PaymentMethod(method_type="debit_card", last4="1234")
        assert pm.method_type == "debit_card"

    def test_with_expiry(self):
        pm = PaymentMethod(
            method_type="credit_card",
            last4="4242",
            expiry_month=12,
            expiry_year=2025,
        )
        assert pm.expiry_month == 12
        assert pm.expiry_year == 2025

    def test_optional_fields(self):
        pm = PaymentMethod(method_type="bank_transfer")
        assert pm.last4 is None
        assert pm.expiry_month is None
