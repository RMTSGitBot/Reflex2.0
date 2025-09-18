# common/common.py  
import os
import json
from .app_logging import setup_logger
import psycopg2
from config import DB_CONFIG

log = setup_logger("common")

# ─────────────────────────────────────────────
# 📁 Path Resolution
# ─────────────────────────────────────────────

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FLAGS_PATH = os.path.join(ROOT_DIR, "common", "lifecycle_flags.json")

# ─────────────────────────────────────────────
# 📦 Metadata Loaders
# ─────────────────────────────────────────────

def load_symbols_from_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM ticks")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def load_lifecycle_flags(path=FLAGS_PATH):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"[❌] Failed to load lifecycle_flags.json: {e}")
        return {}

CONFIG_PATH = os.path.join(ROOT_DIR, "common", "config.json")

def load_json_config(path=CONFIG_PATH):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"[❌] Failed to load config.json: {e}")
        return {}
    