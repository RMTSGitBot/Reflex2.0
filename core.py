# --- core.py ---
# Reflexion DataHub Orchestration with Readiness Handshake, Replay Mode, and Diagnostics

import threading
import time
import os

from ingestion.tick_stream import start_tick_stream
from ingestion.quote_stream import start_quote_stream
from ingestion.bar_builder import start_bar_builder
from ingestion.daily_updater import start_daily_bar_updater
from ingestion.cold_hydration import hydrate_registry
from snapshots.snapshot_loop import start_snapshot_loop
from evaluator.evaluator import start_evaluator
from diagnostics.symbol_health_check import start_diagnostics
from pubsub.pubsub import start_pubsub_loop
from shared_mem.buffers import initialize_memory
from diagnostics.model_tracker import start_model_tracker

# --- Readiness Events ---
registry_ready = threading.Event()
snapshots_ready = threading.Event()

# --- Replay Mode Toggle ---
REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"

def run_datahub():
    print("🚀 Reflexion DataHub starting...")
    initialize_memory()
    print("[🧠] Memory buffers initialized.")

    hydrate_registry()
    registry_ready.set()
    print("[💾] Registry hydrated.")

    if not REPLAY_MODE:
        print("[📡] Starting live ingestion streams...")
        threading.Thread(target=start_tick_stream, daemon=True).start()
        threading.Thread(target=start_quote_stream, daemon=True).start()
        time.sleep(0.5)

        print("[📊] Starting bar builders...")
        threading.Thread(target=start_bar_builder, daemon=True).start()
        threading.Thread(target=start_daily_bar_updater, daemon=True).start()
    else:
        print("[⏪] Replay mode active — skipping live ingestion.")

    def snapshot_wrapper():
        start_snapshot_loop()
        snapshots_ready.set()

    print("[🖼️] Starting snapshot loop...")
    threading.Thread(target=snapshot_wrapper, daemon=True).start()

    print("[⏳] Waiting for registry + snapshots to be ready...")
    registry_ready.wait(timeout=2)
    snapshots_ready.wait(timeout=2)

    print("[🧠] Starting evaluator...")
    threading.Thread(target=start_evaluator, daemon=True).start()

    print("[🔍] Starting diagnostics...")
    threading.Thread(target=start_diagnostics, daemon=True).start()

    print("[📢] Starting pub/sub loop...")
    threading.Thread(target=start_pubsub_loop, daemon=True).start()

    print("[📈] Starting model tracker...")
    threading.Thread(target=start_model_tracker, daemon=True).start()

    print("✅ DataHub is live and reflexive.")