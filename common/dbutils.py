# common/dbutils.py
 
import os
import sys
import subprocess
import pytz
from datetime import datetime, time, timezone
from typing import Union, Optional

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Resilient Import Utility ---
def ensure_package(module_name: str, pip_name: Optional[str] = None):
    try:
        return __import__(module_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name or module_name])
        return __import__(module_name)

def ensure_submodule(module_name: str, submodule: str, pip_name: Optional[str] = None):
    try:
        return __import__(module_name, fromlist=[submodule])
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name or module_name])
        return __import__(module_name, fromlist=[submodule])

# --- Third-Party Imports ---
pd = ensure_package("pandas")
psycopg2 = ensure_package("psycopg2")
psycopg2_extras = ensure_submodule("psycopg2.extras", "DictCursor", "psycopg2-binary")
connect = getattr(psycopg2, "connect")
MongoClient = getattr(ensure_package("pymongo"), "MongoClient")
parse = getattr(ensure_submodule("dateutil.parser", "parse", "python-dateutil"), "parse")

# --- Internal Modules ---
from common.config import DB_PARAMS, APP_ENV, DB_ADMIN, MONGO_DB, TIMESCALE_DB
from common.app_logging import setup_logger
from common.utils import normalize_datetime

from contextlib import contextmanager

# --- Constants ---
EASTERN = pytz.timezone("US/Eastern")

# --- Logger ---
log = setup_logger("dbutils", level="INFO")


def exec_sql_query(conn, sql: str, logger=None) -> list[dict]:
    try:
        with conn.cursor(cursor_factory=psycopg2_extras.DictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            if logger:
                logger.info(f"[📥] Retrieved {len(rows)} rows from query.")
            return [dict(row) for row in rows]
    except Exception as e:
        if logger:
            logger.error(f"[❌] Query failed: {e}")
        return []
    
def execute_sql_commands(sql_list: list[str], conn, logger=None):
    """
    Executes a list of SQL statements using the provided connection.
    Logs each statement's first line and handles errors gracefully.

    Args:
        sql_list (list[str]): List of SQL strings to execute.
        conn (psycopg2 connection): Active DB connection.
        logger (logging.Logger, optional): Logger instance. Defaults to None.
    """
    conn.autocommit = True
    with conn.cursor() as cur:
        for sql in sql_list:
            preview = sql.strip().splitlines()[0] if sql.strip() else "[Empty SQL]"
            try:
                cur.execute(sql)
                msg = f"✅ Executed: {preview}"
            except Exception as e:
                msg = f"[❌] Failed: {preview}\n{e}"
            finally:
                if logger:
                    logger.info(msg) if "✅" in msg else logger.error(msg)
                else:
                    print(msg)
def get_db_params():
    """Returns the database connection parameters from common.config."""
    return {
        "dbname": DB_PARAMS.get("dbname", "default_db"),
        "user": DB_PARAMS.get("user", "default_user"),
        "password": DB_PARAMS.get("password", "default_password"),
        "host": DB_PARAMS.get("host", "localhost"),
        "port": DB_PARAMS.get("port", 5432),

    }
        
def get_connection(set_schema=False):
    log.info(f"🔍 Get connection")
    try:
        params = dict(DB_PARAMS)  # Safe copy
        schema = params.pop("schema", "public")  # Remove before connect
        clean_params = strip_invalid_keys(params)  # Final clean dict
        conn = connect(**clean_params)
        log.info(f"🔍 Connection params: {clean_params}")
        
        if set_schema:
            conn.set_session(autocommit=True)
            with conn.cursor() as cur:
                cur.execute(f"SET search_path TO {schema};")
        log.info(f"✅ Connected to DB '{DB_PARAMS['dbname']}' [{APP_ENV}] at {DB_PARAMS['host']}:{DB_PARAMS['port']}")
        return conn
    except Exception as e:
        log.error(f"[ERROR] Connection to '{DB_PARAMS['dbname']}' failed: {e}")
        raise

def get_admin_connection():
    
    """Get a connection to the admin database (usually 'postgres')."""
    if not DB_ADMIN:
        log.error("🛑 No DB_ADMIN configuration found. Cannot connect to admin database.")
        raise ValueError("DB_ADMIN configuration is missing or incomplete.")
    log.info(f"🔍 Admin connect")
    if not DB_ADMIN.get("dbname"):
        log.error("🛑 No 'dbname' specified in DB_ADMIN configuration. Cannot connect to admin database.")
        raise ValueError("DB_ADMIN 'dbname' is required for admin connection.")
    if not DB_ADMIN.get("user"):
        log.error("🛑 No 'user' specified in DB_ADMIN configuration. Cannot connect to admin database.")
        raise ValueError("DB_ADMIN 'user' is required for admin connection.")
    if not DB_ADMIN.get("host"):
        log.error("🛑 No 'host' specified in DB_ADMIN configuration. Cannot connect to admin database.")
        raise ValueError("DB_ADMIN 'host' is required for admin connection.")
    if not DB_ADMIN.get("port"):
        log.error("🛑 No 'port' specified in DB_ADMIN configuration. Cannot connect to admin database.")
        raise ValueError("DB_ADMIN 'port' is required for admin connection.")
    if not DB_ADMIN.get("password"):
        log.error("🛑 No 'password' specified in DB_ADMIN configuration. Cannot connect to admin database.")
        raise ValueError("DB_ADMIN 'password' is required for admin connection.")
    if not DB_ADMIN.get("sslmode"):
        log.warning("⚠️ No 'sslmode' specified in DB_ADMIN configuration. Defaulting to 'prefer'.")
        DB_ADMIN["sslmode"] = "prefer"
        
    clean_params = strip_invalid_keys(DB_ADMIN)
    log.info(f"🔍 Admin connect params: {clean_params}")

    try:
        if "dbname" not in clean_params:
            clean_params["dbname"] = "postgres" # Default admin DB  
        if "sslmode" not in clean_params:
            clean_params["sslmode"] = "prefer"
        if "port" not in clean_params:
            clean_params["port"] = 5432
        if "host" not in clean_params:
            clean_params["host"] = "localhost"
        if "user" not in clean_params:
            clean_params["user"] = "postgres"
        if "password" not in clean_params:
            clean_params["password"] = "4Asp44!"
        if "schema" in clean_params:
            del clean_params["schema"]
        log.debug(f"🔑 Admin connect params: {clean_params}")
        
        # Connect to the admin database (usually 'postgres')
        log.info(f"🔑 Admin connecting to 'postgres' [{APP_ENV}] at {DB_ADMIN['host']}:{DB_ADMIN['port']}")
        
        conn = connect(**clean_params)
        log.info(f"🔑 Admin connected to 'postgres' [{APP_ENV}] at {DB_ADMIN['host']}:{DB_ADMIN['port']}")
        return conn
    except Exception as e:
        log.error(f"[ERROR] Admin connection failed: {e}")
        raise

# MongoDB Connection
def connect_mongo():
    client = MongoClient(
        host=MONGO_DB["HOST"],
        port=MONGO_DB["PORT"],
        username=MONGO_DB["USER"],
        password=MONGO_DB["PASSWORD"],
    )
    return client[MONGO_DB["DATABASE"]]

# TimescaleDB Connection
def connect_timescale():
    conn = psycopg2.connect(
        host=TIMESCALE_DB["HOST"],
        port=TIMESCALE_DB["PORT"],
        dbname=TIMESCALE_DB["DATABASE"],
        user=TIMESCALE_DB["USER"],
        password=TIMESCALE_DB["PASSWORD"],
    )
    return conn

def strip_invalid_keys(params):
    valid_keys = {"dbname", "user", "password", "host", "port"}
    return {k: v for k, v in params.items() if k in valid_keys}

@contextmanager
def with_connection(set_schema=False):
    conn = get_connection(set_schema=set_schema)
    try:
        yield conn
    finally:
        conn.close()
        
db_manifest = {
    "primary": {
        "name": DB_PARAMS.get("dbname"),
        "purpose": "Real-time trading and historical analysis",
        "schema": DB_PARAMS.get("schema", "public"),
    },
    "admin": {
        "name": DB_ADMIN.get("dbname", "postgres"),
        "purpose": "DDL, migrations, and system-level operations",
    },
    "mongo": {
        "name": MONGO_DB.get("DATABASE"),
        "purpose": "Unstructured logs, audit trails, and metadata",
    },
    "timescale": {
        "name": TIMESCALE_DB.get("DATABASE"),
        "purpose": "High-resolution time-series data",
    },
}

def test_connection():
    try:
        conn = get_connection()
        conn.close()
        log.info("✅ DB connection test passed.")
        return True
    except Exception as e:
        log.error(f"🛑 DB connection test failed: {e}")
        return False
    