import os
import time
import threading
import pandas as pd
from datetime import date
from shared_mem.registry import registry
from shared_mem.buffers import symbol_buffers
from shared_mem.hydrator import hydrate_snapshot
from common.timeutils import REPLAY_MODE, get_session_anchor
from market_data.api import fetch_quotes
from polygon_ws.client import connect_quote_ws

def _append_quote(symbol, ts, bid, bid_size, ask, ask_size):
    event = {
        "timestamp": ts,
        "bid_price": float(bid),
        "bid_size": int(bid_size),
        "ask_price": float(ask),
        "ask_size": int(ask_size)
    }
    symbol_buffers[symbol]["quotes"].append(event)

    quote = {
        "timestamp": ts,
        "bid": float(bid),
        "ask": float(ask),
        "last_price": (float(bid) + float(ask)) / 2,
        "volume": bid_size + ask_size,
        "buy_volume": bid_size,
        "sell_volume": ask_size
    }

    hydrate_snapshot(symbol, quote)

    registry[symbol]["last_quote"] = {
        "bid": float(bid),
        "ask": float(ask),
        "timestamp": ts
    }
    registry[symbol]["last_update"] = ts

def _replay_quotes(symbols, speed, stop_event):
    anchor = get_session_anchor()
    start_day = anchor.date()
    end_day = anchor.date()

    frames = []
    for sym in symbols:
        df = fetch_quotes(sym, start_day, end_day)
        if df.empty:
            continue
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df[df["timestamp"] >= pd.Timestamp(anchor)]
        df["symbol"] = sym
        frames.append(df[["timestamp", "symbol", "bid_price", "bid_size", "ask_price", "ask_size"]])

    if not frames:
        print("[⏪] No replay quote data found.")
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
        _append_quote(sym, ts.isoformat(), row["bid_price"], row["bid_size"], row["ask_price"], row["ask_size"])

def _live_quotes(symbols, stop_event):
    def on_quote(event):
        if event.get("ev") != "Q":
            return
        sym = event["sym"]
        ts = event["t"]
        bid = event["bp"]
        bid_size = event["bs"]
        ask = event["ap"]
        ask_size = event["as"]
        _append_quote(sym, ts, bid, bid_size, ask, ask_size)

    connect_quote_ws(on_quote, symbols)

def start_quote_stream(symbols=None, speed=None, stop_event=None):
    if symbols is None:
        symbols = list(registry.keys())
    if stop_event is None:
        stop_event = threading.Event()
    if speed is None:
        speed = float(os.getenv("REFLEXION_REPLAY_SPEED", "1.0"))

    def runner():
        if REPLAY_MODE:
            _replay_quotes(symbols, speed, stop_event)
        else:
            _live_quotes(symbols, stop_event)

    threading.Thread(target=runner, name="QuoteStream", daemon=True).start()
    print(f"[▶] Quote stream started ({'REPLAY' if REPLAY_MODE else 'LIVE'}; speed={speed}x).")
    return stop_event