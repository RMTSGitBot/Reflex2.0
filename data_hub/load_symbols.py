# data_hub/load_symbols.py
from common.dbutils import get_db_connection

def load_symbols_from_db(exclude_flag="do_not_trade"):
    """
    Load all symbols from DB that are eligible for trading.
    Skips any with the exclude_flag set to true.
    Returns a list of uppercase symbol strings.
    """
    symbols = []
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            query = f"""
                SELECT symbol
                FROM symbols
                WHERE COALESCE({exclude_flag}, false) = false
            """
            cur.execute(query)
            rows = cur.fetchall()
            symbols = [row[0].upper() for row in rows]
    finally:
        conn.close()

    return symbols