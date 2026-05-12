"""Backfill 5 years of onshore inventory history into the DuckDB cache.

Usage:
    python -m scripts.backfill                 # everything
    python -m scripts.backfill --product crude
    python -m scripts.backfill --geography us
    python -m scripts.backfill --years 3

Heavy initial pull — expect this to take a while. Progress is logged
per (product, geography) pair.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.cache import Cache              # noqa: E402
from app.config import get_settings      # noqa: E402
from app.refresh import backfill_pair    # noqa: E402
from app.vortexa_client import VortexaClient  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", help="single product key (default: all)")
    parser.add_argument("--geography", help="single geography key (default: all)")
    parser.add_argument("--years", type=int, default=5)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("backfill")

    settings = get_settings()
    cache = Cache(settings.cache_db_path)
    client = VortexaClient(settings)
    if not client.verify():
        log.error("Vortexa client failed to initialize. Check VORTEXA_API_KEY.")
        return 2

    products = (
        [settings.products[args.product]] if args.product
        else list(settings.products.values())
    )
    geographies = (
        [settings.geographies[args.geography]] if args.geography
        else list(settings.geographies.values())
    )

    total_pairs = 0
    total_rows = 0
    start = time.time()
    for p in products:
        if not p.resolved_ids:
            log.warning("skip product %s: no Vortexa ID configured", p.key)
            continue
        for g in geographies:
            if g.key != "global" and not g.resolved_ids:
                log.warning("skip geography %s: no Vortexa ID configured", g.key)
                continue
            t0 = time.time()
            rows = backfill_pair(settings, cache, client, p, g, years=args.years)
            elapsed = time.time() - t0
            log.info("  %s / %s -> %d rows (%.1fs)", p.key, g.key, rows, elapsed)
            total_pairs += 1
            total_rows += rows

    log.info("backfill complete: %d pairs, %d rows, %.1fs total",
             total_pairs, total_rows, time.time() - start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
