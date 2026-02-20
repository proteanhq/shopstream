"""Demo: Run a customer migration with Priority Lanes.

Simulates a data migration that creates thousands of customers using
Protean's processing_priority() context manager. When priority lanes
are enabled in domain.toml, these events are routed to the backfill
Redis Stream and processed only when the primary stream (production
traffic) is idle.

Prerequisites:
    1. Infrastructure running: make docker-up && make setup-db
    2. Identity Engine running: make engine-identity
    3. Priority lanes enabled in src/identity/domain.toml:
        [server.priority_lanes]
        enabled = true

Usage:
    # Migration with LOW priority (events go to backfill lane)
    python scripts/migration_demo.py --count 5000 --priority low

    # Migration with NORMAL priority (baseline comparison)
    python scripts/migration_demo.py --count 5000 --priority normal

    # Bulk priority (lowest — processed last)
    python scripts/migration_demo.py --count 5000 --priority bulk --batch-size 200

While this runs, send production traffic to see priority lanes in action:
    curl -X POST http://localhost:8000/orders -H 'Content-Type: application/json' \\
         -d '{"customer_id":"prod-cust","items":[...]}'

Monitor in Observatory (http://localhost:9000):
    - customer stream: production events processed immediately
    - customer:backfill stream: migration events queue up, drain when idle
"""

import argparse
import sys
import time
import uuid

# Add src/ to path so we can import domain modules
sys.path.insert(0, "src")


def main():
    parser = argparse.ArgumentParser(
        description="Run a customer migration with Priority Lanes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --count 1000 --priority low       # Low-priority migration
  %(prog)s --count 5000 --priority bulk       # Bulk-priority migration
  %(prog)s --count 1000 --priority normal     # Normal priority (baseline)
        """,
    )
    parser.add_argument("--count", type=int, default=1000, help="Number of customers to migrate (default: 1000)")
    parser.add_argument(
        "--priority", choices=["bulk", "low", "normal"], default="low", help="Processing priority (default: low)"
    )
    parser.add_argument("--batch-size", type=int, default=100, help="Print progress every N records (default: 100)")
    args = parser.parse_args()

    from protean.utils.processing import Priority, processing_priority

    priority_map = {
        "bulk": Priority.BULK,
        "low": Priority.LOW,
        "normal": Priority.NORMAL,
    }
    priority = priority_map[args.priority]

    from identity.customer.register_customer import RegisterCustomer
    from identity.domain import identity

    print(f"\n{'='*60}")
    print("  ShopStream Migration Demo — Priority Lanes")
    print(f"{'='*60}")
    print(f"  Customers to migrate: {args.count:,}")
    print(f"  Processing priority:  {args.priority.upper()} ({int(priority)})")
    print(f"  Batch report every:   {args.batch_size:,} records")
    print(f"{'='*60}\n")

    success = 0
    errors = 0
    start = time.monotonic()

    with identity.domain_context(), processing_priority(priority):
        for i in range(args.count):
            try:
                identity.process(
                    RegisterCustomer(
                        external_id=f"migration-{uuid.uuid4().hex[:8]}",
                        email=f"migrated-{uuid.uuid4().hex[:6]}@migration.example.com",
                        first_name="Migrated",
                        last_name=f"User-{i+1}",
                    )
                )
                success += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  [ERROR] Record {i+1}: {e}")
                elif errors == 6:
                    print("  [ERROR] Suppressing further error messages...")

            if (i + 1) % args.batch_size == 0:
                elapsed = time.monotonic() - start
                rate = (i + 1) / elapsed
                print(
                    f"  [{time.strftime('%H:%M:%S')}] Migrated {i+1:,}/{args.count:,} "
                    f"({rate:.1f} rec/sec, {errors} errors)"
                )

    elapsed = time.monotonic() - start
    rate = success / elapsed if elapsed > 0 else 0

    print(f"\n{'='*60}")
    print("  Migration Complete")
    print(f"{'='*60}")
    print(f"  Total time:   {elapsed:.1f}s")
    print(f"  Succeeded:    {success:,}")
    print(f"  Errors:       {errors:,}")
    print(f"  Rate:         {rate:.1f} records/sec")
    print(f"  Priority:     {args.priority.upper()} ({int(priority)})")
    print(f"{'='*60}")
    print("\n  Check Observatory at http://localhost:9000 to see events")
    print(f"  in the {'backfill lane' if priority < 0 else 'primary lane'}.\n")


if __name__ == "__main__":
    main()
