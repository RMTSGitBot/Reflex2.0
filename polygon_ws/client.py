import websocket
import json
import threading
import time
from common.config import POLYGON_API
from diagnostics.model_logger import log_model_decision
from shared_mem.registry import registry

POLYGON_WS_URL = "wss://socket.polygon.io/stocks"

def _run_ws(url, auth_key, subs, on_message):
    def _on_open(ws):
        ws.send(json.dumps({"action": "auth", "params": auth_key}))
        for sub in subs:
            ws.send(json.dumps({"action": "subscribe", "params": sub}))
        print(f"[📡] Subscribed to: {subs}")

    def _on_error(ws, error):
        print(f"[❌] WebSocket error: {error}")

    def _on_close(ws, close_status_code, close_msg):
        print(f"[⚠️] WebSocket closed: {close_status_code} {close_msg}")

    def _on_message(ws, message):
        try:
            data = json.loads(message)
            for event in data:
                on_message(event)
        except Exception as e:
            print(f"[⚠️] WS message parse error: {e}")

    ws_app = websocket.WebSocketApp(
        url,
        on_open=_on_open,
        on_message=_on_message,
        on_error=_on_error,
        on_close=_on_close
    )

    threading.Thread(target=ws_app.run_forever, daemon=True).start()

def connect_tick_ws(on_message, symbols):
    subs = [f"T.{sym}" for sym in symbols]
    _run_ws(POLYGON_WS_URL, POLYGON_API, subs, on_message)

def connect_quote_ws(on_message, symbols):
    subs = [f"Q.{sym}" for sym in symbols]
    _run_ws(POLYGON_WS_URL, POLYGON_API, subs, on_message)