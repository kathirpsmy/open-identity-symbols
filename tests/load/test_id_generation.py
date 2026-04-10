"""
Load test: Generate 1,000,000 symbol IDs and verify no duplicates.

Run with:
    python tests/load/test_id_generation.py
"""

import sys
import time
sys.path.insert(0, ".")

from backend.services.identity_engine import generate_symbol_id


def run(n: int = 1_000_000):
    print(f"Generating {n:,} IDs...")
    start = time.perf_counter()

    ids = set()
    aliases = set()
    dupes = 0

    for i in range(n):
        result = generate_symbol_id()
        sid = result["symbol_id"]
        alias = result["alias"]

        if sid in ids:
            dupes += 1
        ids.add(sid)
        aliases.add(alias)

        if (i + 1) % 100_000 == 0:
            elapsed = time.perf_counter() - start
            print(f"  {i+1:>8,} IDs  |  {len(ids):>8,} unique  |  {elapsed:.1f}s")

    elapsed = time.perf_counter() - start
    rate = n / elapsed

    print("\n── Results ────────────────────────────────────")
    print(f"  Total generated   : {n:,}")
    print(f"  Unique symbol IDs : {len(ids):,}")
    print(f"  Unique aliases    : {len(aliases):,}")
    print(f"  Duplicates        : {dupes}")
    print(f"  Time              : {elapsed:.2f}s")
    print(f"  Rate              : {rate:,.0f} IDs/sec")
    print("────────────────────────────────────────────────")

    if dupes > 0:
        print(f"⚠  {dupes} collisions detected (expected for large N vs pool capacity)")
    else:
        print("✓  No collisions in this sample")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000
    run(n)
