"""Faker-based data generators for Locust load test scenarios.

Each generator produces payloads that pass the domain's validation rules
(EmailAddress VO, PhoneNumber VO, SKU VO, etc.) and match the exact field
names expected by the API's Pydantic request schemas.
"""

import random
import uuid

from faker import Faker

fake = Faker()

# ---------- Identity Domain ----------


def unique_external_id() -> str:
    """Generate unique external IDs like 'EXT-LT-a1b2c3d4'."""
    return f"EXT-LT-{uuid.uuid4().hex[:8]}"


def valid_email() -> str:
    """Generate emails that pass EmailAddress VO validation.

    Rules: exactly one @, no spaces/tabs, valid domain with dot,
    no leading/trailing dots, no consecutive dots.
    """
    local = fake.user_name()[:20]
    domain = fake.free_email_domain()
    return f"{local}.{uuid.uuid4().hex[:4]}@{domain}"


def valid_phone() -> str:
    """Generate phones matching PhoneNumber VO regex: ^\\+?[\\d\\s\\-()]+$"""
    area = random.randint(200, 999)
    prefix = random.randint(200, 999)
    line = random.randint(1000, 9999)
    return f"+1-{area}-{prefix}-{line}"


def customer_name() -> tuple[str, str]:
    """Generate (first_name, last_name) within 100-char max."""
    return fake.first_name()[:100], fake.last_name()[:100]


def date_of_birth() -> str:
    """Generate ISO date string for age 18-80."""
    return fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat()


def address_data() -> dict:
    """Generate AddAddressRequest payload matching schema field names."""
    return {
        "label": random.choice(["Home", "Work", "Other"]),
        "street": fake.street_address()[:255],
        "city": fake.city()[:100],
        "state": fake.state_abbr(),
        "postal_code": fake.zipcode()[:20],
        "country": "US",
        "geo_lat": str(round(random.uniform(25.0, 48.0), 4)),
        "geo_lng": str(round(random.uniform(-125.0, -70.0), 4)),
    }


# ---------- Catalogue Domain ----------


def valid_sku(prefix: str = "LT") -> str:
    """Generate SKU passing SKU VO validation: 3-50 chars, alphanumeric + hyphens,
    no leading/trailing/consecutive hyphens."""
    suffix = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{suffix}"


def product_data(sku: str | None = None) -> dict:
    """Generate CreateProductRequest payload matching schema field names."""
    sku = sku or valid_sku("PROD")
    word = fake.word().capitalize()
    slug_base = word.lower()
    return {
        "sku": sku,
        "seller_id": f"seller-{uuid.uuid4().hex[:6]}",
        "title": f"{word} {fake.word().capitalize()} Product"[:255],
        "description": fake.paragraph(nb_sentences=3),
        "brand": fake.company()[:100],
        "visibility": random.choice(["Public", "Unlisted", "Tier_Restricted"]),
        "meta_title": f"{word} Product"[:70],
        "meta_description": fake.sentence()[:160],
        "slug": f"{slug_base}-{uuid.uuid4().hex[:6]}"[:200],
    }


def variant_data(variant_sku: str | None = None) -> dict:
    """Generate AddVariantRequest payload matching schema field names."""
    return {
        "variant_sku": variant_sku or valid_sku("VAR"),
        "attributes": {"size": random.choice(["S", "M", "L", "XL"])},
        "base_price": round(random.uniform(9.99, 299.99), 2),
        "currency": "USD",
        "weight_value": round(random.uniform(0.1, 5.0), 2),
        "weight_unit": "kg",
        "length": round(random.uniform(5.0, 50.0), 1),
        "width": round(random.uniform(5.0, 40.0), 1),
        "height": round(random.uniform(1.0, 30.0), 1),
        "dimension_unit": "cm",
    }


def image_data(is_primary: bool = False) -> dict:
    """Generate AddProductImageRequest payload matching schema field names."""
    return {
        "url": f"https://cdn.example.com/images/{uuid.uuid4().hex}.jpg",
        "alt_text": fake.sentence(nb_words=5)[:255],
        "is_primary": is_primary,
    }


def category_attributes() -> dict:
    """Generate category attributes dict."""
    return {
        "season": random.choice(["spring", "summer", "fall", "winter", "all"]),
        "gender": random.choice(["men", "women", "unisex", "kids"]),
    }


def category_name() -> str:
    """Generate a category name like 'Casual Footwear'."""
    return f"{fake.word().capitalize()} {fake.word().capitalize()}"[:100]


# ---------- Ordering Domain ----------


def order_address() -> dict:
    """Generate AddressSchema payload for order shipping/billing."""
    return {
        "street": fake.street_address()[:255],
        "city": fake.city()[:100],
        "state": fake.state_abbr(),
        "postal_code": fake.zipcode()[:20],
        "country": "US",
    }


def order_item(product_id: str | None = None, variant_id: str | None = None) -> dict:
    """Generate OrderItemSchema payload for order creation."""
    return {
        "product_id": product_id or f"prod-{uuid.uuid4().hex[:8]}",
        "variant_id": variant_id or f"var-{uuid.uuid4().hex[:8]}",
        "sku": valid_sku("ORD"),
        "title": f"{fake.word().capitalize()} {fake.word().capitalize()}"[:100],
        "quantity": random.randint(1, 5),
        "unit_price": round(random.uniform(9.99, 199.99), 2),
    }


def order_data(customer_id: str | None = None, num_items: int = 2) -> dict:
    """Generate CreateOrderRequest payload."""
    items = [order_item() for _ in range(num_items)]
    return {
        "customer_id": customer_id or f"cust-{uuid.uuid4().hex[:8]}",
        "items": items,
        "shipping_address": order_address(),
        "billing_address": order_address(),
        "shipping_cost": round(random.uniform(0, 15.99), 2),
        "tax_total": round(random.uniform(0, 25.0), 2),
        "discount_total": 0.0,
        "currency": "USD",
    }


def cart_data(customer_id: str | None = None) -> dict:
    """Generate CreateCartRequest payload."""
    return {
        "customer_id": customer_id or f"cust-{uuid.uuid4().hex[:8]}",
    }


def cart_item_data() -> dict:
    """Generate AddToCartRequest payload."""
    return {
        "product_id": f"prod-{uuid.uuid4().hex[:8]}",
        "variant_id": f"var-{uuid.uuid4().hex[:8]}",
        "quantity": random.randint(1, 3),
    }


def checkout_data() -> dict:
    """Generate CheckoutRequest payload."""
    return {
        "shipping": order_address(),
        "billing": order_address(),
        "payment_method": random.choice(["credit_card", "debit_card", "wallet"]),
    }


def shipment_data() -> dict:
    """Generate RecordShipmentRequest payload."""
    carriers = ["FedEx", "UPS", "USPS", "DHL"]
    return {
        "shipment_id": f"ship-{uuid.uuid4().hex[:8]}",
        "carrier": random.choice(carriers),
        "tracking_number": f"TRK{uuid.uuid4().hex[:12].upper()}",
        "estimated_delivery": fake.future_date(end_date="+14d").isoformat(),
    }


# ---------- Inventory Domain ----------


def warehouse_data() -> dict:
    """Generate CreateWarehouseRequest payload."""
    return {
        "name": f"{fake.city()} Warehouse {random.randint(1, 99)}",
        "address": order_address(),
        "capacity": random.randint(1000, 50000),
    }


def initialize_stock_data(
    product_id: str | None = None,
    variant_id: str | None = None,
    warehouse_id: str | None = None,
    initial_quantity: int | None = None,
) -> dict:
    """Generate InitializeStockRequest payload."""
    return {
        "product_id": product_id or f"prod-{uuid.uuid4().hex[:8]}",
        "variant_id": variant_id or f"var-{uuid.uuid4().hex[:8]}",
        "warehouse_id": warehouse_id or f"wh-{uuid.uuid4().hex[:8]}",
        "sku": valid_sku("INV"),
        "initial_quantity": initial_quantity if initial_quantity is not None else random.randint(10, 500),
        "reorder_point": 10,
        "reorder_quantity": 50,
    }


def reserve_stock_data(
    order_id: str | None = None,
    quantity: int = 1,
    expires_in_minutes: int = 15,
) -> dict:
    """Generate ReserveStockRequest payload."""
    return {
        "order_id": order_id or f"ord-{uuid.uuid4().hex[:8]}",
        "quantity": quantity,
        "expires_in_minutes": expires_in_minutes,
    }


# ---------- Payments Domain ----------


def payment_data(
    order_id: str | None = None,
    customer_id: str | None = None,
    amount: float | None = None,
) -> dict:
    """Generate InitiatePaymentRequest payload."""
    return {
        "order_id": order_id or f"ord-{uuid.uuid4().hex[:8]}",
        "customer_id": customer_id or f"cust-{uuid.uuid4().hex[:8]}",
        "amount": amount or round(random.uniform(19.99, 499.99), 2),
        "currency": "USD",
        "payment_method_type": random.choice(["credit_card", "debit_card", "wallet"]),
        "last4": str(random.randint(1000, 9999)),
        "idempotency_key": f"idem-{uuid.uuid4().hex[:12]}",
    }


def webhook_data_success(payment_id: str) -> dict:
    """Generate ProcessWebhookRequest payload for successful payment."""
    return {
        "payment_id": payment_id,
        "gateway_transaction_id": f"gtx-{uuid.uuid4().hex[:12]}",
        "gateway_status": "succeeded",
    }


def webhook_data_failure(payment_id: str) -> dict:
    """Generate ProcessWebhookRequest payload for failed payment."""
    reasons = ["Card declined", "Insufficient funds", "Card expired", "Processing error"]
    return {
        "payment_id": payment_id,
        "gateway_transaction_id": f"gtx-{uuid.uuid4().hex[:12]}",
        "gateway_status": "failed",
        "failure_reason": random.choice(reasons),
    }


def invoice_data(order_id: str | None = None, customer_id: str | None = None) -> dict:
    """Generate GenerateInvoiceRequest payload."""
    num_items = random.randint(1, 4)
    return {
        "order_id": order_id or f"ord-{uuid.uuid4().hex[:8]}",
        "customer_id": customer_id or f"cust-{uuid.uuid4().hex[:8]}",
        "line_items": [
            {
                "description": f"{fake.word().capitalize()} {fake.word().capitalize()}"[:100],
                "quantity": random.randint(1, 5),
                "unit_price": round(random.uniform(9.99, 99.99), 2),
            }
            for _ in range(num_items)
        ],
        "tax": round(random.uniform(0, 30.0), 2),
    }


# ---------- Fulfillment Domain ----------


def fulfillment_item_data() -> dict:
    """Generate FulfillmentItemRequest payload."""
    return {
        "order_item_id": f"oi-{uuid.uuid4().hex[:8]}",
        "product_id": f"prod-{uuid.uuid4().hex[:8]}",
        "sku": valid_sku("FUL"),
        "quantity": random.randint(1, 3),
    }


def fulfillment_data(
    order_id: str | None = None,
    customer_id: str | None = None,
    num_items: int | None = None,
) -> dict:
    """Generate CreateFulfillmentRequest payload."""
    num = num_items or random.randint(1, 4)
    return {
        "order_id": order_id or f"ord-{uuid.uuid4().hex[:8]}",
        "customer_id": customer_id or f"cust-{uuid.uuid4().hex[:8]}",
        "items": [fulfillment_item_data() for _ in range(num)],
    }


# ---------- Reviews Domain ----------


_REVIEW_PROS = [
    "Great quality",
    "Fast shipping",
    "Good value",
    "Easy to use",
    "Durable",
    "Looks great",
    "Comfortable",
    "As described",
]

_REVIEW_CONS = [
    "Pricey",
    "Slow delivery",
    "Bulky packaging",
    "Minor defect",
    "Runs small",
    "Color slightly off",
    "Instructions unclear",
]


def review_data(
    product_id: str | None = None,
    customer_id: str | None = None,
) -> dict:
    """Generate SubmitReviewRequest payload."""
    rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 15, 35, 35])[0]
    body = fake.paragraph(nb_sentences=random.randint(3, 5))
    if len(body) < 20:
        body = body + " " + fake.sentence()
    return {
        "product_id": product_id or f"prod-{uuid.uuid4().hex[:8]}",
        "customer_id": customer_id or f"cust-{uuid.uuid4().hex[:8]}",
        "rating": rating,
        "title": fake.sentence(nb_words=random.randint(3, 8))[:200],
        "body": body,
        "pros": random.sample(_REVIEW_PROS, k=random.randint(1, 3)),
        "cons": random.sample(_REVIEW_CONS, k=random.randint(0, 2)),
    }


def edit_review_data(customer_id: str) -> dict:
    """Generate EditReviewRequest payload with updated content."""
    body = fake.paragraph(nb_sentences=random.randint(3, 5))
    if len(body) < 20:
        body = body + " " + fake.sentence()
    return {
        "customer_id": customer_id,
        "title": fake.sentence(nb_words=random.randint(3, 8))[:200],
        "body": body,
        "rating": random.randint(1, 5),
    }


# ---------- Notifications Domain ----------

_NOTIFICATION_TYPES = [
    "CartRecovery",
    "OrderConfirmation",
    "ShippingUpdate",
    "DeliveryConfirmation",
    "ReviewRequest",
    "PriceAlert",
    "BackInStock",
    "Promotional",
]


def notification_preferences_data() -> dict:
    """Generate UpdatePreferencesRequest payload."""
    return {
        "email_enabled": random.choice([True, False]),
        "sms_enabled": random.choice([True, False]),
        "push_enabled": random.choice([True, False]),
    }


def quiet_hours_data() -> dict:
    """Generate SetQuietHoursRequest payload."""
    start_hour = random.randint(20, 23)
    end_hour = random.randint(6, 9)
    return {
        "start": f"{start_hour:02d}:00",
        "end": f"{end_hour:02d}:00",
    }


def notification_type() -> str:
    """Return a random NotificationType enum value."""
    return random.choice(_NOTIFICATION_TYPES)
