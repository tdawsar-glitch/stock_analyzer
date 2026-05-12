"""Configuration loading: env vars + YAML reference maps."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

# Project root resolution:
#   - dev layout:    .../oil_inventory_tracker/backend/app/config.py  -> ROOT = oil_inventory_tracker/
#   - docker layout: /app/app/config.py with config copied to /app/config
# parents[2] gives us the right directory in both cases.
ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(os.getenv("OIT_CONFIG_DIR") or (ROOT / "config"))

# Try a few common .env locations; dotenv is a no-op if the file is missing.
for _candidate in (ROOT / ".env", Path.cwd() / ".env"):
    if _candidate.exists():
        load_dotenv(_candidate)
        break


@dataclass
class Product:
    key: str
    label: str
    vortexa_search_term: str
    id: str
    children: list[str] = field(default_factory=list)
    display_unit: str = "kb"

    @property
    def resolved_ids(self) -> list[str]:
        return [i for i in ([self.id] + list(self.children)) if i]


@dataclass
class Geography:
    key: str
    label: str
    kind: str          # global | region | country | hub
    id: str
    children: list[str] = field(default_factory=list)
    eia_reconcile: bool = False

    @property
    def resolved_ids(self) -> list[str]:
        return [i for i in ([self.id] + list(self.children)) if i]


@dataclass
class Settings:
    vortexa_api_key: Optional[str]
    eia_api_key: Optional[str]
    admin_token: Optional[str]
    cache_db_path: Path
    refresh_cron: str
    backend_host: str
    backend_port: int
    products: dict[str, Product]
    geographies: dict[str, Geography]


def _load_products() -> dict[str, Product]:
    with open(CONFIG_DIR / "products.yaml", "r") as f:
        raw = yaml.safe_load(f) or {}
    return {p["key"]: Product(**p) for p in raw.get("products", [])}


def _load_geographies() -> dict[str, Geography]:
    with open(CONFIG_DIR / "geographies.yaml", "r") as f:
        raw = yaml.safe_load(f) or {}
    return {g["key"]: Geography(**g) for g in raw.get("geographies", [])}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    cache_path = Path(os.getenv("CACHE_DB_PATH", "./data/inventory_cache.duckdb"))
    if not cache_path.is_absolute():
        cache_path = (ROOT / "backend" / cache_path).resolve()
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        vortexa_api_key=os.getenv("VORTEXA_API_KEY") or None,
        eia_api_key=os.getenv("EIA_API_KEY") or None,
        admin_token=os.getenv("ADMIN_TOKEN") or None,
        cache_db_path=cache_path,
        refresh_cron=os.getenv("REFRESH_CRON", "15 6 * * *"),
        backend_host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        products=_load_products(),
        geographies=_load_geographies(),
    )
