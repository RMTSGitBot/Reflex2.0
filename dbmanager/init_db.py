# dbmanager/init_db.py

import os
import sys

CURRENT_FILE = os.path.abspath(__file__)
DBMANAGER_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_ROOT = os.path.abspath(os.path.join(DBMANAGER_DIR, ".."))
COMMON_PATH = os.path.join(PROJECT_ROOT, "common")

if COMMON_PATH not in sys.path:
    sys.path.append(COMMON_PATH)
from common.dbutils import get_connection, execute_sql_commands
from common.app_logging import setup_logger
from common.config import DB_PARAMS

log = setup_logger("dbmanager-init", level="INFO")

try:
    import psycopg2
except ImportError:
    import subprocess
    import sys
    log.info("psycopg2 not found. Installing it...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2"])
    import psycopg2

SQL_STATEMENTS = [
    """CREATE EXTENSION IF NOT EXISTS timescaledb;""",

    # tick_data
    """
    DROP TABLE IF EXISTS tick_data CASCADE;
    CREATE TABLE tick_data (
        symbol TEXT NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        sip_timestamp BIGINT NOT NULL,
        price NUMERIC(18, 6) NOT NULL,
        size INTEGER,
        exchange TEXT,
        conditions TEXT[],
        tape TEXT,
        participant_id TEXT,
        is_trade_through BOOLEAN DEFAULT FALSE,
        UNIQUE (symbol, timestamp, sip_timestamp)
    );
    SELECT create_hypertable('tick_data', 'timestamp', chunk_time_interval => interval '1 day', if_not_exists => TRUE);
    CREATE INDEX IF NOT EXISTS idx_tick_conflict ON tick_data (symbol, timestamp, sip_timestamp);
    """,

    # quote_data
    """
    DROP TABLE IF EXISTS quote_data CASCADE;
    CREATE TABLE quote_data (
        symbol TEXT NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        bid_price NUMERIC(18,6),
        bid_size INTEGER,
        ask_price NUMERIC(18,6),
        ask_size INTEGER,
        exchange TEXT,
        tape TEXT,
        PRIMARY KEY (symbol, timestamp)
    );
    SELECT create_hypertable('quote_data', 'timestamp', chunk_time_interval => interval '1 day', if_not_exists => TRUE);
    """,

    # trade_triggers
    """
    DROP TABLE IF EXISTS trade_triggers CASCADE;
    CREATE TABLE trade_triggers (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        trigger_type TEXT,
        timestamp TIMESTAMPTZ NOT NULL,
        metadata JSONB
    );
    """,

    # minute_bar_audit
    """
    DROP TABLE IF EXISTS minute_bar_audit CASCADE;
    CREATE TABLE minute_bar_audit (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        ingested_volume BIGINT,
        expected_volume BIGINT,
        integrity_passed BOOLEAN
    );
    """,

    # minute_bars
    """
    DROP TABLE IF EXISTS minute_bars CASCADE;
    CREATE TABLE minute_bars (
        symbol TEXT NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        open NUMERIC(18, 6),
        high NUMERIC(18, 6),
        low NUMERIC(18, 6),
        close NUMERIC(18, 6),
        volume BIGINT,
        PRIMARY KEY (symbol, timestamp)
    );
    SELECT create_hypertable('minute_bars', 'timestamp', chunk_time_interval => interval '1 day', if_not_exists => TRUE);
    """,

    # daily_bars
    """
    DROP TABLE IF EXISTS daily_bars CASCADE;
    CREATE TABLE daily_bars (
        symbol TEXT NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        open NUMERIC(18, 6),
        high NUMERIC(18, 6),
        low NUMERIC(18, 6),
        close NUMERIC(18, 6),
        volume BIGINT,
        PRIMARY KEY (symbol, timestamp)
    );
    SELECT create_hypertable('daily_bars', 'timestamp', chunk_time_interval => interval '7 days', if_not_exists => TRUE);
    """,

    # fundamental_data
    """
    DROP TABLE IF EXISTS fundamental_data CASCADE;
    CREATE TABLE fundamental_data (
        symbol TEXT PRIMARY KEY,
        company TEXT,
        sector TEXT,
        industry TEXT,
        country TEXT,
        exchange TEXT,
        market_cap NUMERIC(18, 2),
        pe_ratio NUMERIC(10, 2),
        shares_float BIGINT,
        float_percent NUMERIC(10, 2),
        insider_transactions NUMERIC(10, 2),
        short_float NUMERIC(10, 2),
        average_true_range NUMERIC(10, 4),
        last_updated TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_fundamental_symbol ON fundamental_data (symbol);
    CREATE INDEX IF NOT EXISTS idx_sector ON fundamental_data (sector);
    CREATE INDEX IF NOT EXISTS idx_industry ON fundamental_data (industry);
    CREATE INDEX IF NOT EXISTS idx_country ON fundamental_data (country);
    CREATE INDEX IF NOT EXISTS idx_exchange ON fundamental_data (exchange);
    CREATE INDEX IF NOT EXISTS idx_market_cap ON fundamental_data (market_cap);
    CREATE INDEX IF NOT EXISTS idx_pe_ratio ON fundamental_data (pe_ratio);
    CREATE INDEX IF NOT EXISTS idx_shares_float ON fundamental_data (shares_float);
    CREATE INDEX IF NOT EXISTS idx_float_percent ON fundamental_data (float_percent);
    """,

    # materialized views
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS agg_5m_bars WITH (timescaledb.continuous) AS
    SELECT
        symbol,
        time_bucket('5 minutes', timestamp) AS bucket,
        first(open, timestamp)::NUMERIC(18, 6) AS open,
        max(high)::NUMERIC(18, 6) AS high,
        min(low)::NUMERIC(18, 6) AS low,
        last(close, timestamp)::NUMERIC(18, 6) AS close,
        sum(volume) AS volume
    FROM minute_bars
    GROUP BY symbol, bucket
    WITH NO DATA;
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS agg_15m_bars WITH (timescaledb.continuous) AS
    SELECT
        symbol,
        time_bucket('15 minutes', timestamp) AS bucket,
        first(open, timestamp)::NUMERIC(18, 6) AS open,
        max(high)::NUMERIC(18, 6) AS high,
        min(low)::NUMERIC(18, 6) AS low,
        last(close, timestamp)::NUMERIC(18, 6) AS close,
        sum(volume) AS volume
    FROM minute_bars
    GROUP BY symbol, bucket
    WITH NO DATA;
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS agg_1h_bars WITH (timescaledb.continuous) AS
    SELECT
        symbol,
        time_bucket('1 hour', timestamp) AS bucket,
        first(open, timestamp)::NUMERIC(18, 6) AS open,
        max(high)::NUMERIC(18, 6) AS high,
        min(low)::NUMERIC(18, 6) AS low,
        last(close, timestamp)::NUMERIC(18, 6) AS close,
        sum(volume) AS volume
    FROM minute_bars
    GROUP BY symbol, bucket
    WITH NO DATA;
    """,
    """
    CREATE MATERIALIZED VIEW IF NOT EXISTS agg_1d_bars WITH (timescaledb.continuous) AS
    SELECT
        symbol,
        time_bucket('1 day', timestamp) AS bucket,
        first(open, timestamp)::NUMERIC(18, 6) AS open,
        max(high)::NUMERIC(18, 6) AS high,
        min(low)::NUMERIC(18, 6) AS low,
        last(close, timestamp)::NUMERIC(18, 6) AS close,
        sum(volume) AS volume
    FROM minute_bars
    GROUP BY symbol, bucket
    WITH NO DATA;
    """,

    # symbol_metadata (with filters)
    """
    DROP TABLE IF EXISTS symbol_metadata CASCADE;
    CREATE TABLE symbol_metadata (
        symbol VARCHAR PRIMARY KEY,
        mode VARCHAR NOT NULL,
        filters TEXT[] DEFAULT ARRAY[]::TEXT[],
        last_updated TIMESTAMP DEFAULT NOW()
    );
    """,

    # ingest_sessions
    """
    DROP TABLE IF EXISTS ingest_sessions CASCADE;
    CREATE TABLE ingest_sessions (
        session_id UUID PRIMARY KEY,
        start_time TIMESTAMPTZ NOT NULL,
        source TEXT,
        notes TEXT
    );
    """,

    # evaluator_flags
    """
    DROP TABLE IF EXISTS evaluator_flags CASCADE;
    CREATE TABLE evaluator_flags (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        flag_type TEXT,
        confidence NUMERIC(5,2),
        metadata JSONB
    );
    """,
    """
    CREATE VIEW symbol_profile_view AS
    SELECT
        f.symbol,
        f.company,
        f.sector,
        f.industry,
        f.country,
        f.exchange,
        f.market_cap,
        f.shares_float,
        f.float_percent,
        f.pe_ratio,
        f.average_true_range,
        f.last_updated AS fundamentals_updated,

        m.mode,
        m.filters,
        m.last_updated AS metadata_updated,

        ef.flag_type,
        ef.confidence,
        ef.metadata,
        ef.timestamp AS flag_timestamp

    FROM fundamental_data f

    LEFT JOIN symbol_metadata m ON f.symbol = m.symbol

    LEFT JOIN (
        SELECT DISTINCT ON (symbol, flag_type)
            symbol,
            flag_type,
            confidence,
            metadata,
            timestamp
        FROM evaluator_flags
        WHERE flag_type IN ('do_not_trade', 'manual_exclude', 'ipo_recent')
        ORDER BY symbol, flag_type, timestamp DESC
    ) ef ON f.symbol = ef.symbol;
    """
]

def drop_and_create_database():
    dbname = DB_PARAMS["dbname"]
    admin_conn = psycopg2.connect(
        dbname="postgres",  # connect to system DB
        user=DB_PARAMS["user"],
        password=DB_PARAMS["password"],
        host=DB_PARAMS["host"],
        port=DB_PARAMS["port"]
    )
    admin_conn.autocommit = True
    admin_cur = admin_conn.cursor()

    # Check if DB exists
    admin_cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
    exists = admin_cur.fetchone()

    if exists:
        log.info(f"🧨 Dropping existing database '{dbname}'...")
        admin_cur.execute(f"DROP DATABASE {dbname};")

    log.info(f"🧱 Creating new database '{dbname}'...")
    admin_cur.execute(f"CREATE DATABASE {dbname};")

    admin_cur.close()
    admin_conn.close()

    # Now connect to the new DB and run schema setup
    log.info(f"⚙️ Connecting to '{dbname}' to initialize schema...")
    conn = psycopg2.connect(
        dbname=dbname,
        user=DB_PARAMS["user"],
        password=DB_PARAMS["password"],
        host=DB_PARAMS["host"],
        port=DB_PARAMS["port"]
    )
    execute_sql_commands(SQL_STATEMENTS, conn, logger=log)
    conn.close()

    log.info(f"✅ Database '{dbname}' initialized successfully.")
