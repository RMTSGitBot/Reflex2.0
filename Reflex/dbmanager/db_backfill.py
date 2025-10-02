# dbmanager/db_backfill.py
# -----------------------------------------------------------------------------
# Backfill helpers for Reflex dbmanager
# - Respects common.config.PolygonParams (api_key, rest_base, ws_base)
# - Restores legacy entry points: refresh_recent, prime_moderate, prime_full
# - Daily path standardized to `timestamp TIMESTAMPTZ` (America/New_York -> UTC)
# - Tick/minute paths present but idle by default
# - Does NOT send 'day' (DB generated STORED column)
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import logging
import math
from dataclasses import dataclass
from datetime import datetime, date, time, timezone, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import Table, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

# HTTP client for Polygon
try:
    import requests
except Exception:
    requests = None  # type: ignore

# Optional market calendar (valid sessions)
try:
    import pandas_market_calendars as mcal
except Exception:
    mcal = None  # type: ignore

# Optional timezone helper
try:
    import pytz
except Exception:
    pytz = None  # type: ignore

# Prefer structured Polygon config from common.config
PolygonParamsT = None
try:
    from common.config import PolygonParams as _PolygonParams  # dataclass(frozen=True)
    PolygonParamsT = _PolygonParams
except Exception:
    PolygonParamsT = None  # fall back to env if not importable

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
log = logging.getLogger("dbmanager.backfill")
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    log.addHandler(_h)
log.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# Constants / schema assumptions (must match DB)
# -----------------------------------------------------------------------------
MARKET_TZ_NAME = "America/New_York"
MARKET_TZ = pytz.timezone(MARKET_TZ_NAME) if pytz else None

# Tables:
#   daily_bars(
#       symbol TEXT, timestamp TIMESTAMPTZ,
#       open NUMERIC(18,6), high NUMERIC(18,6), low NUMERIC(18,6), close NUMERIC(18,6),
#       volume BIGINT, PRIMARY KEY(symbol, timestamp)
#   )
#   tick_data(
#       symbol TEXT, timestamp TIMESTAMPTZ, sip_timestamp BIGINT,
#       price NUMERIC(18,6), size INT, exchange TEXT, conditions TEXT[],
#       tape TEXT, participant_id TEXT, is_trade_through BOOLEAN,
#       UNIQUE(symbol, timestamp, sip_timestamp)
#   )
#   `day DATE` is GENERATED ALWAYS (market day from timestamp)


@dataclass
class InsertResult:
    table: str
    attempted: int
    inserted: int


# -----------------------------------------------------------------------------
# DB / Engine helpers
# -----------------------------------------------------------------------------
def _build_db_url_from_config() -> str:
    try:
        # prefer your shared config
        from common.config import DB_PARAMS  # type: ignore
        if isinstance(DB_PARAMS, dict):
            dbname = DB_PARAMS.get("dbname", "timedata")
            user = DB_PARAMS.get("user", "postgres")
            password = DB_PARAMS.get("password", "")
            host = DB_PARAMS.get("host", "127.0.0.1")
            port = DB_PARAMS.get("port", 5432)
        else:
            dbname = getattr(DB_PARAMS, "dbname", "timedata")
            user = getattr(DB_PARAMS, "user", "postgres")
            password = getattr(DB_PARAMS, "password", "")
            host = getattr(DB_PARAMS, "host", "127.0.0.1")
            port = getattr(DB_PARAMS, "port", 5432)
    except Exception:
        # minimal fallback
        dbname = os.environ.get("PGDATABASE", "timedata")
        user = os.environ.get("PGUSER", "postgres")
        password = os.environ.get("PGPASSWORD", "")
        host = os.environ.get("PGHOST", "127.0.0.1")
        port = int(os.environ.get("PGPORT", "5432"))
    from urllib.parse import quote_plus
    return f"postgresql+psycopg://{user}:{quote_plus(str(password))}@{host}:{port}/{dbname}"


def _get_engine() -> Engine:
    """Prefer engine from Flask app context; otherwise build from config."""
    try:
        from flask import current_app  # imported lazily (only if app context)
        eng = current_app and current_app.config.get("ENGINE")
        if eng is not None:
            return eng
    except Exception:
        pass
    from sqlalchemy import create_engine
    return create_engine(
        _build_db_url_from_config(),
        future=True,
        pool_pre_ping=True,
        execution_options={"insertmanyvalues_page_size": 1000},
    )


# -----------------------------------------------------------------------------
# Polygon config & fetch (daily only)
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class _PolygonCfg:
    api_key: str
    rest_base: str
    ws_base: str


def _get_polygon_cfg() -> _PolygonCfg:
    """
    Preferred: common.config.PolygonParams(api_key, rest_base, ws_base)
    Fallback: POLYGON_* environment variables (with sane defaults).
    """
    if PolygonParamsT is not None:
        try:
            pp = PolygonParamsT()  # dataclass defaults pull from env if your code does that
            return _PolygonCfg(api_key=pp.api_key, rest_base=pp.rest_base, ws_base=pp.ws_base)
        except Exception as e:
            log.warning("PolygonParams dataclass not usable, falling back to env: %s", e)

    api_key = os.getenv("POLYGON_API_KEY", "")
    rest_base = os.getenv("POLYGON_REST_BASE", "https://api.polygon.io")
    ws_base = os.getenv("POLYGON_WS_BASE", "wss://socket.polygon.io/stocks")
    return _PolygonCfg(api_key=api_key, rest_base=rest_base, ws_base=ws_base)


def _fetch_polygon_daily(symbol: str, start_d: date, end_d: date) -> List[Dict[str, Any]]:
    """
    Calls Polygon Aggregates v2 using rest_base from PolygonParams:
      GET {rest_base}/v2/aggs/ticker/{symbol}/range/1/day/{from}/{to}?adjusted=true&sort=asc&limit=50000&apiKey=...
    """
    cfg = _get_polygon_cfg()
    if not cfg.api_key:
        raise RuntimeError("Polygon API key not available (PolygonParams.api_key / POLYGON_API_KEY)")

    if requests is None:
        raise RuntimeError("The 'requests' package is required for Polygon calls")

    fr, to = start_d.isoformat(), end_d.isoformat()
    base = cfg.rest_base.rstrip("/")
    url = f"{base}/v2/aggs/ticker/{symbol}/range/1/day/{fr}/{to}"
    params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": cfg.api_key}

    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Polygon daily fetch failed ({resp.status_code}): {resp.text[:200]}")

    data = resp.json() or {}
    results = data.get("results") or []
    return results


def _polygon_to_daily_df(symbol: str, rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert Polygon aggregate rows to DataFrame:
      - 't' => epoch ms -> TIMESTAMPTZ aware UTC
      - 'o','h','l','c','v'
    """
    if not rows:
        return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])

    ts_utc = pd.to_datetime([r.get("t") for r in rows], unit="ms", utc=True)
    df = pd.DataFrame(
        {
            "symbol": [symbol] * len(rows),
            "timestamp": ts_utc,
            "open": [r.get("o") for r in rows],
            "high": [r.get("h") for r in rows],
            "low": [r.get("l") for r in rows],
            "close": [r.get("c") for r in rows],
            "volume": [r.get("v") for r in rows],
        }
    )
    # Normalize numeric types
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce").round(6)
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("Int64")
    return df


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def _to_utc_ts_from_datelike(series: pd.Series) -> pd.Series:
    """
    Convert a Series of date/datetime strings to tz-aware UTC datetimes.
    If value is a date string like '2025-09-30', localize to NY midnight -> UTC.
    If already tz-aware, convert to UTC.
    """
    if series.empty:
        return series

    s = pd.to_datetime(series, errors="coerce")

    def _localize_or_convert(dt: pd.Timestamp) -> pd.Timestamp:
        if pd.isna(dt):
            return dt
        if dt.tzinfo is None:
            if MARKET_TZ is None:
                return dt.replace(tzinfo=timezone.utc)
            ny_midnight = pd.Timestamp(year=dt.year, month=dt.month, day=dt.day)
            return MARKET_TZ.localize(ny_midnight).tz_convert("UTC")
        return dt.tz_convert("UTC")

    return s.apply(_localize_or_convert)


def _numeric(series: pd.Series, scale: Optional[int] = None) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if scale is not None:
        return s.round(scale)
    return s


def _as_bigint(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    return s.astype("Int64")


def _daily_dtypes() -> dict:
    return {
        "symbol": sa.types.String(),
        "timestamp": sa.types.DateTime(timezone=True),
        "open": sa.types.Numeric(18, 6),
        "high": sa.types.Numeric(18, 6),
        "low": sa.types.Numeric(18, 6),
        "close": sa.types.Numeric(18, 6),
        "volume": sa.types.BigInteger(),
    }


def _normalize_daily_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize vendor daily payload to DB schema:
      required columns: symbol, timestamp, open, high, low, close, volume
      vendor may send `date` -> map to `timestamp`
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])

    col_map = {}
    if "date" in df.columns:
        col_map["date"] = "timestamp"
    df = df.rename(columns=col_map)

    keep = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
    for col in keep:
        if col not in df.columns:
            df[col] = pd.NA

    df["symbol"] = df["symbol"].astype(str)
    if "timestamp" in df.columns:
        df["timestamp"] = _to_utc_ts_from_datelike(df["timestamp"])

    for col in ("open", "high", "low", "close"):
        df[col] = _numeric(df[col], scale=6)
    df["volume"] = _as_bigint(df["volume"])

    df = df[keep]
    df = df.dropna(subset=["symbol", "timestamp"])
    return df


def last_market_day_check(reference_dt: datetime | None = None) -> datetime:
    """
    Returns the most recent valid US market day (end-of-day UTC) before or on reference_dt.
    Defaults to now (UTC) if not provided.
    """
    if mcal is None:
        dt = reference_dt or datetime.utcnow()
        resolved = datetime(dt.year, dt.month, dt.day, 23, 59, tzinfo=timezone.utc)
        log.warning("pandas_market_calendars not available; fallback last market day: %s", resolved)
        return resolved

    dt = reference_dt or datetime.utcnow()
    nyse = mcal.get_calendar("NYSE")
    schedule = nyse.valid_days(
        start_date=(dt - timedelta(days=10)).date().isoformat(),
        end_date=dt.date().isoformat(),
    )
    if schedule.empty:
        raise ValueError("No valid market days found in range")

    last_valid = schedule[-1].to_pydatetime()  # midnight UTC of session
    resolved = datetime.combine(last_valid.date(), time(23, 59), tzinfo=timezone.utc)
    log.info("📅 Resolved last market day: %s", resolved)
    return resolved


def _ns_or_dt_to_utc_dt(value) -> Optional[datetime]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(int(value) / 1e9, tz=timezone.utc)
        except Exception:
            return None
    try:
        t = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(t):
            return None
        return t.to_pydatetime()
    except Exception:
        return None


def _safe_page_size(params_per_row: int, max_params: int = 65535, margin: int = 2000) -> int:
    if params_per_row <= 0:
        return 1000
    return max(1, (max_params - margin) // params_per_row)


def _reflect_table(engine: Engine, name: str) -> Table:
    md = MetaData()
    return Table(name, md, autoload_with=engine, schema=None)  # assumes 'public'


# -----------------------------------------------------------------------------
# Backfill dispatcher (preserves original routine and signature)
# -----------------------------------------------------------------------------
def run_backfill(
    symbols,
    mode: str = "recent",
    start=None,
    end=None,
    store_daily: bool = True,
    store_minute: bool = True,
    store_tick: bool = True,
):
    """
    Backward-compatible backfill orchestrator.

    Preserves original behavior:
        - recent   -> refresh_recent(symbols)
        - moderate -> prime_moderate(symbols)
        - full     -> prime_full(symbols)

    Upgrades: optional range (start/end) via backfill_range if you add one.
    """
    if isinstance(symbols, str):
        symbols = [symbols]
    symbols = [s.strip().upper() for s in symbols if s and str(s).strip()]
    mode = (mode or "recent").strip().lower()

    log.info(
        "🚀 run_backfill: mode=%s symbols=%s start=%s end=%s | store_daily=%s store_minute=%s store_tick=%s",
        mode, symbols, start, end, store_daily, store_minute, store_tick
    )

    # Optional range path (if you add backfill_range later)
    if (start is not None or end is not None) and "backfill_range" in globals():
        try:
            result = backfill_range(  # type: ignore[name-defined]
                symbols=symbols,
                start=start,
                end=end,
                store_daily=store_daily,
                store_minute=store_minute,
                store_tick=store_tick,
            )
            log.info("✅ run_backfill(backfill_range) complete")
            return {"mode": "range", "symbols": symbols, "result": result}
        except Exception as e:
            log.warning("⚠️ backfill_range failed, falling back to mode switch: %s", e)

    # Legacy dispatch (restored below)
    if mode == "recent":
        res = refresh_recent(symbols)
        log.info("✅ run_backfill recent complete")
        return {"mode": mode, "symbols": symbols, "result": res}

    elif mode == "moderate":
        res = prime_moderate(symbols)
        log.info("✅ run_backfill moderate complete")
        return {"mode": mode, "symbols": symbols, "result": res}

    elif mode == "full":
        res = prime_full(symbols)
        log.info("✅ run_backfill full complete")
        return {"mode": mode, "symbols": symbols, "result": res}

    else:
        raise ValueError(f"Unknown backfill mode: {mode}")


# -----------------------------------------------------------------------------
# Public API (used by app route)
# -----------------------------------------------------------------------------
def insert_dataframe(table_name: str, engine: Engine, df: pd.DataFrame) -> InsertResult:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("insert_dataframe: df must be a pandas.DataFrame")

    if table_name == "daily_bars":
        norm = _normalize_daily_df(df)
        if norm.empty:
            log.info("No daily rows to insert.")
            return InsertResult(table=table_name, attempted=0, inserted=0)

        dtypes = _daily_dtypes()
        with engine.begin() as conn:
            conn = conn.execution_options(insertmanyvalues_page_size=1000)
            norm.to_sql(
                "daily_bars",
                conn,
                if_exists="append",
                index=False,
                method="multi",
                dtype=dtypes,
                chunksize=1000,
            )
        return InsertResult(table=table_name, attempted=len(norm), inserted=len(norm))

    if table_name == "minute_bars":
        log.info("Minute bar insertion requested via insert_dataframe; currently disabled.")
        return InsertResult(table=table_name, attempted=0, inserted=0)

    if table_name in ("tick_data", "ticks"):
        log.info("Tick insertion requested via insert_dataframe; call insert_tick_dataframe() instead.")
        return InsertResult(table=table_name, attempted=0, inserted=0)

    # Fallback generic append (discouraged)
    log.warning("Unknown table '%s' passed to insert_dataframe; attempting generic append.", table_name)
    with engine.begin() as conn:
        conn = conn.execution_options(insertmanyvalues_page_size=1000)
        df.to_sql(table_name, conn, if_exists="append", index=False, method="multi", chunksize=1000)
    return InsertResult(table=table_name, attempted=len(df), inserted=len(df))


def insert_minute_dataframe(engine: Engine, df: pd.DataFrame) -> InsertResult:
    if df is None or df.empty:
        return InsertResult(table="minute_bars", attempted=0, inserted=0)

    df = df.copy()
    if "ts" in df.columns and "timestamp" not in df.columns:
        df = df.rename(columns={"ts": "timestamp"})

    df["timestamp"] = _to_utc_ts_from_datelike(df["timestamp"])
    for col in ("open", "high", "low", "close"):
        df[col] = _numeric(df[col], scale=6)
    df["volume"] = _as_bigint(df.get("volume"))

    keep = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
    for k in keep:
        if k not in df.columns:
            df[k] = pd.NA
    df = df[keep].dropna(subset=["symbol", "timestamp"])

    dtypes = _daily_dtypes()
    with engine.begin() as conn:
        conn = conn.execution_options(insertmanyvalues_page_size=1000)
        df.to_sql("minute_bars", conn, if_exists="append", index=False, method="multi", dtype=dtypes, chunksize=1000)
    return InsertResult(table="minute_bars", attempted=len(df), inserted=len(df))


def insert_tick_dataframe(engine: Engine, df: pd.DataFrame, page_size: Optional[int] = None) -> InsertResult:
    table_name = "tick_data"
    if df is None or df.empty:
        return InsertResult(table=table_name, attempted=0, inserted=0)

    tick_table = _reflect_table(engine, table_name)

    SCHEMA_KEYS = [
        "symbol", "timestamp", "sip_timestamp", "price", "size",
        "exchange", "conditions", "tape", "participant_id", "is_trade_through"
    ]

    records: list[dict] = []
    for _, row in df.iterrows():
        r = {}
        r["symbol"] = str(row.get("symbol")) if row.get("symbol") is not None else None
        r["timestamp"] = _ns_or_dt_to_utc_dt(row.get("timestamp"))
        st = row.get("sip_timestamp")
        if st is None or (isinstance(st, float) and math.isnan(st)):
            r["sip_timestamp"] = None
        else:
            try:
                r["sip_timestamp"] = int(st)
            except Exception:
                r["sip_timestamp"] = None
        r["price"] = None if pd.isna(row.get("price")) else float(row.get("price"))
        r["size"] = None if pd.isna(row.get("size")) else int(row.get("size"))
        r["exchange"] = None if pd.isna(row.get("exchange")) else str(row.get("exchange"))
        r["tape"] = None if pd.isna(row.get("tape")) else str(row.get("tape"))
        r["participant_id"] = None if pd.isna(row.get("participant_id")) else str(row.get("participant_id"))
        cond = row.get("conditions")
        if cond is None or pd.isna(cond):
            r["conditions"] = []
        elif isinstance(cond, (list, tuple)):
            r["conditions"] = [str(x) for x in cond]
        else:
            r["conditions"] = [str(cond)]
        it = row.get("is_trade_through")
        r["is_trade_through"] = False if it is None or (isinstance(it, float) and math.isnan(it)) else bool(it)

        rec = {k: r.get(k) for k in SCHEMA_KEYS}
        if not rec["symbol"] or rec["timestamp"] is None or rec["sip_timestamp"] is None:
            continue
        records.append(rec)

    if not records:
        return InsertResult(table=table_name, attempted=0, inserted=0)

    params_per_row = len(SCHEMA_KEYS)
    chunk = page_size or _safe_page_size(params_per_row)

    base_ins = pg_insert(tick_table)
    excluded = base_ins.excluded
    upsert_set = {
        "price": excluded.price,
        "size": excluded.size,
        "exchange": excluded.exchange,
        "conditions": excluded.conditions,
        "tape": excluded.tape,
        "participant_id": excluded.participant_id,
        "is_trade_through": excluded.is_trade_through,
    }

    total = 0
    with _get_engine().begin() as conn:
        conn = conn.execution_options(insertmanyvalues_page_size=chunk)
        for i in range(0, len(records), chunk):
            batch = records[i:i + chunk]
            stmt = base_ins.values(batch).on_conflict_do_update(
                index_elements=[tick_table.c.symbol, tick_table.c.timestamp, tick_table.c.sip_timestamp],
                set_=upsert_set,
            )
            conn.execute(stmt)
            total += len(batch)

    return InsertResult(table=table_name, attempted=len(records), inserted=total)


# -----------------------------------------------------------------------------
# Legacy entry points (RESTORED) - daily only
# -----------------------------------------------------------------------------
def _daily_backfill(symbols: List[str], start_d: date, end_d: date) -> Dict[str, Dict[str, int]]:
    """
    Fetches daily bars from Polygon for each symbol and inserts into daily_bars.
    Returns per-symbol counts: {"SYMB": {"daily": N}}
    """
    engine = _get_engine()
    summary: Dict[str, Dict[str, int]] = {}
    for sym in symbols:
        try:
            rows = _fetch_polygon_daily(sym, start_d, end_d)
            df = _polygon_to_daily_df(sym, rows)
            res = insert_dataframe("daily_bars", engine, df)
            summary[sym] = {"daily": res.inserted}
            log.info("✅ %s %s..%s: daily=%d", sym, start_d, end_d, res.inserted)
        except Exception as e:
            log.warning("❌ daily backfill failed for %s: %s", sym, e)
            summary[sym] = {"daily": 0}
    return summary


def refresh_recent(symbols: List[str]) -> Dict[str, Dict[str, int]]:
    """
    Backfill the most recent market day (daily only).
    """
    last = last_market_day_check()
    return _daily_backfill(symbols, last.date(), last.date())


def prime_moderate(symbols: List[str]) -> Dict[str, Dict[str, int]]:
    """
    Backfill the last 7 valid market days (calendar range).
    """
    end_dt = last_market_day_check()
    start_dt = end_dt - timedelta(days=7)
    return _daily_backfill(symbols, start_dt.date(), end_dt.date())


def prime_full(symbols: List[str]) -> Dict[str, Dict[str, int]]:
    """
    Backfill the last 365 calendar days (daily only).
    """
    end_dt = last_market_day_check()
    start_dt = end_dt - timedelta(days=365)
    return _daily_backfill(symbols, start_dt.date(), end_dt.date())