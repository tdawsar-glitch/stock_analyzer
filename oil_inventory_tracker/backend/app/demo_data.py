"""Synthetic onshore inventory data for local development.

Enabled when OIT_DEMO_MODE=1. Generates a deterministic 5+ year daily series
per (product, geography) pair with realistic seasonality, trend, and noise.
The shape and order of magnitude are loosely tuned to public EIA/JODI ranges
so the chart looks plausible — but this is NOT real data. Never ship demo
mode to production.
"""
from __future__ import annotations

import datetime as dt
import hashlib

import numpy as np
import pandas as pd


# Rough plausible levels per (product, geography_kind) in barrels.
# Crude / refined diverge by ~2 orders of magnitude.
_BASE_LEVELS_BBL = {
    "crude": {
        "global": 4_400_000_000, "region": 1_000_000_000,
        "country": 450_000_000, "hub": 60_000_000,
    },
    "gasoline":  {"global": 800_000_000, "region": 230_000_000,
                  "country": 230_000_000, "hub": 35_000_000},
    "gasoil":    {"global": 900_000_000, "region": 260_000_000,
                  "country": 140_000_000, "hub": 40_000_000},
    "jet":       {"global": 350_000_000, "region": 90_000_000,
                  "country": 40_000_000, "hub": 15_000_000},
    "fuel_oil":  {"global": 320_000_000, "region": 80_000_000,
                  "country": 35_000_000, "hub": 28_000_000},
    "naphtha":   {"global": 200_000_000, "region": 55_000_000,
                  "country": 28_000_000, "hub": 10_000_000},
    "lpg":       {"global": 280_000_000, "region": 75_000_000,
                  "country": 32_000_000, "hub": 11_000_000},
}


def _seed(product_key: str, geography_key: str) -> int:
    h = hashlib.sha256(f"{product_key}|{geography_key}".encode()).digest()
    return int.from_bytes(h[:4], "big")


def synthesize(
    product_key: str,
    geography_kind: str,
    geography_key: str,
    start: dt.datetime,
    end: dt.datetime,
) -> pd.DataFrame:
    """Return a daily DataFrame with columns date, value_bbl."""
    base = _BASE_LEVELS_BBL.get(product_key, {}).get(geography_kind, 50_000_000)

    # Hub-sized for hub keys regardless of product table coverage.
    rng = np.random.default_rng(_seed(product_key, geography_key))

    dates = pd.date_range(start.date(), end.date(), freq="D")
    n = len(dates)
    if n == 0:
        return pd.DataFrame(columns=["date", "value_bbl"])

    # Seasonal: refined products draw down in summer (driving) and winter
    # (heating) depending on product. Use a simple annual sinusoid with a
    # product-specific phase.
    phase = {
        "crude": 0.0,
        "gasoline": -np.pi / 2,    # low in summer
        "gasoil": -np.pi / 2,
        "jet": -np.pi / 3,
        "fuel_oil": np.pi / 2,
        "naphtha": 0.0,
        "lpg": np.pi / 2,          # low in winter
    }.get(product_key, 0.0)
    t = np.arange(n)
    year_frac = (t / 365.25) * 2 * np.pi
    seasonal = 0.06 * np.sin(year_frac + phase)

    # Gentle multi-year trend (random direction per pair)
    trend_slope = rng.uniform(-0.015, 0.025) / 365.25  # per day
    trend = trend_slope * t

    # AR(1) noise so the series looks autocorrelated rather than i.i.d.
    noise = np.zeros(n)
    rho = 0.92
    sigma = 0.008
    z = rng.normal(0, sigma, size=n)
    for i in range(1, n):
        noise[i] = rho * noise[i - 1] + z[i]

    # One or two shocks (e.g. 2020 COVID drawdown)
    shock = np.zeros(n)
    for d in dates:
        if d.year == 2020 and 4 <= d.month <= 8 and product_key in ("jet", "gasoline"):
            shock[(dates == d).argmax()] -= 0.18
    # Smooth the shocks
    if shock.any():
        shock = pd.Series(shock).rolling(30, min_periods=1, center=True).mean().to_numpy()

    factor = 1.0 + seasonal + trend + noise + shock
    values = base * np.clip(factor, 0.5, 2.0)

    return pd.DataFrame({"date": dates.date, "value_bbl": values})
