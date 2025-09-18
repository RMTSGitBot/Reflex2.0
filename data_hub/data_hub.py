# data_hub/datahub.py
import threading
import os
from datetime import datetime

from shared_mem.buffers import initialize_memory
from shared_mem.registry import initialize_registry, registry
from ingestion.cold_hydration import (
    load_fundamentals,
    load_indicator_precals,
    load_daily_bars,
    load_minute_bars,
    load_ticks
)
from ingestion.tick_stream import start_tick_stream
from ingestion.quote_stream import start_quote_stream
from snapshots.snapshot_loop import start_snapshot_loop
from evaluator.evaluator_loop import start_evaluator_loop
from diagnostics.model_logger import log_model_decision

# These now live in data_hub instead of core
from data_hub.load_symbols import load_symbols_from_db
from data_hub.load_models import load_models_for_symbols

# Events for main.py to wait on
registry_ready = threading.Event()
snapshots_ready = threading.Event()

REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"

def run_datahub():
    print(f"[🧩] DataHub starting at {datetime.utcnow().isoformat()} (mode: {'REPLAY' if REPLAY_MODE else 'LIVE'})")

    # 1. Load eligible symbols (skip do_not_trade)
    symbols = load_symbols_from_db(exclude_flag="do_not_trade")
    print(f"[📜] Loaded {len(symbols)} eligible symbols from DB.")

    # 2. Initialize memory and registry
    initialize_memory(symbols)
    initialize_registry(symbols)

    # 3. Load models for each symbol (default to momentum_filter_v2 if none assigned)
    load_models_for_symbols(symbols, default_model="momentum_filter_v2.json")

    # 4. Hydration pass for all eligible symbols
    for sym in symbols:
        load_fundamentals(sym)
        load_indicator_precals(sym)  # enough data for filters to run immediately

    # 5. Deep hydration for WARM/HOT symbols
    for sym in symbols:
        state = registry[sym]['state']
        if state in ('WARM', 'HOT'):
            print(f"[🔥] Deep hydrating {sym} ({state})...")
            load_daily_bars(sym, lookback_days=252)  # ~1 year
            load_minute_bars(sym, enough_for_indicators=True)
            load_ticks(sym, days=2, up_to_now=True)

    # 6. Signal registry readiness
    registry_ready.set()
    print("[✅] Registry hydrated and ready.")

    # 7. Start ingestion streams
    threading.Thread(target=start_tick_stream, name="TickStream", daemon=True).start()
    threading.Thread(target=start_quote_stream, name="QuoteStream", daemon=True).start()

    # 8. Start snapshot loop
    threading.Thread(target=start_snapshot_loop, name="SnapshotLoop", daemon=True).start()
    snapshots_ready.set()
    print("[✅] Snapshot loop started.")

    # 9. Start evaluator loop
    threading.Thread(target=start_evaluator_loop, name="EvaluatorLoop", daemon=True).start()

    # 10. Log DataHub start
    for sym in symbols:
        log_model_decision(
            sym