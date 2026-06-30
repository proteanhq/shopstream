"""Seed baseline data for load testing.

Creates a realistic initial state: customers, products with variants,
categories, warehouses, and inventory. Run standalone or opt-in via
the LOADTEST_SEED=1 env var when starting Locust.

Usage:
    # Standalone:
    python -m loadtests.seed --host http://localhost:8000

    # Via Locust (opt-in):
    LOADTEST_SEED=1 locust -f loadtests/locustfile.py
"""

import argparse
import sys

import requests

from loadtests.data_generators import (
    category_name,
    customer_name,
    initialize_stock_data,
    loyalty_customer_id,
    product_data,
    unique_external_id,
    valid_email,
    valid_phone,
    variant_data,
    warehouse_data,
)

DEFAULT_COUNTS = {
    "customers": 20,
    "products": 15,
    "categories": 5,
    "warehouses": 3,
    "loyalty_accounts": 10,
}


def seed_data(host: str, counts: dict | None = None) -> dict:
    """Seed baseline data. Returns dict of created entity IDs."""
    counts = counts or DEFAULT_COUNTS
    created: dict[str, list[str]] = {
        "customer_ids": [],
        "product_ids": [],
        "category_ids": [],
        "warehouse_ids": [],
        "inventory_item_ids": [],
        "loyalty_account_ids": [],
    }

    # Customers
    for _ in range(counts["customers"]):
        first, last = customer_name()
        resp = requests.post(
            f"{host}/customers",
            json={
                "external_id": unique_external_id(),
                "email": valid_email(),
                "first_name": first,
                "last_name": last,
                "phone": valid_phone(),
            },
            timeout=10,
        )
        if resp.status_code == 201:
            created["customer_ids"].append(resp.json()["customer_id"])

    # Products with variants (activated)
    for _ in range(counts["products"]):
        resp = requests.post(f"{host}/products", json=product_data(), timeout=10)
        if resp.status_code == 201:
            pid = resp.json()["product_id"]
            var_resp = requests.post(f"{host}/products/{pid}/variants", json=variant_data(), timeout=10)
            if var_resp.status_code != 201:
                print(f"[SEED] WARNING: variant creation failed for product {pid}: {var_resp.status_code}")
                continue
            act_resp = requests.put(f"{host}/products/{pid}/activate", timeout=10)
            if act_resp.status_code != 200:
                print(f"[SEED] WARNING: activation failed for product {pid}: {act_resp.status_code}")
                continue
            created["product_ids"].append(pid)

    # Categories
    for _ in range(counts["categories"]):
        resp = requests.post(f"{host}/categories", json={"name": category_name()}, timeout=10)
        if resp.status_code == 201:
            created["category_ids"].append(resp.json()["category_id"])

    # Warehouses
    for _ in range(counts["warehouses"]):
        resp = requests.post(f"{host}/warehouses", json=warehouse_data(), timeout=10)
        if resp.status_code == 201:
            created["warehouse_ids"].append(resp.json()["warehouse_id"])

    # Initialize stock for each product in first warehouse
    if created["warehouse_ids"] and created["product_ids"]:
        wh_id = created["warehouse_ids"][0]
        for pid in created["product_ids"]:
            payload = initialize_stock_data(
                product_id=pid,
                warehouse_id=wh_id,
                initial_quantity=100,
            )
            resp = requests.post(f"{host}/inventory", json=payload, timeout=10)
            if resp.status_code == 201:
                created["inventory_item_ids"].append(resp.json()["inventory_item_id"])

    # Loyalty reward accounts (enrolled + seeded with points to redeem/transfer)
    for _ in range(counts.get("loyalty_accounts", 0)):
        resp = requests.post(
            f"{host}/loyalty/accounts",
            json={"customer_id": loyalty_customer_id()},
            timeout=10,
        )
        if resp.status_code == 201:
            account_id = resp.json()["account_id"]
            created["loyalty_account_ids"].append(account_id)
            requests.post(
                f"{host}/loyalty/accounts/{account_id}/earn",
                json={"amount": 500, "reason": "seed"},
                timeout=10,
            )

    return created


def main():
    parser = argparse.ArgumentParser(description="Seed ShopStream with baseline load test data")
    parser.add_argument("--host", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--customers", type=int, default=DEFAULT_COUNTS["customers"])
    parser.add_argument("--products", type=int, default=DEFAULT_COUNTS["products"])
    parser.add_argument("--categories", type=int, default=DEFAULT_COUNTS["categories"])
    parser.add_argument("--warehouses", type=int, default=DEFAULT_COUNTS["warehouses"])
    args = parser.parse_args()

    counts = {
        "customers": args.customers,
        "products": args.products,
        "categories": args.categories,
        "warehouses": args.warehouses,
    }

    print(f"[SEED] Seeding {args.host} with {counts}")
    created = seed_data(args.host, counts)
    print(f"[SEED] Created: {', '.join(f'{len(v)} {k}' for k, v in created.items())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
