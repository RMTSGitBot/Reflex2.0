# === Path Setup ===
import sys
import os

# Ensure required packages are installed
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    import psycopg2.extras

try:
    from flask import g, Flask, render_template, request, redirect, url_for
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Flask"])
    from flask import g, Flask, render_template, request, redirect, url_for

CURRENT_FILE = os.path.abspath(__file__)
DBMANAGER_DIR = os.path.dirname(CURRENT_FILE)
PROJECT_ROOT = os.path.abspath(os.path.join(DBMANAGER_DIR, ".."))
COMMON_PATH = os.path.join(PROJECT_ROOT, "common")

if COMMON_PATH not in sys.path:
    sys.path.append(COMMON_PATH)

from common.app_logging import setup_logger
from common.config import DB_PARAMS, APP_ENV, LOG_LEVEL
from common.dbutils import get_connection
from .db_backfill import run_backfill
from .finviz_adapter import fetch_finviz_fundamentals, map_and_upsert
from .symbol_editor import set_symbol_status, set_flag
from .init_db import drop_and_create_database

app = Flask(__name__)
log = setup_logger("dbmanager - app", level=LOG_LEVEL)

def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(
            dbname=DB_PARAMS["dbname"],
            user=DB_PARAMS["user"],
            password=DB_PARAMS["password"],
            host=DB_PARAMS["host"],
            port=DB_PARAMS["port"],
            cursor_factory=psycopg2.extras.DictCursor
        )
    return g.db

@app.teardown_appcontext
def teardown_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# ─────────────────────────────────────────────
# 🏠 Status: DB Pulse
# ─────────────────────────────────────────────
@app.route("/")
def index():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cur.execute("SELECT COUNT(*) FROM symbol_metadata;")
            symbol_count = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) FROM symbol_profile_view;")
            profile_count = cur.fetchone()["count"]

            cur.execute("SELECT pg_database_size(current_database());")
            db_size_bytes = cur.fetchone()["pg_database_size"]
            db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

            db_status = "✅ Connected"
            init_required = False

        except psycopg2.errors.UndefinedTable:
            symbol_count = profile_count = db_size_mb = 0
            db_status = "⚠️ No tables found"
            init_required = True

        except Exception as e:
            symbol_count = profile_count = db_size_mb = 0
            db_status = f"❌ Connection failed: {str(e)}"
            init_required = True

        cur.close()
        conn.close()

    except Exception as e:
        symbol_count = profile_count = db_size_mb = 0
        db_status = f"❌ DB unreachable: {str(e)}"
        init_required = True

    return render_template("dashboard.html",
        app_env=APP_ENV,
        db_params=DB_PARAMS,
        db_status=db_status,
        symbol_count=symbol_count,
        profile_count=profile_count,
        db_size_mb=db_size_mb,
        init_required=init_required
    )

# ─────────────────────────────────────────────
# 🧬 Symbol Editor
# ─────────────────────────────────────────────
@app.route("/symbol_editor", methods=["GET", "POST"])
def symbol_editor():
    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        mode = request.form["mode"]
        filters = request.form.get("filters", "").split(",")
        filters = [f.strip() for f in filters if f.strip()]
        cur.execute("""
            INSERT INTO symbol_metadata (symbol, mode, filters, last_updated)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (symbol) DO UPDATE
            SET mode = EXCLUDED.mode,
                filters = EXCLUDED.filters,
                last_updated = NOW();
        """, (symbol, mode, filters))
        conn.commit()

    cur.execute("SELECT symbol, mode, filters, last_updated FROM symbol_metadata ORDER BY symbol;")
    rows = cur.fetchall()
    conn.close()
    return render_template("symbol_editor.html", rows=rows)

# ─────────────────────────────────────────────
# 📋 Finviz Hydration
# ─────────────────────────────────────────────
@app.route("/symbol_list")
def symbol_list():
    df = fetch_finviz_fundamentals()
    map_and_upsert(df, "COLD")
    return redirect(url_for("index"))

# ─────────────────────────────────────────────
# 🗄️ Polygon S3 Loader (Stub)
# ─────────────────────────────────────────────
@app.route("/poly_s3")
def poly_s3():
    return render_template("poly_s3.html", message="🗄️ Polygon S3 loader not yet implemented.")

# ─────────────────────────────────────────────
# 📦 Backfill Loader
# ─────────────────────────────────────────────
@app.route("/backfill", methods=["GET", "POST"])
def backfill():
    if request.method == "GET":
        return render_template("backfill.html")

    mode = request.form.get("mode", "recent").lower()
    target = request.form.get("target", "single")
    symbols_raw = request.form.get("symbols", "")
    symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]

    if target == "all":
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM symbol_metadata WHERE mode != 'NOT';")
        symbols = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()

    if not symbols:
        return render_template("backfill.html", message="⚠️ No symbols provided.")

    try:
        run_backfill(symbols, mode)
        msg = f"✅ Backfill complete for {len(symbols)} symbols in '{mode}' mode"
        return render_template("backfill.html", message=msg)
    except Exception as e:
        return render_template("backfill.html", message=f"❌ Backfill failed: {str(e)}")

# ─────────────────────────────────────────────
# 🧨 Reset: Init (Danger Zone)
# ─────────────────────────────────────────────
@app.route("/init")
def init_db_route():
    confirm = request.args.get("confirm", "").upper()
    if confirm != "YES":
        return render_template("init_confirm.html", message="🧨 Init requires confirmation. Append ?confirm=YES to proceed.")
    
    drop_and_create_database()
    return redirect(url_for("index"))

# ─────────────────────────────────────────────
# ❤️ Health: Heartbeat
# ─────────────────────────────────────────────
@app.route("/health")
def health():
    return {"status": "ok", "env": APP_ENV, "db": DB_PARAMS["dbname"]}

# ─────────────────────────────────────────────
# 🔁 Symbol Detail + Edit
# ─────────────────────────────────────────────
@app.route("/symbol/<ticker>")
def symbol(ticker):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM symbol_profile_view WHERE symbol = %s;", (ticker,))
    row = cur.fetchone()
    return render_template("symbol.html", symbol=row)

@app.route("/logs")
def logs():
    log_path = os.path.join(PROJECT_ROOT, "logs", "dbmanager.log")
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()[-100:]
    except Exception as e:
        lines = [f"❌ Failed to read log: {e}"]

    return render_template("logs.html", lines=lines)

# ─────────────────────────────────────────────
# 🚀 Launch
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Launching Reflexion DBManager in '{APP_ENV}' mode [log level: {LOG_LEVEL}]")
    app.run(host="0.0.0.0", port=5000, debug=(APP_ENV == "dev"))