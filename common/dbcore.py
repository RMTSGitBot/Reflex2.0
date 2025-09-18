import os
import sys
import pandas as pd
from datetime import datetime
from common.dbutils import get_connection
import psycopg2
import pandas as pd

# Ensure the script can find the common directory
CURRENT_FILE = os.path.abspath(__file__)
DBMANAGER_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_ROOT = os.path.abspath(os.path.join(DBMANAGER_DIR, ".."))
COMMON_PATH = os.path.join(PROJECT_ROOT, "common")

# Ensure Python can import from common
if COMMON_PATH not in sys.path:
    sys.path.append(COMMON_PATH)
    
from common.app_logging import setup_logger
log = setup_logger("db_core", level="INFO")

    #from db import session  # or your database connection
    #from models import DailyBar, MinuteBar, TickData  # or your table definitions

def get_totals_by_symbol():
    log.info("Fetching symbol totals from daily_data, minute_data, and tick_data")  
    
    """
    Returns counts and latest timestamps per symbol from daily_data, minute_data, and tick_data.
    Uses raw SQL tailored to schema defined in init_db.py.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Daily totals and last timestamp
    cursor.execute("""
        SELECT symbol, COUNT(*) AS count, MAX(timestamp) AS last_updated
        FROM daily_data
        GROUP BY symbol
    """)
    daily = {row[0]: {"count": row[1], "last": row[2]} for row in cursor.fetchall()}
    # Ensure daily has all symbols
    if not daily:       
        log.warning("[⚠️] No daily data found")


    # Minute totals and last timestamp
    cursor.execute("""
        SELECT symbol, COUNT(*) AS count, MAX(timestamp) AS last_updated
        FROM minute_data
        GROUP BY symbol
    """)
    minute = {row[0]: {"count": row[1], "last": row[2]} for row in cursor.fetchall()}

    # Tick totals and last timestamp
    cursor.execute("""
        SELECT symbol, COUNT(*) AS count, MAX(timestamp) AS last_updated
        FROM tick_data
        GROUP BY symbol
    """)
    tick = {row[0]: {"count": row[1], "last": row[2]} for row in cursor.fetchall()}

    # Union of all symbols
    all_symbols = set(daily) | set(minute) | set(tick)

    results = []
    for sym in sorted(all_symbols):
        results.append({
            "symbol": sym,
            "daily": daily.get(sym, {}).get("count", 0),
            "daily_last": daily.get(sym, {}).get("last"),
            "minute": minute.get(sym, {}).get("count", 0),
            "minute_last": minute.get(sym, {}).get("last"),
            "tick": tick.get(sym, {}).get("count", 0),
            "tick_last": tick.get(sym, {}).get("last")
        })

    return results

# ---------- Daily Bar Logic ----------

def get_daily_bars_db(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    log.info(f"[📥] Fetching DB daily bars for {symbol} in range {start} → {end}")
    sql = """
        SELECT * FROM daily_data
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp ASC
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (symbol.upper(), start, end))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []

        df = pd.DataFrame(rows, columns=columns)
        if df.empty:
            log.warning(f"[⚠️] No DB daily bars found for fetch DB{symbol} in range {start} → {end}")
            # Return empty but well-formed DataFrame
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])

        log.info(f"[📥] !! Fetched DB !!  {len(df)} daily bars for {symbol}")
        return df

    except Exception as e:
        log.error(f"[❌] Daily DB fetch failed for {symbol}: {e}")
        return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])
    
def insert_daily_bars_db(symbol: str, df: pd.DataFrame) -> None:
    if df.empty:
        log.warning(f"[⚠️] Skipped insert: Empty daily bars for {symbol}")
        return

    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        log.error(f"[❌] Missing daily bar columns for {symbol}: {required - set(df.columns)}")
        return

    df = df.copy()
    df["symbol"] = symbol
    records = df.to_dict(orient="records")

    sql = """
        INSERT INTO daily_data (symbol, timestamp, open, high, low, close, volume)
        VALUES (%(symbol)s, %(timestamp)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
        ON CONFLICT (symbol, timestamp) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.executemany(sql, records)
            conn.commit()
            log.info(f"[🆕] Upserted {len(records)} daily bars for {symbol}")
    except Exception as e:
        log.error(f"[❌] Daily upsert failed for {symbol}: {e}")
        conn.rollback()
        
 
def insert_minute_bars_db(df: pd.DataFrame) -> None:
    if df.empty:
        log.warning(f"[⚠️] Skipped insert: Empty minute bars")
        return

    required = {"symbol", "timestamp", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        log.error(f"[❌] Missing minute bar columns: {missing}")
        return

    df = df.copy()
    records = df.to_dict(orient="records")

    sql = """
        INSERT INTO minute_data (symbol, timestamp, open, high, low, close, volume)
        VALUES (%(symbol)s, %(timestamp)s, %(open)s, %(high)s, %(low)s,
                %(close)s, %(volume)s)
        ON CONFLICT (symbol, timestamp) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.executemany(sql, records)
            conn.commit()
            log.info(f"[🧮] Upserted {len(records)} minute bars for {df['symbol'].iloc[0]}")
    except Exception as e:
        log.error(f"[❌] Minute upsert failed: {e}")
        conn.rollback()

def get_minute_bars_db(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    log.info(f"[📥] Fetching DB minute bars for {symbol} in range {start} → {end}")
    sql = """
        SELECT * FROM minute_data
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp ASC
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (symbol.upper(), start, end))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []

        df = pd.DataFrame(rows, columns=columns)
        if df.empty:
            log.warning(f"[⚠️] No DB minute bars found for {symbol} in range {start} → {end}")
            # returning empty but well-formed DataFrame
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])  
        
        log.info(f"[📥] Fetched DB {len(df)} minute bars for {symbol}")
        return df

    except Exception as e:
        log.error(f"[❌] Minute DB fetch failed for {symbol}: {e}")
        return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])  # returning empty but well-formed DataFrame

                    
# ---------- Tick Data Logic ----------
def get_ticks_db(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    log.info(f"[📥] Fetching DB tick data for {symbol} in range {start} → {end}")
    sql = """
        SELECT * FROM tick_data
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp ASC
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (symbol.upper(), start, end))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []

        df = pd.DataFrame(rows, columns=columns)
        if df.empty:
            log.warning(f"[⚠️] No DB tick data found for {symbol} in range {start} → {end}")
            return pd.DataFrame(columns=["symbol", "timestamp", "price", "size", "exchange"])

        log.info(f"[📥] Fetched DB {len(df)} ticks for {symbol}")
        return df
    except Exception as e:
        log.error(f"[❌] Tick DB fetch failed for {symbol}: {e}")
        return pd.DataFrame(columns=["symbol", "timestamp", "price", "size", "exchange"])    
             
def insert_ticks_db(symbol: str, df: pd.DataFrame) -> None:
    if df.empty:
        log.warning(f"[⚠️] Empty tick dataframe for {symbol}, skipping insert.")
        return

    required = {
        "timestamp", "sip_timestamp", "price", "size",
        "exchange", "conditions", "tape",
        "participant_id", "is_trade_through"
    }
    missing = required - set(df.columns)
    if missing:
        log.error(f"[❌] Missing required tick columns for {symbol}: {missing}")
        return

    df = df.copy()
    df["symbol"] = symbol

    # Optional: sanitize SIP format
    if not df["sip_timestamp"].apply(lambda x: isinstance(x, int)).all():
        log.warning(f"[⚠️] Non-integer SIP timestamps detected in tick data for {symbol}")
        return

    records = df.to_dict(orient="records")
    sql = """
        INSERT INTO tick_data (
            symbol, timestamp, sip_timestamp, price, size,
            exchange, conditions, tape, participant_id, is_trade_through
        )
        VALUES (
            %(symbol)s, %(timestamp)s, %(sip_timestamp)s, %(price)s, %(size)s,
            %(exchange)s, %(conditions)s, %(tape)s, %(participant_id)s, %(is_trade_through)s
        )
        ON CONFLICT (symbol, timestamp, sip_timestamp)
        DO UPDATE SET
            price = EXCLUDED.price,
            size = EXCLUDED.size,
            exchange = EXCLUDED.exchange,
            conditions = EXCLUDED.conditions,
            tape = EXCLUDED.tape,
            participant_id = EXCLUDED.participant_id,
            is_trade_through = EXCLUDED.is_trade_through
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.executemany(sql, records)
            conn.commit()
            log.info(f"[🧮] Inserted/Updated {len(records)} ticks for {symbol}")
    except Exception as e:
        log.error(f"[❌] Failed tick insert for {symbol}: {e}")
        conn.rollback()

# ---------- Fundamentals Logic ----------

def get_fundamentals_db(symbol: str) -> list[dict]:
    sql = """
        SELECT * FROM fundamental_data
        WHERE symbol = %s
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (symbol,))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

        if not rows:
            log.warning(f"[⚠️] No fundamentals found for {symbol}")
            return []

        return [dict(zip(columns, row)) for row in rows]

    except Exception as e:
        log.error(f"[❌] Fundamentals DB fetch failed for {symbol}: {e}")
        return []
    
def insert_fundamentals_db(symbol: str, fund_data: dict) -> None:
    columns = fund_data.keys()
    values = [fund_data[col] for col in columns]

    sql = f"""
        INSERT INTO fundamental_data ({', '.join(columns)})
        VALUES ({', '.join(['%s'] * len(values))})
        ON CONFLICT (symbol) DO UPDATE SET
        {', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'symbol'])}
    """

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, values)
            conn.commit()
        log.info(f"[✅] Fundamentals inserted for {symbol}")
    except Exception as e:
        log.error(f"[❌] Insert failed for {symbol}: {e}")
    """
    Insert fundamentals for a given symbol into the database.
    fund_list must match column structure.
    """
    try:
        columns = [
            "symbol", "company", "sector", "industry", "country",
            "exchange", "market_cap", "pe_ratio", "shares_float",
            "float_percent", "insider_transactions", "short_float",
            "average_true_range", "last_updated"
        ]

        if len(fund_list) != len(columns):
            raise ValueError(f"[ERROR] Expected {len(columns)} values, got {len(fund_list)} for {symbol}")

        df = pd.DataFrame([fund_list], columns=columns)

        numeric_fields = [
            "market_cap", "pe_ratio", "shares_float", "float_percent",
            "insider_transactions", "short_float", "average_true_range"
        ]
        for col in numeric_fields:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        conn = get_connection()
        with conn.cursor() as cur:
            sql = """
                INSERT INTO fundamental_data (
                    symbol, company, sector, industry, country, exchange,
                    market_cap, pe_ratio, shares_float, float_percent,
                    insider_transactions, short_float, average_true_range, last_updated
                )
                VALUES (
                    %(symbol)s, %(company)s, %(sector)s, %(industry)s, %(country)s, %(exchange)s,
                    %(market_cap)s, %(pe_ratio)s, %(shares_float)s, %(float_percent)s,
                    %(insider_transactions)s, %(short_float)s, %(average_true_range)s, %(last_updated)s
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
                    last_updated = NOW()
            """
            cur.execute(sql, df.iloc[0].to_dict())
            conn.commit()
        log.info(f"[INFO] Fundamentals inserted for {symbol} successfully")

    except Exception as e:
        log.error(f"[ERROR] insert_fundamentals_db failed for {symbol}: {e}")