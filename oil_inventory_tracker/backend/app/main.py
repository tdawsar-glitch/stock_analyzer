"""FastAPI app: serves the dashboard's data layer.

Endpoints:
  GET  /api/health
  GET  /api/meta                       -- products, geographies, last refresh
  GET  /api/inventory                  -- chart payload for one product+geog
  GET  /api/inventory/csv              -- same series as CSV
  GET  /api/reconcile/us_crude         -- Vortexa vs EIA delta widget
  POST /api/refresh                    -- admin: trigger refresh
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import logging
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import aggregation
from .cache import Cache
from .config import Settings, get_settings
from .eia_reconcile import compare as eia_compare
from .eia_reconcile import latest_eia_us_crude
from .refresh import refresh_all
from .vortexa_client import VortexaClient

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


# --------- app state ---------

class AppState:
    settings: Settings
    cache: Cache
    client: VortexaClient
    scheduler: BackgroundScheduler


state = AppState()


def _scheduled_refresh() -> None:
    log.info("scheduled refresh starting")
    try:
        summary = refresh_all(state.settings, state.cache, state.client,
                              mode="incremental")
        log.info("scheduled refresh done: %s", summary)
    except Exception:
        log.exception("scheduled refresh failed")


def _cron_trigger(expr: str) -> CronTrigger:
    # APScheduler's from_crontab handles 5-field cron expressions.
    return CronTrigger.from_crontab(expr, timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.settings = get_settings()
    state.cache = Cache(state.settings.cache_db_path)
    state.client = VortexaClient(state.settings)
    state.client.verify()  # warn-only; does not block startup

    state.scheduler = BackgroundScheduler(timezone="UTC")
    try:
        state.scheduler.add_job(
            _scheduled_refresh,
            trigger=_cron_trigger(state.settings.refresh_cron),
            id="daily_refresh",
            replace_existing=True,
        )
        state.scheduler.start()
        log.info("scheduler started: cron='%s'", state.settings.refresh_cron)
    except Exception:
        log.exception("scheduler failed to start (continuing)")

    yield

    try:
        state.scheduler.shutdown(wait=False)
    except Exception:
        pass


app = FastAPI(title="Oil Inventory Tracker", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # internal tool; tighten in production deploy
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------- dependencies ---------

def settings_dep() -> Settings:
    return state.settings


def require_admin(request: Request) -> None:
    expected = state.settings.admin_token
    if not expected:
        raise HTTPException(503, "ADMIN_TOKEN is not configured")
    got = request.headers.get("x-admin-token")
    if got != expected:
        raise HTTPException(401, "invalid admin token")


# --------- routes ---------

@app.get("/api/health")
def health():
    return {"ok": True, "time": dt.datetime.utcnow().isoformat() + "Z"}


@app.get("/api/meta")
def meta(s: Settings = Depends(settings_dep)):
    last = state.cache.last_refresh()
    return {
        "last_refresh": last.isoformat() + "Z" if last else None,
        "demo_mode": s.demo_mode,
        "products": [
            {"key": p.key, "label": p.label, "display_unit": p.display_unit,
             "configured": s.demo_mode or bool(p.resolved_ids)}
            for p in s.products.values()
        ],
        "geographies": [
            {"key": g.key, "label": g.label, "kind": g.kind,
             "configured": s.demo_mode or g.key == "global" or bool(g.resolved_ids),
             "eia_reconcile": g.eia_reconcile}
            for g in s.geographies.values()
        ],
    }


def _resolve(product: str, geography: str, s: Settings):
    if product not in s.products:
        raise HTTPException(400, f"unknown product: {product}")
    if geography not in s.geographies:
        raise HTTPException(400, f"unknown geography: {geography}")
    return s.products[product], s.geographies[geography]


@app.get("/api/inventory")
def inventory(
    product: str = Query(...),
    geography: str = Query("global"),
    frequency: str = Query("weekly", pattern="^(daily|weekly|monthly)$"),
    s: Settings = Depends(settings_dep),
):
    p, g = _resolve(product, geography, s)
    df = state.cache.fetch(p.key, g.key)
    partial = bool(df["partial"].any()) if not df.empty and "partial" in df.columns else False

    result = aggregation.compute(df, frequency=frequency, partial=partial)
    summary = aggregation.yoy_and_vs_avg_delta(result)

    return {
        "metadata": {
            "product_key": p.key,
            "product_label": p.label,
            "geography_key": g.key,
            "geography_label": g.label,
            "display_unit": p.display_unit,
            "unit_base": "bbl",
            "source": "Vortexa OnshoreInventories",
            "frequency": frequency,
            "last_observation": (
                df["date"].max().isoformat() if not df.empty else None
            ),
            "rows_cached": int(len(df)),
        },
        **result.to_payload(),
        "summary": summary,
    }


@app.get("/api/inventory/csv")
def inventory_csv(
    product: str = Query(...),
    geography: str = Query("global"),
    s: Settings = Depends(settings_dep),
):
    p, g = _resolve(product, geography, s)
    df = state.cache.fetch(p.key, g.key)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "value_bbl", "partial", "product", "geography"])
    for r in df.itertuples():
        w.writerow([r.date.isoformat(), r.value_bbl, r.partial, p.key, g.key])
    buf.seek(0)
    filename = f"{p.key}_{g.key}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/reconcile/us_crude")
async def reconcile_us_crude(s: Settings = Depends(settings_dep)):
    df = state.cache.fetch("crude", "us")
    vortexa_latest = float(df["value_bbl"].iloc[-1]) if not df.empty else None
    eia = await latest_eia_us_crude(s.eia_api_key or "")
    return {
        "vortexa_latest": vortexa_latest,
        "vortexa_as_of": df["date"].iloc[-1].isoformat() if not df.empty else None,
        "eia": eia,
        "comparison": eia_compare(vortexa_latest, eia),
    }


@app.post("/api/refresh", dependencies=[Depends(require_admin)])
def refresh(
    mode: str = Query("incremental", pattern="^(incremental|backfill)$"),
    product: Optional[str] = Query(None),
    geography: Optional[str] = Query(None),
    s: Settings = Depends(settings_dep),
):
    summary = refresh_all(s, state.cache, state.client,
                          mode=mode, only_product=product, only_geography=geography)
    return {"ok": True, "summary": summary}
