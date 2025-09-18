# data_hub/load_models.py
import json
import os
from shared_mem.registry import registry
from common.dbutils import get_db_connection

def load_models_for_symbols(symbols, default_model):
    """
    Loads model configs for each symbol from DB.
    If none assigned, loads the default model JSON from disk.
    """
    default_model_path = os.path.join("models", default_model)
    with open(default_model_path, "r") as f:
        default_model_json = json.load(f)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for sym in symbols:
                cur.execute(
                    "SELECT model_json FROM symbol_models WHERE symbol = %s",
                    (sym,)
                )
                row = cur.fetchone()
                if row and row[0]:
                    try:
                        model_config = json.loads(row[0])
                    except json.JSONDecodeError:
                        print(f"[⚠️] Invalid model JSON for {sym}, using default.")
                        model_config = default_model_json
                else:
                    model_config = default_model_json

                registry[sym]["model"] = model_config
    finally:
        conn.close()