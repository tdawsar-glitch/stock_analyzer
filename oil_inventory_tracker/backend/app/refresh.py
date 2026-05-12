"""Backfill and incremental refresh orchestration."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from .cache import Cache
from .config import Geography, Product, Settings
from .vortexa_client import VortexaClient

log = logging.getLogger(__name__)


def backfill_pair(
    settings: Settings,
    cache: Cache,
    client: VortexaClient,
    product: Product,
    geography: Geography,
    years: int = 5,
) -> int:
    """Pull `years` of history for a single (product, geography) pair."""
    end = dt.datetime.utcnow()
    start = end - dt.timedelta(days=365 * years + 30)
    started = dt.datetime.utcnow()
    try:
        result = client.fetch_series(product, geography, start, end, frequency="day")
        rows = cache.upsert(product.key, geography.key, result.df, partial=result.partial)
        cache.log_refresh(product.key, geography.key, started,
                          dt.datetime.utcnow(), rows, "ok")
        log.info("backfill %s/%s: %d rows (partial=%s)",
                 product.key, geography.key, rows, result.partial)
        return rows
    except Exception as e:  # noqa: BLE001
        cache.log_refresh(product.key, geography.key, started,
                          dt.datetime.utcnow(), 0, "error", str(e))
        log.exception("backfill %s/%s failed", product.key, geography.key)
        return 0


def incremental_refresh(
    settings: Settings,
    cache: Cache,
    client: VortexaClient,
    product: Product,
    geography: Geography,
    lookback_days: int = 7,
) -> int:
    """Pull the last `lookback_days` of data and upsert."""
    end = dt.datetime.utcnow()
    last = cache.last_observation(product.key, geography.key)
    if last is None:
        return backfill_pair(settings, cache, client, product, geography)
    start = dt.datetime.combine(last, dt.time.min) - dt.timedelta(days=lookback_days)
    started = dt.datetime.utcnow()
    try:
        result = client.fetch_series(product, geography, start, end, frequency="day")
        rows = cache.upsert(product.key, geography.key, result.df, partial=result.partial)
        cache.log_refresh(product.key, geography.key, started,
                          dt.datetime.utcnow(), rows, "ok")
        return rows
    except Exception as e:  # noqa: BLE001
        cache.log_refresh(product.key, geography.key, started,
                          dt.datetime.utcnow(), 0, "error", str(e))
        log.exception("incremental %s/%s failed", product.key, geography.key)
        return 0


def refresh_all(
    settings: Settings,
    cache: Cache,
    client: VortexaClient,
    *,
    mode: str = "incremental",
    only_product: Optional[str] = None,
    only_geography: Optional[str] = None,
) -> dict:
    summary = {"pairs": 0, "rows": 0, "errors": 0}
    fn = backfill_pair if mode == "backfill" else incremental_refresh

    products = (
        [settings.products[only_product]] if only_product else list(settings.products.values())
    )
    geographies = (
        [settings.geographies[only_geography]] if only_geography
        else list(settings.geographies.values())
    )

    for product in products:
        if not settings.demo_mode and not product.resolved_ids:
            log.warning("skipping product %s: no Vortexa ID", product.key)
            continue
        for geo in geographies:
            # Global skips filter_storage_locations entirely (handled in client),
            # so an empty resolved_ids list is OK for the 'global' key only.
            if (not settings.demo_mode
                    and geo.key != "global" and not geo.resolved_ids):
                log.warning("skipping geography %s: no Vortexa ID(s)", geo.key)
                continue
            rows = fn(settings, cache, client, product, geo)
            summary["pairs"] += 1
            summary["rows"] += rows
            if rows == 0:
                summary["errors"] += 1
    return summary
