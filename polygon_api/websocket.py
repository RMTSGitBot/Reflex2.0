# --- polygon_ws/client.py ---
import websocket
import json
import threading
import time
from common.config import POLYGON_API
from diagnostics.model_logger import log_model_decision
from shared_mem.registry import registry

POLYGON_TRADE_URL = "wss://socket.polygon.io/stocks"
POLYGON_QUOTE_URL = "wss://socket.polygon.io/stocks"

def _run_ws(url, auth_key, subs, on_message):
    def _on_open(ws):
        # Authenticate
        ws.send(json.dumps({"action": "auth", "params": auth_key}))
        # Subscribe to channels
        for sub in subs:
            ws.send(json.dumps({"action": "subscribe", "params": sub}))
        print(f"[📡] Subscribed to: {subs}")

    def _on_error(ws, error):
        print(f"[❌] WebSocket error: {error}")

    def _on_close(ws, close_status_code, close_msg):
        print(f"[⚠️] WebSocket closed: {close_status_code} {close_msg}")
        # Optional: reconnect logic here

    ws_app = websocket.WebSocketApp(
        url,
        on_open=_on_open,
        on_message=on_message,
        on_error=_on_error,
        on_close=_on_close
    )

    # Run in thread so it doesn't block
    threading.Thread(target=ws_app.run_forever, daemon=True).start()

def connect_tick_ws(on_message, symbols):
    subs = [f"T.{sym}" for sym in symbols]  # Polygon trade channel format
    _run_ws(POLYGON_TRADE_URL, POLYGON_API, subs, on_message)

def connect_quote_ws(on_message, symbols):
    subs = [f"Q.{sym}" for sym in symbols]  # Polygon quote channel format
    _run_ws(POLYGON_QUOTE_URL, POLYGON_API, subs, on_message)