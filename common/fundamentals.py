# common/fundamentals.py
import psycopg2
from psycopg2 import sql, errors
from common.config import DB_CONFIG

def get_fundamentals(symbol):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("""
            SELECT market_cap, pe_ratio, exchange, sector
            FROM fundamentals
            WHERE symbol = %s
            LIMIT 1
        """, (symbol,))
        row = cur.fetchone()
        conn.close()

        if not row:
            print(f"[⚠️] No fundamentals found for {symbol}")
            return {}

        return {
            "market_cap": row[0],
            "pe_ratio": row[1],
            "exchange": row[2],
            "sector": row[3]
        }

    except errors.UndefinedTable:
        print(f"[⚠️] Table 'fundamentals' does not exist—skipping {symbol}")
        return {}

    except Exception as e:
        print(f"[⚠️] Fundamentals fetch error for {symbol}: {e}")
        return {}