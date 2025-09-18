# --- add_logic.py ---
# Reflexion Add-to-Position Logic: Modular, model-driven, cockpit-controllable

from trader.trade_queue import trade_queue
from diagnostics.model_logger import log_model_decision

def run_add_logic(symbol, snapshot, model, flags):
    add_model = model.get('add_model', {})
    add_type = add_model.get('type')
    params = add_model.get('params', {})

    add_count = flags.setdefault('add_count', 0)
    max_adds = params.get('max_adds', 1)
    add_size = params.get('add_size', 1)

    if add_count >= max_adds:
        return

    if add_type == "liquidity_absorption":
        threshold = params.get('absorption_threshold', 0.8)
        spread_behavior = params.get('spread_behavior', "narrowing")

        if snapshot.get('ask_volume_absorbed', 0) >= threshold:
            if spread_behavior == "narrowing" and not snapshot.get('spread_narrowing'):
                return
            if spread_behavior == "stable" and not snapshot.get('spread_stable'):
                return

            trade_queue.put((symbol, "buy", {"qty": add_size}))
            flags['add_count'] += 1
            log_model_decision(symbol, "add_liquidity_absorption", model, snapshot, flags)
            print(f"[⚡] {symbol} added to position on absorption ({flags['add_count']}/{max_adds})")

    elif add_type == "vwap_reentry":
        vwap = snapshot.get("vwap", 0)
        last_price = snapshot.get("last_price", 0)
        if abs(last_price - vwap) < params.get("vwap_tolerance", 0.05) and snapshot.get("momentum", 0) > 0.01:
            trade_queue.put((symbol, "buy", {"qty": add_size}))
            flags['add_count'] += 1
            log_model_decision(symbol, "add_vwap_reentry", model, snapshot, flags)
            print(f"[🔁] {symbol} added on VWAP reentry ({flags['add_count']}/{max_adds})")

    elif add_type == "tape_pressure_add":
        if snapshot.get("tape_pressure", 0) > params.get("pressure_threshold", 0.75) and snapshot.get("volume_near_ask"):
            trade_queue.put((symbol, "buy", {"qty": add_size}))
            flags['add_count'] += 1
            log_model_decision(symbol, "add_tape_pressure", model, snapshot, flags)
            print(f"[📈] {symbol} added on tape pressure ({flags['add_count']}/{max_adds})")

    elif add_type == "trend_continuation":
        if snapshot.get("momentum", 0) > params.get("momentum_threshold", 0.02) and snapshot.get("rsi", 50) > params.get("rsi_min", 55):
            trade_queue.put((symbol, "buy", {"qty": add_size}))
            flags['add_count'] += 1
            log_model_decision(symbol, "add_trend_continuation", model, snapshot, flags)
            print(f"[📊] {symbol} added on trend continuation ({flags['add_count']}/{max_adds})")

    elif add_type == "iceberg_detection":
        if snapshot.get("quote_depth", 0) > params.get("depth_threshold", 5) and snapshot.get("ask_size", 0) < params.get("visible_size_max", 100):
            trade_queue.put((symbol, "buy", {"qty": add_size}))
            flags['add_count'] += 1
            log_model_decision(symbol, "add_iceberg_detected", model, snapshot, flags)
            print(f"[🧊] {symbol} added on iceberg detection ({flags['add_count']}/{max_adds})")