import os
import time
import threading
import pandas as pd
from datetime import date
from shared_mem.registry import registry
from shared_mem.buffers import symbol_buffers
from common.timeutils import REPLAY_MODE, get_session_anchor
from market_data.api import fetch_ticks
from polygon_ws.client import connect_tick_ws

def _append_trade(symbol, ts, price, size):
    event = {"timestamp": ts, "price": float(price), "size": int(size)}
    symbol_buffers[symbol]["trades"].append(event)
    registry[symbol]["last_price"] = float(price)
    registry[symbol]["last_update"] = ts

def _replay_ticks(symbols, speed, stop_event):
    anchor = get_session_anchor()
    start_day = anchor.date()
    end_day = anchor.date()

    frames = []
    for sym in symbols:
        df = fetch_ticks(sym, start_day, end_day)
        if df.empty:
            continue
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df[df["timestamp"] >= pd.Timestamp(anchor)]
        df["symbol"] = sym
        frames.append(df[["timestamp", "symbol", "price", "size"]])

    if not frames:
        print("[⏪] No replay tick data found.")
        return

    merged = pd.concat(frames).sort_values("timestamp").reset_index(drop=True)
    sim_start = merged.iloc[0]["timestamp"].to_pydatetime()
    wall_start = time.monotonic()

    for _, row in merged.iterrows():
        if stop_event.is_set():
            break
        ts = row["timestamp"].to_pydatetime()
        sym = row["symbol"]
        sim_elapsed = (ts - sim_start).total_seconds()
        target_wall = sim_elapsed / max(0.0001, speed)
        sleep_s = target_wall - (time.monotonic() - wall_start)
        if sleep_s > 0:
            time.sleep(sleep_s)
        _append_trade(sym, ts.isoformat(), row["price"], row["size"])

def _live_ticks(symbols, stop_event):
    def on_trade(event):
        if event.get("ev") != "T":
            return
        sym = event["sym"]
        ts = event["t"]
        price = event["p"]
        size = event["s"]
        _append_trade(sym, ts, price, size)

    connect_tick_ws(on_trade, symbols)

def start_tick_stream(symbols=None, speed=None, stop_event=None):
    if symbols is None:
        symbols = list(registry.keys())
    if stop_event is None:
        stop_event = threading.Event()
    if speed is None:
        speed = float(os.getenv("REFLEXION_REPLAY_SPEED", "1.0"))

    def runner():
        if REPLAY_MODE:
            _replay_ticks(symbols, speed, stop_event)
        else:
            _live_ticks(symbols, stop_event)

    threading.Thread(target=runner, name="TickStream", daemon=True).start()
    print(f"[▶] Tick stream started ({'REPLAY' if REPLAY_MODE else 'LIVE'}; speed={speed}x).")
    return stop_event