import numpy as np
from collections import deque
from shared_mem.registry import registry
from common.timeutils import get_current_session
from trader.trace import log_trade_event

ROLLING_WINDOW = 30

def hydrate_snapshot(symbol, quote):
    session = get_current_session()

    # --- Base snapshot ---
    snapshot = {
        "timestamp": quote.get("timestamp"),
        "bid": quote.get("bid", 0.0),
        "ask": quote.get("ask", 0.0),
        "last_price": quote.get("last_price", 0.0),
        "volume": quote.get("volume", 0),
        "session": session
    }

    # --- Volatility (session-aware) ---
    vol_key = f"volatility_buffer_{session}"
    if vol_key not in registry[symbol]:
        registry[symbol][vol_key] = deque(maxlen=ROLLING_WINDOW)

    registry[symbol][vol_key].append(snapshot["last_price"])
    buffer = registry[symbol][vol_key]
    snapshot["volatility"] = float(np.std(buffer)) if len(buffer) >= 5 else 0.0

    # --- Rolling Spread ---
    spread = snapshot["ask"] - snapshot["bid"]
    if "spread_buffer" not in registry[symbol]:
        registry[symbol]["spread_buffer"] = deque(maxlen=ROLLING_WINDOW)
    registry[symbol]["spread_buffer"].append(spread)
    snapshot["rolling_spread"] = float(np.mean(registry[symbol]["spread_buffer"]))

    # --- Tape Pressure ---
    buy_vol = quote.get("buy_volume", 0)
    sell_vol = quote.get("sell_volume", 0)
    delta = buy_vol - sell_vol
    if abs(delta) < 100:
        snapshot["tape_pressure"] = "neutral"
    elif delta > 0:
        snapshot["tape_pressure"] = "buy"
    else:
        snapshot["tape_pressure"] = "sell"

    # --- Diagnostics ---
    if snapshot["bid"] == 0 or snapshot["ask"] == 0:
        log_trade_event(symbol, "missing_quote", {"timestamp": snapshot["timestamp"]})
    if snapshot["volatility"] == 0.0 and len(buffer) >= 5:
        log_trade_event(symbol, "flat_volatility", {"timestamp": snapshot["timestamp"]})

    # --- Inject into registry ---
    registry[symbol]["snapshot"] = snapshot