"""US crude reconciliation against EIA weekly stocks.

Data quality check: Vortexa's US onshore crude should be within a few percent
of EIA's weekly commercial crude stocks (PET.WCESTUS1.W). This widget
surfaces the delta so analysts can spot drift.

Requires EIA_API_KEY (free, register at https://www.eia.gov/opendata/).
"""
from __future__ import annotations

import datetime as dt
import logging

import httpx

log = logging.getLogger(__name__)

EIA_SERIES_ID = "PET.WCESTUS1.W"   # weekly US commercial crude stocks, kb
EIA_ENDPOINT = "https://api.eia.gov/v2/seriesid/{series_id}"


async def latest_eia_us_crude(api_key: str) -> dict | None:
    """Return the latest weekly EIA US commercial crude stock in barrels."""
    if not api_key:
        return None
    url = EIA_ENDPOINT.format(series_id=EIA_SERIES_ID)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, params={"api_key": api_key, "length": 1})
            r.raise_for_status()
            data = r.json()
    except Exception as e:  # noqa: BLE001
        log.warning("EIA fetch failed: %s", e)
        return None

    rows = (data.get("response") or {}).get("data") or []
    if not rows:
        return None
    row = rows[0]
    # EIA returns thousand barrels — normalize to bbl for direct comparison.
    period = row.get("period")
    val_kb = row.get("value")
    if val_kb is None:
        return None
    try:
        value_bbl = float(val_kb) * 1000.0
        as_of = dt.date.fromisoformat(period[:10])
    except (TypeError, ValueError):
        return None
    return {"as_of": as_of.isoformat(), "value_bbl": value_bbl, "source": "EIA WCESTUS1"}


def compare(vortexa_latest_bbl: float | None, eia: dict | None) -> dict | None:
    if vortexa_latest_bbl is None or eia is None:
        return None
    eia_val = eia["value_bbl"]
    delta = vortexa_latest_bbl - eia_val
    pct = (delta / eia_val) if eia_val else None
    return {
        "vortexa_bbl": vortexa_latest_bbl,
        "eia_bbl": eia_val,
        "eia_as_of": eia["as_of"],
        "delta_bbl": delta,
        "delta_pct": pct,
    }
