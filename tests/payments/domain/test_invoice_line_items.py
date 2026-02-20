"""Tests for InvoiceLineItem entity."""

from payments.invoice.invoice import InvoiceLineItem


class TestInvoiceLineItem:
    def test_construction(self):
        item = InvoiceLineItem(
            description="Black T-Shirt (M)",
            quantity=2,
            unit_price=29.99,
            total=59.98,
        )
        assert item.description == "Black T-Shirt (M)"
        assert item.quantity == 2
        assert item.unit_price == 29.99
        assert item.total == 59.98

    def test_total_calculated_in_aggregate(self):
        """Line item totals are calculated by the Invoice factory."""
        from payments.invoice.invoice import Invoice

        invoice = Invoice.create(
            order_id="ord-001",
            customer_id="cust-001",
            line_items_data=[
                {"description": "Item A", "quantity": 3, "unit_price": 10.00},
            ],
        )
        assert len(invoice.line_items) == 1
        item = invoice.line_items[0]
        assert item.total == 30.00
