from snapshots.snapshot_patterns import detect_bull_flag, detect_last_bar_cross
from snapshots.snapshot_metrics import compute_vwap, compute_atr, compute_rsi
from snapshots.snapshot_metrics import compute_volatility

def enrich_snapshot(symbol, snapshot):
    snapshot["entry_ready"] = snapshot["momentum"] > 0.01
    snapshot["bull_flag"] = detect_bull_flag(snapshot)
    snapshot["last_bar_cross"] = detect_last_bar_cross(snapshot)

    snapshot["vwap"] = compute_vwap(symbol)
    snapshot["atr"] = compute_atr(symbol)
    snapshot["rsi"] = compute_rsi(symbol)

    snapshot["gain_points"] = snapshot["last_price"] - snapshot.get("entry_price", snapshot["last_price"])
    snapshot["drawdown_points"] = snapshot.get("entry_price", snapshot["last_price"]) - snapshot["last_price"]

    snapshot["volume_near_ask"] = snapshot["ask_size"] > 500
    snapshot["volume_near_bid"] = snapshot["bid_size"] > 500
    snapshot["ask_volume_absorbed"] = snapshot["ask_size"] < 100
    snapshot["spread_narrowing"] = snapshot["spread"] < 0.02
    snapshot["spread_stable"] = 0.02 <= snapshot["spread"] <= 0.05
    snapshot["volatility"] = compute_volatility(symbol)


    return snapshot