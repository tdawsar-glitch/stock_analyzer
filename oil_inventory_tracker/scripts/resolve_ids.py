"""Resolve Vortexa product and geography names to IDs.

Run once after installing the SDK and setting VORTEXA_API_KEY:

    python -m scripts.resolve_ids

This prints suggested IDs for every entry in config/products.yaml and
config/geographies.yaml. Copy the IDs into the YAMLs by hand — the script
does NOT auto-mutate the config so that you can review ambiguous matches
(e.g. "Fuel Oil" matches several Vortexa sub-products).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make backend/app importable when running as `python -m scripts.resolve_ids`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402


def main() -> int:
    try:
        from vortexasdk import Geographies, Products  # type: ignore
    except ImportError:
        print("vortexasdk is not installed. pip install vortexasdk", file=sys.stderr)
        return 2

    settings = get_settings()
    if not settings.vortexa_api_key:
        print("VORTEXA_API_KEY is not set. Populate .env first.", file=sys.stderr)
        return 2

    print("\n=== Products ===")
    for p in settings.products.values():
        try:
            df = Products().search(term=p.vortexa_search_term).to_df()
        except Exception as e:  # noqa: BLE001
            print(f"  {p.key:10s}  ERROR: {e}")
            continue
        print(f"\n  [{p.key}] search='{p.vortexa_search_term}'")
        cols = [c for c in ("id", "name", "layer", "leaf") if c in df.columns]
        print(df[cols].head(10).to_string(index=False))

    print("\n\n=== Geographies ===")
    for g in settings.geographies.values():
        if g.key == "global":
            print(f"\n  [{g.key}] uses worldwide aggregate — leave id/children empty.")
            continue
        try:
            df = Geographies().search(term=g.label.split(" ")[0]).to_df()
        except Exception as e:  # noqa: BLE001
            print(f"  {g.key:14s}  ERROR: {e}")
            continue
        print(f"\n  [{g.key}] search='{g.label}'")
        cols = [c for c in ("id", "name", "layer", "country", "exclusion_rule")
                if c in df.columns]
        print(df[cols].head(10).to_string(index=False))

    print("\nDone. Copy the IDs you want into config/products.yaml and "
          "config/geographies.yaml.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
