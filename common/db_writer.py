from datetime import datetime
import pandas as pd
from .dbutils import get_connection
from .cleaners import _clean_str, _parse_numeric
from .app_logging import setup_logger
from shared_mem.registry import registry

log = setup_logger("db_writer")

# ─────────────────────────────────────────────
# 🧠 Fundamentals Writer
# ─────────────────────────────────────────────

def upsert_fundamentals_for_symbol(df: pd.DataFrame, symbol: str, mode="COLD"):
    if df is None or df.empty:
        log.warning(f"⚠️ No fundamentals for {symbol}")
        return

    symbol = symbol.upper()
    row = df[df["symbol"].str.upper() == symbol]
    if row.empty:
        log.warning(f"⚠️ Symbol {symbol} not found in fundamentals view")
        return

    row = row.iloc[0]

    metadata_record = (symbol, mode)
    fundamentals_record = (
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
    )

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO symbol_metadata (symbol, mode, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (symbol) DO UPDATE SET
                    mode = EXCLUDED.mode,
                    last_updated = NOW();
            """, metadata_record)

            cur.execute("""
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
            """, fundamentals_record)

        conn.commit()
        log.info(f"✅ Fundamentals upserted for {symbol} (mode={mode})")

    except Exception as e:
        conn.rollback()
        log.error(f"❌ Fundamentals upsert failed for {symbol}: {e}")

    finally:
        conn.close()

# ─────────────────────────────────────────────
# 📊 Daily Bars Writer
# ─────────────────────────────────────────────

def upsert_daily_bars_for_symbol(df: pd.DataFrame, symbol: str):
    if df is None or df.empty:
        log.warning(f"⚠️ No daily bars for {symbol}")
        return

    symbol = symbol.upper()
    rows = df[df["symbol"].str.upper() == symbol]
    if rows.empty:
        log.warning(f"⚠️ No daily rows found for {symbol}")
        return

    batch = [
        (
            symbol,
            row["timestamp"],
            row["open"],
            row["high"],
            row["low"],
            row["close"],
            row["volume"]
        )
        for _, row in rows.iterrows()
    ]

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO daily_bars (symbol, timestamp, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, timestamp) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume;
            """, batch)

        conn.commit()
        log.info(f"✅ Daily bars upserted for {symbol}: {len(batch)} records")

    except Exception as e:
        conn.rollback()
        log.error(f"❌ Daily bars upsert failed for {symbol}: {e}")

    finally:
        conn.close()

# ─────────────────────────────────────────────
# 🕒 Minute Bars Writer
# ─────────────────────────────────────────────

def upsert_minute_bars_for_symbol(df: pd.DataFrame, symbol: str):
    if df is None or df.empty:
        log.warning(f"⚠️ No minute bars for {symbol}")
        return

    symbol = symbol.upper()
    rows = df[df["symbol"].str.upper() == symbol]
    if rows.empty:
        log.warning(f"⚠️ No minute rows found for {symbol}")
        return

    batch = [
        (
            symbol,
            row["timestamp"],
            row["open"],
            row["high"],
            row["low"],
            row["close"],
            row["volume"]
        )
        for _, row in rows.iterrows()
    ]

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO minute_bars (symbol, timestamp, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, timestamp) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume;
            """, batch)

        conn.commit()
        log.info(f"✅ Minute bars upserted for {symbol}: {len(batch)} records")

    except Exception as e:
        conn.rollback()
        log.error(f"❌ Minute bars upsert failed for {symbol}: {e}")

    finally:
        conn.close()

# ─────────────────────────────────────────────
# 🧵 Tick Writer
# ─────────────────────────────────────────────

def upsert_ticks_for_symbol(df: pd.DataFrame, symbol: str):
    if df is None or df.empty:
        log.warning(f"⚠️ No ticks for {symbol}")
        return

    symbol = symbol.upper()
    rows = df[df["symbol"].str.upper() == symbol]
    if rows.empty:
        log.warning(f"⚠️ No tick rows found for {symbol}")
        return

    batch = [
        (
            symbol,
            row["timestamp"],
            row["price"],
            row["size"],
            row.get("conditions", [])
        )
        for _, row in rows.iterrows()
    ]

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO tick_data (symbol, timestamp, price, size, conditions)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (symbol, timestamp, sip_timestamp) DO UPDATE SET
                    price = EXCLUDED.price,
                    size = EXCLUDED.size,
                    conditions = EXCLUDED.conditions;
            """, batch)

        conn.commit()
        log.info(f"✅ Ticks upserted for {symbol}: {len(batch)} records")

    except Exception as e:
        conn.rollback()
        log.error(f"❌ Tick upsert failed for {symbol}: {e}")

    finally:
        conn.close()

# ─────────────────────────────────────────────
# 🧹 Tick Deletion
# ─────────────────────────────────────────────

def delete_ticks_for_day(symbol: str, date: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            log.info(f"🧹 Deleting ticks for {symbol} on {date}")
            cur.execute("""
                DELETE FROM tick_data
                WHERE symbol = %s AND timestamp::date = %s
            """, (symbol, date))
        conn.commit()
        log.info(f"✅ Deleted ticks for {symbol} on {date}")
    except Exception as e:
        conn.rollback()
        log.error(f"❌ Failed to delete ticks for {symbol} on {date}: {e}")
    finally:
        conn.close()