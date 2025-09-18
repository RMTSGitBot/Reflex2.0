# dbmanager/schema.py
def get_schema(conn, table="symbol_profile_view"):
    cur = conn.cursor()
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s;
    """, (table,))
    return cur.fetchall()