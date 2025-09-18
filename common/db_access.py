import pandas as pd
from datetime import datetime
from common.dbutils import get_connection
from common.app_logging import setup_logger

log = setup_logger("db_access", level="INFO")

# ---------- Symbol Totals ----------

def get_totals_by_symbol():
    log.info("📊 Fetching symbol totals from daily_data, minute_data, and tick_data")
    conn = get_connection()
    cur = conn.cursor()

    def fetch_totals(table):
        cur.execute(f"""
            SELECT symbol, COUNT(*) AS count, MAX(timestamp) AS last_updated
            FROM {table}
            GROUP BY symbol
        """)
        return {row[0]: {"count": row[1], "last": row[2]} for row in cur.fetchall()}

    daily = fetch_totals("daily_data")
    minute = fetch_totals("minute_data")
    tick = fetch_totals("tick_data")

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
    symbol = symbol.upper()
    log.info(f"[📥] Fetching daily bars for {symbol} from {start} to {end}")
    sql = """
        SELECT * FROM daily_data
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp ASC
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (symbol, start, end))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []

        df = pd.DataFrame(rows, columns=columns)
        if df.empty:
            log.warning(f"[⚠️] No daily bars found for {symbol} in range {start} → {end}")
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])

        log.info(f"[📥] Fetched {len(df)} daily bars for {symbol}")
        return df

    except Exception as e:
        log.error(f"[❌] Daily fetch failed for {symbol}: {e}")
        return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])

def insert_daily_bars_db(symbol: str, df: pd.DataFrame) -> None:
    symbol = symbol.upper()
    if df.empty:
        log.warning(f"[⚠️] Skipped insert: Empty daily bars for {symbol}")
        return

    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        log.error(f"[❌] Missing columns for {symbol}: {required - set(df.columns)}")
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

# ---------- Minute Bar Logic ----------

def get_minute_bars_db(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    symbol = symbol.upper()
    log.info(f"[📥] Fetching minute bars for {symbol} from {start} to {end}")
    sql = """
        SELECT * FROM minute_data
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp ASC
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (symbol, start, end))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []

        df = pd.DataFrame(rows, columns=columns)
        if df.empty:
            log.warning(f"[⚠️] No minute bars found for {symbol} in range {start} → {end}")
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])

        log.info(f"[📥] Fetched {len(df)} minute bars for {symbol}")
        return df

    except Exception as e:
        log.error(f"[❌] Minute fetch failed for {symbol}: {e}")
        return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])

def insert_minute_bars_db(df: pd.DataFrame) -> None:
    if df.empty:
        log.warning("[⚠️] Skipped insert: Empty minute bars")
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
            log.info(f"[🧮] Upserted {len(records)} minute bars for {df['symbol'].iloc[0]}")
    except Exception as e:
        log.error(f"[❌] Minute upsert failed: {e}")
        conn.rollback()

# ---------- Tick Data Logic ----------

def get_ticks_db(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    symbol = symbol.upper()
    log.info(f"[📥] Fetching tick data for {symbol} from {start} to {end}")
    sql = """
        SELECT * FROM tick_data
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp ASC
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, (symbol, start, end))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []

        df = pd.DataFrame(rows, columns=columns)
        if df.empty:
            log.warning(f"[⚠️] No tick data found for {symbol} in range {start} → {end}")
            return pd.DataFrame(columns=["symbol", "timestamp", "price", "size", "exchange"])

        log.info(f"[📥] Fetched {len(df)} ticks for {symbol}")
        return df

    except Exception as e:
        log.error(f"[❌] Tick fetch failed for {symbol}: {e}")
        return pd.DataFrame(columns=["symbol", "timestamp", "price", "size", "exchange"])
def insert_ticks_db(symbol: str, df: pd.DataFrame) -> None:
    symbol = symbol.upper()
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
        log.error(f"[❌] Missing tick columns for {symbol}: {missing}")
        return

    df = df.copy()
    df["symbol"] = symbol

    if not df["sip_timestamp"].apply(lambda x: isinstance(x, int)).all():
        log.warning(f"[⚠️] Non-integer SIP timestamps detected for {symbol}, skipping insert.")
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
            log.info(f"[🧮] Upserted {len(records)} ticks for {symbol}")
    except Exception as e:
        log.error(f"[❌] Tick upsert failed for {symbol}: {e}")
        conn.rollback()

# ---------- Fundamentals Logic ----------

def get_fundamentals_db(symbol: str) -> list[dict]:
    symbol = symbol.upper()
    log.info(f"[📥] Fetching fundamentals for {symbol}")
    sql = "SELECT * FROM fundamental_data WHERE symbol = %s"
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
        log.error(f"[❌] Fundamentals fetch failed for {symbol}: {e}")
        return []

def insert_fundamentals_db(symbol: str, fund_data: dict) -> None:
    symbol = symbol.upper()
    if not fund_data:
        log.warning(f"[⚠️] Empty fundamentals for {symbol}, skipping insert.")
        return

    fund_data = fund_data.copy()
    fund_data["symbol"] = symbol

    columns = fund_data.keys()
    placeholders = ", ".join([f"%({col})s" for col in columns])
    updates = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns if col != "symbol"])

    sql = f"""
        INSERT INTO fundamental_data ({', '.join(columns)})
        VALUES ({placeholders})
        ON CONFLICT (symbol) DO UPDATE SET
        {updates}
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, fund_data)
            conn.commit()
            log.info(f"[🧠] Upserted fundamentals for {symbol}")
    except Exception as e:
        log.error(f"[❌] Fundamentals insert failed for {symbol}: {e}")
        conn.rollback()