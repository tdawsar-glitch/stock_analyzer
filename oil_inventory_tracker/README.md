# Oil Inventory Tracker

Crude and refined product onshore inventory dashboard, sourced from Vortexa, with EIA/IEA-style 5-year range and 5-year average overlays.

Internal analyst tool for the Saudi Ministry of Energy. Prioritizes data fidelity and analytical depth over consumer polish.

---

## What it shows

For every product × geography pair:

- **Solid line** — current observed inventory (trailing ~4 years)
- **Dashed line** — 5-year average, indexed by ISO week
- **Shaded band** — 5-year min/max envelope (range), indexed by ISO week
- **Tooltip** — exact value, YoY delta, vs-5y-avg delta, percentile within 5y range
- **Partial-data badge** — surfaced when Vortexa returns incomplete coverage

The x-axis uses **ISO week** rather than calendar day-of-year so leap years don't misalign the overlay by a day every four years.

### Products tracked
Crude · Gasoline · Gasoil/Diesel · Jet/Kerosene · Fuel Oil · Naphtha · LPG.

Each product is pulled independently — no lumped categories.

### Geographies tracked
Global · regions (North America, Europe, Middle East, Asia-Pacific, LatAm, Africa) · countries (US, China, Japan, South Korea, Singapore) · hubs (ARA, Fujairah).

---

## Architecture

```
+--------------+        +-------------------------+        +------------------+
|  Vortexa SDK | <----- |    FastAPI backend      | -----> |  DuckDB cache    |
|              |        |  - daily refresh job    |        |  inventory_cache |
|              |        |  - 5y aggregation       |        +------------------+
+--------------+        |  - /api/inventory       |
                        |  - /api/refresh (admin) |
                        +-----------+-------------+
                                    |
                                    v
                        +-------------------------+
                        |  React + TS + Recharts  |
                        |  /  grid view           |
                        |  /  deep-dive modal     |
                        |  /  EIA reconcile chip  |
                        +-------------------------+
```

---

## Setup

### 1. Backend

```bash
cd oil_inventory_tracker
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
# Fill in VORTEXA_API_KEY (and optionally EIA_API_KEY, ADMIN_TOKEN).
```

Verify the Vortexa SDK can authenticate:

```bash
python -m vortexasdk.check_setup
```

### 2. Resolve Vortexa IDs

Vortexa endpoints take numeric/UUID IDs, not human names. Run the resolver:

```bash
python -m scripts.resolve_ids
```

This prints candidate IDs for every product and geography in `config/*.yaml`. Copy the chosen IDs into the YAMLs by hand — the script does **not** auto-write, because product/geography matches are often ambiguous (e.g. "Fuel Oil" returns multiple sub-products in Vortexa). For regional aggregates, fill the `children:` list with the constituent country IDs.

### 3. Backfill 5 years of history

This is a heavy initial pull. Expect minutes to tens of minutes depending on how many pairs are configured.

```bash
python -m scripts.backfill              # everything
python -m scripts.backfill --product crude   # one product
python -m scripts.backfill --geography us    # one geography
```

Progress is logged per (product, geography) pair.

### 4. Run the backend

```bash
uvicorn app.main:app --reload --app-dir backend
```

The daily incremental refresh job (cron-style, configurable via `REFRESH_CRON` in `.env`) starts automatically with the server.

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Browse to http://localhost:5173. The Vite dev server proxies `/api/*` to `http://localhost:8000`.

### Docker

```bash
docker compose up --build
# backend  -> :8000
# frontend -> :5173 (nginx, proxies /api -> backend)
```

The first container start backfills nothing — you still need to mount your `.env` and run the backfill script (either against the host venv or by `docker compose exec backend python -m scripts.backfill`).

---

## API surface

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Liveness probe |
| GET | `/api/meta` | Available products and geographies, last refresh time |
| GET | `/api/inventory?product=…&geography=…&frequency=weekly\|monthly` | Chart payload (current, 5y avg, 5y max, 5y min, summary) |
| GET | `/api/inventory/csv?product=…&geography=…` | Raw daily series as CSV |
| GET | `/api/reconcile/us_crude` | Vortexa vs EIA delta for US crude (requires `EIA_API_KEY`) |
| POST | `/api/refresh?mode=incremental\|backfill` | Admin: trigger refresh (requires `x-admin-token` header) |

### Response shape (`/api/inventory`)

```jsonc
{
  "metadata": { "product_label": "Crude Oil", "geography_label": "Global",
                "display_unit": "mb", "last_observation": "2025-05-04", ... },
  "current":       [{ "date": "2021-05-...", "value": 1234567890.0 }, ...],
  "five_year_avg": [{ "date": "2025-W01-Mon", "value": ... }, ...],
  "five_year_max": [...],
  "five_year_min": [...],
  "prior_years":   { "2020": [...], "2021": [...] },
  "summary": {
    "latest_value": 1234567890.0,
    "yoy_delta":   { "abs": ..., "pct": ... },
    "vs_avg_delta": { "abs": ..., "pct": ... },
    "percentile_in_5y_range": 0.42
  },
  "partial": false
}
```

All values are barrels at the API layer; the frontend converts to kb/mb per the unit toggle.

---

## Configuration files

### `config/products.yaml`

Each product entry needs at minimum a `key`, `label`, and a Vortexa `id` (fill in via the resolver). For combined views (e.g. all gasoil sub-products), list sibling IDs in `children:`.

### `config/geographies.yaml`

Same shape, with `kind` (global/region/country/hub) controlling the sidebar grouping. For regions, leave `id` empty and list constituent country IDs in `children:` — the backend sums them at query time.

The `global` key is special: leave `id` and `children` empty and the Vortexa call sends no `filter_storage_locations`, returning the worldwide aggregate.

---

## Caching & performance

- **Cache**: DuckDB at `CACHE_DB_PATH` (defaults to `backend/data/inventory_cache.duckdb`), keyed by `(product_key, geography_key, date)`. Upserts are atomic.
- **First run**: `scripts/backfill.py` pulls 5 years of daily history per pair. Progress logged per pair.
- **Daily refresh**: `APScheduler` runs incremental refresh (last 7 days) on the `REFRESH_CRON` schedule. The job pulls only the recent window and upserts.
- **Manual refresh**: `POST /api/refresh` with `x-admin-token: $ADMIN_TOKEN`.
- **Frontend** never calls Vortexa directly — only the FastAPI cache layer.

---

## Data quality

### US crude reconciliation

The Vortexa US crude series should track EIA's weekly commercial crude stocks (`PET.WCESTUS1.W`) within a few percent. When `EIA_API_KEY` is set and US crude is in the cache, the dashboard surfaces a small reconciliation chip showing the latest delta.

Set `EIA_API_KEY` in `.env` (free, register at https://www.eia.gov/opendata/register.php).

### Partial-data badge

If Vortexa returns no data for one of the child IDs in a regional aggregate, the row is flagged `partial: true` and the chart shows a "data partial" badge. The series is still rendered (summed across whatever children did return data) — analysts can decide whether to trust it.

---

## Known Vortexa quirks

- **Parameter naming drift across SDK versions.** `filter_products` / `filter_storage_locations` / `filter_time_min` / `filter_time_max` are stable but minor variants exist. If the SDK rejects a kwarg, run `help(OnshoreInventories().search)` and update `backend/app/vortexa_client.py`.
- **`OnshoreInventories` returns onshore tank stocks only.** Floating storage (oil on water) is a separate endpoint (e.g. `CargoTimeSeries` / `FleetUtilisationTimeseries`). Out of scope for v1.
- **Unit returned is barrels.** The display unit is set per-product in `products.yaml` (crude → `mb`, refined → `kb`).
- **Day-of-year vs ISO week.** We index the 5y overlay by ISO week, *not* calendar day, otherwise leap years misalign the overlay by a day every four years.
- **Ambiguous product matches.** "Fuel Oil", "Gasoil", and "Jet" often resolve to multiple Vortexa products. Pick the right leaf product manually after running `resolve_ids.py`.

---

## Future extensions (not built)

- Floating-storage overlay (separate Vortexa endpoint)
- Refinery run rates on a secondary y-axis
- OPEC+ compliance overlay on Middle East crude charts
- Bilingual EN / AR UI toggle

---

## Files

| Path | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app + scheduler |
| `backend/app/vortexa_client.py` | SDK wrapper, child-ID summing |
| `backend/app/cache.py` | DuckDB upsert/fetch |
| `backend/app/aggregation.py` | 5y range/avg by ISO week, summary stats |
| `backend/app/refresh.py` | Backfill / incremental refresh orchestration |
| `backend/app/eia_reconcile.py` | EIA API call + delta calc |
| `backend/app/config.py` | YAML + env loader |
| `config/products.yaml` | Product key → Vortexa ID(s) |
| `config/geographies.yaml` | Geography key → Vortexa ID(s) |
| `scripts/resolve_ids.py` | Lookup helper for filling YAMLs |
| `scripts/backfill.py` | 5-year historical pull |
| `frontend/src/App.tsx` | Layout, state |
| `frontend/src/components/InventoryChart.tsx` | Recharts chart with range band + avg + current |
| `frontend/src/components/ChartCard.tsx` | Grid cell |
| `frontend/src/components/DeepDive.tsx` | Modal with full chart + stats + CSV download |
| `frontend/src/components/Sidebar.tsx` | Geography selector, product multi-select, frequency toggle |
| `frontend/src/components/Reconcile.tsx` | Vortexa vs EIA chip |
| `docker-compose.yml` | Backend + nginx-served frontend |
| `.env.example` | Credentials template (never commit a real key) |
