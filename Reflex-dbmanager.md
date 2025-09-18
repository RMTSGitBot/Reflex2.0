
Reflex v1.16 dbmanager notes 

✅ Summary of Key Design Commitments
🧱 Database Initialization
init_db.py will:
Drop and rebuild the database cleanly.
Include a safety latch to prevent accidental deletion.
Be wrapped in a Flask interface for controlled access.
📦 Data Ingestion
S3 download + Polygon update pipeline.
Download requestor module for Polygon REST and WebSocket.
Finviz ingestor to prime the symbol list.
🔄 Symbol Lifecycle
All new symbols start as Cold.
Symbol states: Cold → Watch → Warm → Hot.
Managed via symbol editor, which also supports:
Editing flags (e.g., do_not_trade, manual_exclude) in a variable list.
🧪 Dashboard / Front Door
Displays basic DB stats (nerd-level).
Must not crash if DB is missing or corrupt.
Supports multiple environments:
Dev, Production, and future offsite co-lo.

✅ Current Assumptions for init_db.py Execution


Hypertables: tick, quote, minute, daily — created fresh with time-series indexing.
Materialized Views: Aggregations for 5/15/60 min bars.
Metadata Tables: Symbol settings, flags (cold, watch, warm, hot, do_not_trade), and lifecycle states.
Fundamentals Table: Created during fundamentals update from Polygon.
No legacy tracking tables unless explicitly reintroduced.
Schema rebuild includes full index setup and aggregation logic.
Symbol editor will manage flags and variable lists from scratch.


The full architecture and purpose of dbmanager as a standalone Flask tool.
Its integration with the common directory modules.
The safety-latched init_db.py, symbol editor with state/flag management, S3 reader, Finviz ingestor, dashboard, and fundamentals updater.

Primary focus: Production-grade deployment starting with the dbmanager module.
Environment: High-end 96GB machine, Flask-based standalone tool.
Core modules: Uses foundational tools from the common directory—common.py, config.py, dbcore.py, dbutils.py, poly_tools.py.

🧰 dbmanager Capabilities
Full DB reset and schema rebuild with indexes and aggregations.
Historical backfill:
1 year of daily bars
3 days of minute bars with 5/15/60 min aggregations
1 day of tick data
Fundamentals update from Polygon.
Front door dashboard:
DB status
Fail-safe display (stable even if DB is missing or corrupt)
S3 reader for Polygon data with download requestor.
Symbol editor:
States: cold, watch, warm, hot
Flags: do_not_trade, variable list support
All new symbols start as cold
Finviz ingestor primes the symbol list.
Safety latch for DB reset via init_db.py.
No stubs—all modules wired up for full functionality.
Logging and status runner for large operations.
Multi-environment support: dev, production, and offsite co-lo.

start_dbmanager.bat – Launches the Flask dashboard
init_database.bat – Triggers the DB reset

precalc is not long part of dbmanager

📊 Core Hypertables
tick_data
quote_data
minute_bars
daily_bars
📈 Materialized Views
agg_5m_bars
agg_15m_bars
agg_1h_bars
agg_1d_bars
🧠 Metadata & Fundamentals
fundamental_data
symbol_metadata
symbol_profile_view (joins fundamentals, metadata, and evaluator flags)
🧪 Tracking & Audit Tables
minute_bar_audit
trade_triggers
ingest_sessions
evaluator_flags

🧩 Schema Highlights
Uses TimescaleDB hypertables for time-series performance.
Includes continuous aggregates for multi-resolution analysis.
Tracks symbol lifecycle flags like do_not_trade, manual_exclude, ipo_recent.
Supports session-level ingestion tracking via ingest_sessions.
Provides audit trail for minute bar integrity.
Fully indexed for performance across fundamentals, metadata, and flags.

🖥️ Flask Interface Responsibilities
Front Door Dashboard:

Displays basic DB stats (nerd-level).
Must not crash if DB is missing or corrupt.
Shows status of hypertables, views, symbol counts, ingestion health.
Environment Switching:

Supports multiple environments:
Dev, Production, and future Offsite Co-Lo.
Configurable via config.py and Flask routing.
🧠 Symbol Lifecycle Logic (Retained)
