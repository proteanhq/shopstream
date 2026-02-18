"""Faker-based data generators for Locust load test scenarios.

Each generator produces payloads that pass the domain's validation rules
(EmailAddress VO, PhoneNumber VO, SKU VO, etc.) and match the exact field
names expected by the API's Pydantic request schemas.
"""

import json
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
        "attributes": json.dumps({"size": random.choice(["S", "M", "L", "XL"])}),
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


def category_attributes() -> str:
    """Generate valid JSON string for category attributes.

    The command handler does json.loads() on this field, so it must be valid JSON.
    """
    attrs = {
        "season": random.choice(["spring", "summer", "fall", "winter", "all"]),
        "gender": random.choice(["men", "women", "unisex", "kids"]),
    }
    return json.dumps(attrs)


def category_name() -> str:
    """Generate a category name like 'Casual Footwear'."""
    return f"{fake.word().capitalize()} {fake.word().capitalize()}"[:100]
