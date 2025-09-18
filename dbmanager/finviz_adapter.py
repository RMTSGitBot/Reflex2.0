# dbmanager/finviz_adapter.py
import os, sys
import pandas as pd
import time
from datetime import datetime


CURRENT_FILE = os.path.abspath(__file__)
DBMANAGER_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_ROOT = os.path.abspath(os.path.join(DBMANAGER_DIR, ".."))
COMMON_PATH = os.path.join(PROJECT_ROOT, "common")
if COMMON_PATH not in sys.path:
    sys.path.append(COMMON_PATH)

from common.app_logging import setup_logger
from common.dbutils import get_connection  
from common.poly_tools import fetch_safe_start_date  # or any reliable validation call
log = setup_logger("finviz_adapter")

try:
    from finvizfinance.screener.overview import Overview
    from finvizfinance.screener.ownership import Ownership
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "finvizfinance"])
    from finvizfinance.screener.overview import Overview
    from finvizfinance.screener.ownership import Ownership


def is_polygon_valid(symbol: str) -> bool:
    try:
        return fetch_safe_start_date(symbol) is not None
    except Exception as e:
        log.warning(f"[⚠️] Polygon validation failed for {symbol}: {e}")
        return False
    
def fetch_finviz_fundamentals(exchanges=["NASDAQ", "NYSE", "AMEX"]) -> pd.DataFrame:
    all_dfs = []

    filters = {
        "Exchange": None,  # set per loop
        "Market Cap.": "Small ($300mln to $2bln)",
        "Price": "Over $1"
    }

    for exch in exchanges:
        print(f"[Finviz] Fetching batch for {exch}...")
        try:
            filters["Exchange"] = exch

            overview = Overview()
            overview.set_filter(filters_dict=filters)
            df_overview = overview.screener_view()

            if df_overview is None or df_overview.empty:
                print(f"[WARN] Overview screener returned no data for {exch}")
                continue

            df_overview.columns = [f"overview_{col}" for col in df_overview.columns]
            print(f"[DEBUG] Overview rows: {len(df_overview)}")

            ownership = Ownership()
            ownership.set_filter(filters_dict=filters)
            df_ownership = ownership.screener_view()

            if df_ownership is None or df_ownership.empty:
                print(f"[WARN] Ownership screener returned no data for {exch}")
                continue

            df_ownership.columns = [f"ownership_{col}" for col in df_ownership.columns]
            print(f"[DEBUG] Ownership rows: {len(df_ownership)}")

            df = pd.merge(
                df_overview,
                df_ownership,
                left_on="overview_Ticker",
                right_on="ownership_Ticker",
                how="outer"
            )

            if df.empty:
                print(f"[WARN] Merge produced empty DataFrame for {exch}")
                continue

            df.drop(columns=["ownership_Ticker"], inplace=True, errors="ignore")
            df.rename(columns={"overview_Ticker": "symbol"}, inplace=True)
            df["source_exchange"] = exch
            all_dfs.append(df)
            print(f"[INFO] Merged {len(df)} rows for {exch}")
            print(df.head())

        except Exception as e:
            print(f"[ERROR] Failed for exchange {exch}: {e}")

    if not all_dfs:
        print("[ERROR] No data fetched from any exchange.")
        return pd.DataFrame()

    return pd.concat(all_dfs, ignore_index=True)


def _clean_str(value):
    return str(value).strip() if value else None

def _parse_numeric(value, max_abs=1e6):
    try:
        val = str(value).replace('%', '').replace(',', '').strip()
        if val in ("N/A", "-", "—", "", None):
            return None
        parsed = float(val)
        return parsed if abs(parsed) < max_abs else None
    except:
        return None

VALID_MODES = {"NOT", "COLD", "WARM", "HOT"}

def sanitize_mode(symbol: str, mode: str) -> str:
    mode = mode.upper().strip() if mode else "NOT"
    if mode not in VALID_MODES:
        log.warning(f"[⚠️] Invalid mode '{mode}' for {symbol}, defaulting to 'NOT'")
        mode = "NOT"

    if not is_polygon_valid(symbol):
        log.warning(f"[🚫] {symbol} failed Polygon validation, forcing mode to 'NOT'")
        mode = "NOT"

    return mode

def map_and_upsert(df, default_mode="COLD"):
    if df is None or df.empty:
        log.warning("⚠️ No data to ingest.")
        return

    start_time = time.time()
    conn = get_connection()
    added, updated, failed = 0, 0, 0

    metadata_batch = []
    fundamentals_batch = []
    



    
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", "")).upper()
       
        if not symbol:
            continue
        
        # Validate mode from incoming row
        incoming_mode = str(row.get("mode", default_mode)).upper().strip()
        mode = incoming_mode if incoming_mode in VALID_MODES else default_mode
        print(f"MODE - {mode}")

        # Polygon gate
        if not is_polygon_valid(symbol):
            mode = "NOT"
            log.warning(f"[🚫] {symbol} forced to NOT: failed Polygon validation")

        metadata_batch.append((symbol, mode))

        if mode != "NOT":
            fundamentals_batch.append((
                symbol,
                _clean_str(row.get("overview_Company")),
                _clean_str(row.get("overview_Sector")),
                _clean_str(row.get("overview_Industry")),
                _clean_str(row.get("overview_Country")),
                _clean_str(row.get("source_exchange")),
                _parse_numeric(row.get("overview_Market Cap")),
                _parse_numeric(row.get("overview_P/E")),
                _parse_numeric(row.get("ownership_Shares Float")),
                _parse_numeric(row.get("ownership_Float")),
                _parse_numeric(row.get("ownership_InsiderTransactions")),
                _parse_numeric(row.get("ownership_Float Short")),
                _parse_numeric(row.get("overview_Average True Range")),
                datetime.utcnow()
            ))

    try:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO symbol_metadata (symbol, mode, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (symbol) DO UPDATE SET
                    mode = EXCLUDED.mode,
                    last_updated = NOW();
            """, metadata_batch)

            if fundamentals_batch:
                cur.executemany("""
                    INSERT INTO fundamental_data (
                        symbol, company, sector, industry, country, exchange,
                        market_cap, pe_ratio, shares_float, float_percent,
                        insider_transactions, short_float, average_true_range, last_updated
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (symbol) DO UPDATE SET
                        company = EXCLUDED.company,
                        sector = EXCLUDED.sector,
                        industry = EXCLUDED.industry,
                        country = EXCLUDED.country,
                        exchange = EXCLUDED.exchange,
                        market_cap = EXCLUDED.market_cap,
                        pe_ratio = EXCLUDED.pe_ratio,
                        shares_float = EXCLUDED.shares_float,
                        float_percent = EXCLUDED.float_percent,
                        insider_transactions = EXCLUDED.insider_transactions,
                        short_float = EXCLUDED.short_float,
                        average_true_range = EXCLUDED.average_true_range,
                        last_updated = EXCLUDED.last_updated;
                """, fundamentals_batch)

        # Optional: count added/updated if needed
        # This requires reloading existing symbols, but can be skipped for speed

    except Exception as e:
        failed = len(metadata_batch)
        log.error(f"[ERROR] Batch upsert failed: {e}")

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time
    log.info(f"✅ Ingestion complete: {len(metadata_batch)} symbols processed, ⚠️ {failed} failed in {elapsed:.2f}s.")