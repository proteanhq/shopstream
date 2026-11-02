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
        "customer_ids": _seed_customers(host, counts["customers"]),
        "product_ids": _seed_products(host, counts["products"]),
        "category_ids": _seed_categories(host, counts["categories"]),
        "warehouse_ids": _seed_warehouses(host, counts["warehouses"]),
    }
    # Stock for each product goes in the first warehouse.
    created["inventory_item_ids"] = _seed_stock(host, created["warehouse_ids"][:1], created["product_ids"])
    created["loyalty_account_ids"] = _seed_loyalty_accounts(host, counts.get("loyalty_accounts", 0))
    return created


def _seed_customers(host: str, count: int) -> list[str]:
    ids = []
    for _ in range(count):
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
            ids.append(resp.json()["customer_id"])
    return ids


def _seed_products(host: str, count: int) -> list[str]:
    """Products with a variant, activated. A product whose variant or activation fails is left out."""
    ids = []
    for _ in range(count):
        resp = requests.post(f"{host}/products", json=product_data(), timeout=10)
        if resp.status_code != 201:
            continue
        pid = resp.json()["product_id"]
        var_resp = requests.post(f"{host}/products/{pid}/variants", json=variant_data(), timeout=10)
        if var_resp.status_code != 201:
            print(f"[SEED] WARNING: variant creation failed for product {pid}: {var_resp.status_code}")
            continue
        act_resp = requests.put(f"{host}/products/{pid}/activate", timeout=10)
        if act_resp.status_code != 200:
            print(f"[SEED] WARNING: activation failed for product {pid}: {act_resp.status_code}")
            continue
        ids.append(pid)
    return ids


def _seed_categories(host: str, count: int) -> list[str]:
    ids = []
    for _ in range(count):
        resp = requests.post(f"{host}/categories", json={"name": category_name()}, timeout=10)
        if resp.status_code == 201:
            ids.append(resp.json()["category_id"])
    return ids


def _seed_warehouses(host: str, count: int) -> list[str]:
    ids = []
    for _ in range(count):
        resp = requests.post(f"{host}/warehouses", json=warehouse_data(), timeout=10)
        if resp.status_code == 201:
            ids.append(resp.json()["warehouse_id"])
    return ids


def _seed_stock(host: str, warehouse_ids: list[str], product_ids: list[str]) -> list[str]:
    ids = []
    for wh_id in warehouse_ids:
        for pid in product_ids:
            payload = initialize_stock_data(
                product_id=pid,
                warehouse_id=wh_id,
                initial_quantity=100,
            )
            resp = requests.post(f"{host}/inventory", json=payload, timeout=10)
            if resp.status_code == 201:
                ids.append(resp.json()["inventory_item_id"])
    return ids


def _seed_loyalty_accounts(host: str, count: int) -> list[str]:
    """Enrolled reward accounts, each earning 500 points so scenarios can redeem and transfer."""
    ids = []
    for _ in range(count):
        resp = requests.post(
            f"{host}/loyalty/accounts",
            json={"customer_id": loyalty_customer_id()},
            timeout=10,
        )
        if resp.status_code == 201:
            account_id = resp.json()["account_id"]
            ids.append(account_id)
            requests.post(
                f"{host}/loyalty/accounts/{account_id}/earn",
                json={"amount": 500, "reason": "seed"},
                timeout=10,
            )
    return ids


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
