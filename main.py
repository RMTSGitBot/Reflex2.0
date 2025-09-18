# --- main.py ---
# Reflexion Launcher with Replay Mode, Logging, and Model Tracking

import threading
import time
import signal
import sys
import os
from datetime import datetime

from core import run_datahub, registry_ready, snapshots_ready
from diagnostics.heartbeat import heartbeat_monitor
from diagnostics.model_tracker import start_model_tracker
from rest_api.api_server import app
from common.dbutils import test_connection
from trader.main import launch_trader
from pubsub.pubsub_loop import start_pubsub_loop  # cockpit event bus

REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"

def _start_thread(target, name, args=(), kwargs=None, daemon=True, delay=0.0):
    def _wrapped_target(*a, **k):
        try:
            target(*a, **k)
        except Exception as e:
            print(f"[❌] Thread {name} crashed: {e}")
    t = threading.Thread(target=_wrapped_target, name=name, args=args, kwargs=kwargs or {}, daemon=daemon)
    t.start()
    if delay:
        time.sleep(delay)
    return t

def _await_readiness(timeout_registry=10.0, timeout_snapshots=15.0):
    print("[⏳] Awaiting registry hydration...")
    registry_ready.wait(timeout=timeout_registry)
    print("[⏳] Awaiting snapshot priming...")
    snapshots_ready.wait(timeout=timeout_snapshots)
    print("[✅] System primed.")

def _install_signal_handlers():
    def _graceful_exit(signum, frame):
        print(f"[🛑] Signal {signum} received at {datetime.utcnow().isoformat()}. Shutting down Reflexion...")
        sys.exit(0)
    for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", None)):
        if sig:
            try:
                signal.signal(sig, _graceful_exit)
            except Exception:
                pass

if __name__ == "__main__":
    print(f"[🧠] Reflexion boot sequence initiated at {datetime.utcnow().isoformat()}")
    print(f"[⚙️] Mode: {'REPLAY' if REPLAY_MODE else 'LIVE'}")

    _install_signal_handlers()

    print("[🔍] Testing DB connection...")
    test_connection()

    print("[🚀] Launching DataHub...")
    _start_thread(run_datahub, name="DataHub", delay=0.1)

    print("[💓] Starting heartbeat monitor...")
    _start_thread(heartbeat_monitor, name="Heartbeat", args=(10, 30))

    print("[📊] Starting model tracker...")
    _start_thread(start_model_tracker, name="ModelTracker")

    print("[📢] Starting cockpit event bus listener...")
    _start_thread(start_pubsub_loop, name="PubSubLoop")

    print("[🌐] Starting API server...")
    _start_thread(app.run, name="API", kwargs={"host": "0.0.0.0", "port": 5055})

    _await_readiness()

    if not REPLAY_MODE:
        print("[📡] Starting trader (alpaca)...")
        _start_thread(launch_trader, name="Trader-Alpaca", args=("alpaca",))
    else:
        print("[⏪] Replay mode active — trader not launched.")

    print("[🧠] Reflexion is live. Awaiting signals...")
    threading.Event().wait()