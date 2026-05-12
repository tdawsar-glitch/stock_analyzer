"""5-year range / average computation, indexed by ISO week.

Why ISO week and not calendar day-of-year:
  Day-of-year shifts by one every leap year, so a day-of-year-indexed 5y
  average misaligns by a day every fourth year. ISO week 1-53 keeps
  comparisons stable.

Output convention matches EIA / IEA style charts:
  - current:        most recent ~4 years of observed values
  - five_year_avg:  per-ISO-week mean across the prior 5 calendar years
  - five_year_max:  per-ISO-week max across the prior 5 calendar years
  - five_year_min:  per-ISO-week min across the prior 5 calendar years

The avg/max/min are emitted as a year-aligned overlay: each output point
carries a real date in the current year so the frontend can plot it on
the same x-axis as `current`.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Series:
    points: list[dict] = field(default_factory=list)  # [{date, value}]


@dataclass
class AggregateResult:
    current: Series
    five_year_avg: Series
    five_year_max: Series
    five_year_min: Series
    prior_years: dict[int, Series]                    # {year: Series}
    partial: bool

    def to_payload(self) -> dict:
        return {
            "current": self.current.points,
            "five_year_avg": self.five_year_avg.points,
            "five_year_max": self.five_year_max.points,
            "five_year_min": self.five_year_min.points,
            "prior_years": {str(k): v.points for k, v in self.prior_years.items()},
            "partial": self.partial,
        }


def _resample(df: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """Resample daily data to weekly (W-MON) or monthly (M)."""
    if df.empty:
        return df
    out = df.set_index(pd.to_datetime(df["date"]))[["value_bbl"]]
    rule = {"daily": "D", "weekly": "W-MON", "monthly": "MS"}.get(frequency, "W-MON")
    out = out.resample(rule).mean().dropna()
    return out.reset_index().rename(columns={"index": "date"})


def _iso_week_key(d: pd.Timestamp) -> tuple[int, int]:
    iso = d.isocalendar()
    # iso.week ranges 1..53; iso.year handles year-boundary weeks correctly.
    return int(iso.week), int(iso.weekday)


def compute(
    df: pd.DataFrame,
    today: dt.date | None = None,
    frequency: str = "weekly",
    current_window_years: int = 4,
    partial: bool = False,
) -> AggregateResult:
    """Compute the chart payload from a raw daily series in barrels."""
    today = today or dt.date.today()
    if df is None or df.empty:
        empty = Series([])
        return AggregateResult(empty, empty, empty, empty, {}, partial=True)

    df = df[["date", "value_bbl"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    resampled = _resample(df, frequency)
    resampled["iso_week"] = resampled["date"].dt.isocalendar().week.astype(int)
    resampled["year"] = resampled["date"].dt.year

    current_year = today.year
    current_cutoff = pd.Timestamp(today) - pd.DateOffset(years=current_window_years)
    current_df = resampled[resampled["date"] >= current_cutoff].copy()

    # 5y stats use the 5 full calendar years prior to the current year.
    five_years = list(range(current_year - 5, current_year))
    history = resampled[resampled["year"].isin(five_years)]

    stats: pd.DataFrame
    if history.empty:
        stats = pd.DataFrame(columns=["iso_week", "avg", "max", "min"])
    else:
        stats = (
            history.groupby("iso_week")["value_bbl"]
            .agg(avg="mean", max="max", min="min")
            .reset_index()
        )

    # Map each ISO week to a representative date in the current year so the
    # overlay can be plotted on the same x-axis as the current line.
    def week_to_current_year_date(week: int) -> dt.date:
        # ISO weeks: %G-W%V-1 (Monday). Use the current ISO year.
        try:
            return dt.date.fromisocalendar(current_year, int(week), 1)
        except ValueError:
            # Week 53 may not exist in every year — clamp to last valid week.
            return dt.date.fromisocalendar(current_year, 52, 1)

    def series_from_stats(col: str) -> Series:
        if stats.empty:
            return Series([])
        pts = [
            {"date": week_to_current_year_date(int(w)).isoformat(),
             "value": float(v) if pd.notna(v) else None}
            for w, v in zip(stats["iso_week"], stats[col])
        ]
        # Sort by date so the chart draws left-to-right.
        pts.sort(key=lambda p: p["date"])
        return Series(pts)

    def series_from_df(d: pd.DataFrame) -> Series:
        if d.empty:
            return Series([])
        return Series([
            {"date": pd.Timestamp(r.date).date().isoformat(),
             "value": float(r.value_bbl) if pd.notna(r.value_bbl) else None}
            for r in d.itertuples()
        ])

    current_series = series_from_df(current_df[["date", "value_bbl"]])

    prior: dict[int, Series] = {}
    for y in five_years:
        yr_df = resampled[resampled["year"] == y][["date", "value_bbl"]]
        if not yr_df.empty:
            prior[y] = series_from_df(yr_df)

    return AggregateResult(
        current=current_series,
        five_year_avg=series_from_stats("avg"),
        five_year_max=series_from_stats("max"),
        five_year_min=series_from_stats("min"),
        prior_years=prior,
        partial=partial,
    )


def yoy_and_vs_avg_delta(result: AggregateResult) -> dict:
    """Compute the small summary widget values (latest vs 1y ago, vs 5y avg)."""
    if not result.current.points:
        return {}
    latest = result.current.points[-1]
    latest_val = latest["value"]
    latest_date = latest["date"]

    # YoY: find value ~52 weeks before latest in `current`
    target = pd.Timestamp(latest_date) - pd.DateOffset(years=1)
    yoy_pt = min(
        result.current.points,
        key=lambda p: abs(pd.Timestamp(p["date"]) - target),
        default=None,
    )
    yoy_val = yoy_pt["value"] if yoy_pt else None

    # vs 5y avg: match by ISO week
    iso_w = pd.Timestamp(latest_date).isocalendar().week
    avg_pt = next(
        (p for p in result.five_year_avg.points
         if pd.Timestamp(p["date"]).isocalendar().week == iso_w),
        None,
    )
    avg_val = avg_pt["value"] if avg_pt else None

    def delta(a, b):
        if a is None or b is None or b == 0:
            return None
        return {"abs": a - b, "pct": (a - b) / b}

    # Percentile within 5y range at the latest ISO week
    max_pt = next((p for p in result.five_year_max.points
                   if pd.Timestamp(p["date"]).isocalendar().week == iso_w), None)
    min_pt = next((p for p in result.five_year_min.points
                   if pd.Timestamp(p["date"]).isocalendar().week == iso_w), None)
    pct_in_range = None
    if max_pt and min_pt and latest_val is not None:
        rng = (max_pt["value"] or 0) - (min_pt["value"] or 0)
        if rng:
            pct_in_range = float(
                np.clip((latest_val - min_pt["value"]) / rng, 0.0, 1.0)
            )

    return {
        "latest_date": latest_date,
        "latest_value": latest_val,
        "yoy_delta": delta(latest_val, yoy_val),
        "vs_avg_delta": delta(latest_val, avg_val),
        "percentile_in_5y_range": pct_in_range,
    }
