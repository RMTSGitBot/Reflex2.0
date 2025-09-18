import threading
import time
from ingestion.quote_stream import start_quote_stream
from trader.api_server import app  # or whatever the correct path is
from shared_mem.registry import registry
from common.timeutils import get_session_anchor

def boot_registry():
    # Optional: load symbols from manifest or config
    symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOG"]
    for sym in symbols:
        registry[sym] = {
            "snapshot": {},
            "model": {},  # or load from model manifest
            "price_buffer": [],
            "spread_buffer": [],
            "last_quote": {},
            "last_update": None
        }
    print(f"[🧠] Registry initialized with {len(symbols)} symbols.")

def start_api_server():
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080, debug=False), name="APIServer", daemon=True).start()
    print("[🌐] API server launched on port 8080.")

def launch_reflexion():
    print("[🚀] Launching Reflexion...")
    boot_registry()
    anchor = get_session_anchor()
    print(f"[🕒] Session anchor: {anchor.isoformat()}")

    stop_event = start_quote_stream()
    start_api_server()

    while True:
        time.sleep(10)  # Keep main thread alive

if __name__ == "__main__":
    launch_reflexion()