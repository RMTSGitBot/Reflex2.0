import os

# ─────────────────────────────────────────────
# 🌍 Environment Context
# ─────────────────────────────────────────────

APP_ENV = os.getenv("APP_ENV", "dev").lower()
VALID_ENVS = {"dev", "prod", "staging", "test"}
if APP_ENV not in VALID_ENVS:
    print(f"🛑 Invalid APP_ENV '{APP_ENV}', defaulting to 'dev'")
    APP_ENV = "dev"

# ─────────────────────────────────────────────
# 🗄️ Database Configurations
# ─────────────────────────────────────────────

DB_CONFIG = {
    "dev": {
        "host": "localhost",
        "port": 5432,
        "dbname": "stock_data",
        "user": "postgres",
        "password": "4Asp44!",
        "connect_timeout": 5
    },
    "prod": {
        "host": "10.0.0.15",
        "port": 5432,
        "dbname": "stock_data",
        "user": "prod_user",
        "password": "securepass",
        "connect_timeout": 5
    },
    "staging": {
        "host": "192.168.1.42",
        "port": 5432,
        "dbname": "stock_data",
        "user": "stage_user",
        "password": "stagepass",
        "connect_timeout": 5
    },
    "test": {
        "host": "localhost",
        "port": 5432,
        "dbname": "test_data",
        "user": "test_user",
        "password": "testpass",
        "connect_timeout": 5
    }
}

DB_PARAMS = DB_CONFIG.get(APP_ENV, DB_CONFIG["dev"])

DB_ADMIN = {
    "dbname": "postgres",
    "user": DB_PARAMS["user"],
    "password": DB_PARAMS["password"],
    "host": DB_PARAMS["host"],
    "port": DB_PARAMS["port"]
}

# ─────────────────────────────────────────────
# 💾 MongoDB Config
# ─────────────────────────────────────────────

MONGO_DB = {
    "host": "localhost",
    "port": 27017,
    "database": "finance_operations",
    "user": "mongo_user",
    "password": "mongo_pass"
}

# ─────────────────────────────────────────────
# 🔐 API Keys
# ─────────────────────────────────────────────

API_KEYS = {
    "polygon": "QiJFJRvmCaea9OGVfp6n2IyYpnHF3qFN",
    "alpaca": "ALPACA_API_KEY_HERE",
    "ibkr": "IBKR_API_KEY_HERE",
    "webull": "WEBULL_API_KEY_HERE",
    "iex": "IEX_API_KEY_HERE"
}

# ─────────────────────────────────────────────
# 📡 Polygon API Config
# ─────────────────────────────────────────────

POLYGON_API = {
    "BASE_URL": "https://api.polygon.io",
    "API_KEY": API_KEYS["polygon"],
    "WS_URL": "wss://socket.polygon.io/stocks",
    "TIMEOUT": 10
}

# ─────────────────────────────────────────────
# 🧭 Broker Config
# ─────────────────────────────────────────────

BROKER_CONFIG = {
    "alpaca": {
        "base_url": "https://paper-api.alpaca.markets",
        "account": "sim1"
    },
    "ibkr": {
        "host": "127.0.0.1",
        "port": 7497,
        "account": "U1234567",
        "username": "ib_user",
        "password": "ib_pass"
    },
    "webull": {
        "username": "webull_user",
        "password": "webull_pass",
        "token": "WEBULL_TOKEN"
    }
}

# ─────────────────────────────────────────────
# ⏪ Replay Engine Config
# ─────────────────────────────────────────────

REPLAY_CONFIG = {
    "default_speed": 1.0,
    "history_dir": "./history",
    "output_dir": "./results"
}

# ─────────────────────────────────────────────
# 📁 DataHub Runtime Config
# ─────────────────────────────────────────────

DATAHUB_CONFIG = {
    "DATA_DIR": "./data",
    "LOG_LEVEL": "INFO",
    "ENV": "local",
    "DEFAULT_SYMBOLS": ["AAPL", "MSFT", "GOOG", "TSLA"],
    "MAX_FEED_RETRIES": 3,
    "HEARTBEAT_INTERVAL": 5  # seconds
}