# dbmanager/symbol_editor.py
def set_symbol_status(db, symbol, status):
    cur = db.cursor()
    cur.execute("""
        UPDATE symbol_metadata SET mode = %s, last_updated = NOW()
        WHERE symbol = %s;
    """, (status, symbol))
    cur.close()

def set_flag(db, symbol, flag, value):
    cur = db.cursor()
    cur.execute("""
        INSERT INTO evaluator_flags (symbol, flag_type, confidence, metadata, timestamp)
        VALUES (%s, %s, %s, %s, NOW());
    """, (symbol, flag, value, {}))
    cur.close()