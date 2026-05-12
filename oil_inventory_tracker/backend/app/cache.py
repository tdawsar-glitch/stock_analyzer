"""DuckDB-backed cache for Vortexa onshore inventory pulls.

Schema:
    inventory(
        product_key   TEXT,
        geography_key TEXT,
        date          DATE,
        value_bbl     DOUBLE,
        partial       BOOLEAN,
        fetched_at    TIMESTAMP,
        PRIMARY KEY (product_key, geography_key, date)
    )

    refresh_log(
        product_key   TEXT,
        geography_key TEXT,
        started_at    TIMESTAMP,
        ended_at      TIMESTAMP,
        rows_upserted INTEGER,
        status        TEXT,
        error         TEXT
    )
"""
from __future__ import annotations

import datetime as dt
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Optional

import duckdb
import pandas as pd


_DDL = [
    """
    CREATE TABLE IF NOT EXISTS inventory (
        product_key   TEXT      NOT NULL,
        geography_key TEXT      NOT NULL,
        date          DATE      NOT NULL,
        value_bbl     DOUBLE,
        partial       BOOLEAN   DEFAULT FALSE,
        fetched_at    TIMESTAMP NOT NULL,
        PRIMARY KEY (product_key, geography_key, date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS refresh_log (
        product_key   TEXT,
        geography_key TEXT,
        started_at    TIMESTAMP,
        ended_at      TIMESTAMP,
        rows_upserted INTEGER,
        status        TEXT,
        error         TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_inventory_pg ON inventory(product_key, geography_key)",
]


class Cache:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as con:
            for stmt in _DDL:
                con.execute(stmt)

    @contextmanager
    def _connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        # DuckDB single-writer: serialize with a lock; readers are fine
        # under the same connection since we use short transactions.
        with self._lock:
            con = duckdb.connect(str(self.db_path))
            try:
                yield con
            finally:
                con.close()

    def upsert(
        self,
        product_key: str,
        geography_key: str,
        df: pd.DataFrame,
        partial: bool = False,
    ) -> int:
        """Upsert daily observations. `df` columns: date, value_bbl."""
        if df is None or df.empty:
            return 0
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["product_key"] = product_key
        df["geography_key"] = geography_key
        df["partial"] = partial
        df["fetched_at"] = dt.datetime.utcnow()
        df = df[["product_key", "geography_key", "date", "value_bbl",
                 "partial", "fetched_at"]]
        with self._connect() as con:
            con.register("incoming", df)
            con.execute(
                """
                INSERT INTO inventory
                SELECT * FROM incoming
                ON CONFLICT (product_key, geography_key, date)
                DO UPDATE SET
                    value_bbl  = excluded.value_bbl,
                    partial    = excluded.partial,
                    fetched_at = excluded.fetched_at
                """
            )
            con.unregister("incoming")
        return len(df)

    def fetch(
        self,
        product_key: str,
        geography_key: str,
        start: Optional[dt.date] = None,
        end: Optional[dt.date] = None,
    ) -> pd.DataFrame:
        q = """
            SELECT date, value_bbl, partial
            FROM inventory
            WHERE product_key = ? AND geography_key = ?
        """
        params: list = [product_key, geography_key]
        if start is not None:
            q += " AND date >= ?"
            params.append(start)
        if end is not None:
            q += " AND date <= ?"
            params.append(end)
        q += " ORDER BY date"
        with self._connect() as con:
            return con.execute(q, params).fetch_df()

    def last_observation(self, product_key: str, geography_key: str) -> Optional[dt.date]:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT max(date) FROM inventory
                WHERE product_key = ? AND geography_key = ?
                """,
                [product_key, geography_key],
            ).fetchone()
        return row[0] if row and row[0] else None

    def last_refresh(self) -> Optional[dt.datetime]:
        with self._connect() as con:
            row = con.execute(
                "SELECT max(ended_at) FROM refresh_log WHERE status = 'ok'"
            ).fetchone()
        return row[0] if row and row[0] else None

    def log_refresh(
        self,
        product_key: str,
        geography_key: str,
        started_at: dt.datetime,
        ended_at: dt.datetime,
        rows_upserted: int,
        status: str,
        error: str | None = None,
    ) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO refresh_log VALUES (?, ?, ?, ?, ?, ?, ?)",
                [product_key, geography_key, started_at, ended_at,
                 rows_upserted, status, error],
            )

    def pairs_with_data(self) -> Iterable[tuple[str, str]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT DISTINCT product_key, geography_key FROM inventory"
            ).fetchall()
        return rows
