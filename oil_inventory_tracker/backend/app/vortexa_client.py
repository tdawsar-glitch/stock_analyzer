"""Thin wrapper around the Vortexa SDK's OnshoreInventories endpoint.

Why a wrapper:
  - Centralizes parameter mapping (product key + geography key -> Vortexa IDs)
  - Sums child IDs into single series (regions are often built from country IDs)
  - Returns a normalized {date, value_bbl} DataFrame regardless of SDK quirks
  - Allows the rest of the app to be unit-testable by substituting a fake
    `_search` callable.

Parameter names on `OnshoreInventories().search` may differ slightly between
SDK versions. Confirm with `help(OnshoreInventories().search)` and adjust
the kwargs below if the install reports unknown arguments.
"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd

from .config import Geography, Product, Settings

log = logging.getLogger(__name__)


@dataclass
class FetchResult:
    df: pd.DataFrame      # columns: date, value_bbl
    partial: bool         # True if any child series was missing/empty


SearchCallable = Callable[..., "pd.DataFrame"]


class VortexaClient:
    def __init__(self, settings: Settings, search_fn: Optional[SearchCallable] = None):
        self.settings = settings
        self._search_fn = search_fn  # injectable for tests
        self._verified = False

    # --------- public API ---------

    def fetch_series(
        self,
        product: Product,
        geography: Geography,
        start: dt.datetime,
        end: dt.datetime,
        frequency: str = "day",
    ) -> FetchResult:
        """Fetch (and sum, where needed) an onshore inventory series in barrels."""
        product_ids = product.resolved_ids
        if not product_ids:
            raise ValueError(
                f"Product '{product.key}' has no Vortexa ID configured. "
                "Run scripts/resolve_ids.py to populate config/products.yaml."
            )
        geog_ids = geography.resolved_ids  # may be empty for 'global'

        # If the geography has explicit children, we issue one call per child
        # and sum — this is the cleanest way to build regional aggregates.
        if geography.children:
            frames: list[pd.DataFrame] = []
            any_partial = False
            for gid in geography.resolved_ids:
                df, partial = self._one_call(
                    product_ids=product_ids,
                    geography_ids=[gid],
                    start=start, end=end, frequency=frequency,
                )
                if df.empty:
                    any_partial = True
                    continue
                frames.append(df)
            if not frames:
                return FetchResult(pd.DataFrame(columns=["date", "value_bbl"]), partial=True)
            merged = (
                pd.concat(frames, ignore_index=True)
                .groupby("date", as_index=False)["value_bbl"]
                .sum()
                .sort_values("date")
            )
            return FetchResult(merged, partial=any_partial)

        # Single call (no children to sum)
        df, partial = self._one_call(
            product_ids=product_ids,
            geography_ids=geog_ids,        # [] for global
            start=start, end=end, frequency=frequency,
        )
        return FetchResult(df, partial=partial)

    # --------- internals ---------

    def _one_call(
        self,
        product_ids: list[str],
        geography_ids: list[str],
        start: dt.datetime,
        end: dt.datetime,
        frequency: str,
    ) -> tuple[pd.DataFrame, bool]:
        search = self._get_search()

        kwargs = dict(
            filter_products=product_ids,
            filter_time_min=start,
            filter_time_max=end,
            timeseries_frequency=frequency,
            timeseries_unit="bbl",
        )
        if geography_ids:
            kwargs["filter_storage_locations"] = geography_ids

        try:
            raw = search(**kwargs)
        except TypeError as e:
            # Param name drift across SDK versions — log and surface.
            log.error("Vortexa SDK rejected kwargs %s: %s", list(kwargs), e)
            raise

        df = self._normalize(raw)
        partial = df.empty or df["value_bbl"].isna().any()
        return df, partial

    @staticmethod
    def _normalize(raw) -> pd.DataFrame:
        """Coerce the SDK's response to a {date, value_bbl} DataFrame."""
        if raw is None:
            return pd.DataFrame(columns=["date", "value_bbl"])
        df = raw.to_df() if hasattr(raw, "to_df") else raw
        if df is None or len(df) == 0:
            return pd.DataFrame(columns=["date", "value_bbl"])

        # Try common Vortexa timeseries column names defensively.
        date_col = next(
            (c for c in ("key", "date", "timestamp", "time") if c in df.columns),
            None,
        )
        value_col = next(
            (c for c in ("value", "count", "quantity") if c in df.columns),
            None,
        )
        if date_col is None or value_col is None:
            raise ValueError(
                f"Unexpected Vortexa timeseries columns: {list(df.columns)}"
            )

        out = pd.DataFrame({
            "date": pd.to_datetime(df[date_col]).dt.tz_localize(None).dt.date,
            "value_bbl": pd.to_numeric(df[value_col], errors="coerce"),
        })
        return out.dropna(subset=["value_bbl"]).sort_values("date").reset_index(drop=True)

    def _get_search(self) -> SearchCallable:
        if self._search_fn is not None:
            return self._search_fn
        if not self.settings.vortexa_api_key:
            raise RuntimeError(
                "VORTEXA_API_KEY is not set. Populate .env (see .env.example)."
            )
        # Lazy import so the package can be imported in offline tests.
        from vortexasdk import OnshoreInventories  # type: ignore

        endpoint = OnshoreInventories()
        return endpoint.search

    def verify(self) -> bool:
        """Optional one-shot sanity check at startup."""
        if self._verified:
            return True
        try:
            self._get_search()
            self._verified = True
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("Vortexa client not ready: %s", e)
            return False
