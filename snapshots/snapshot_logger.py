import csv
import os
from datetime import datetime

LOG_PATH = os.path.abspath("logs/snapshot_log.csv")

def log_snapshot(symbol, snapshot):
    fields = [
        "timestamp", "symbol", "last_price", "momentum", "volume", "tape_pressure",
        "vwap", "atr", "rsi", "spread", "gain_points", "drawdown_points",
        "entry_ready", "bull_flag", "last_bar_cross", "volume_near_ask", "volume_near_bid"
    ]
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": symbol,
        **{k: snapshot.get(k, "") for k in fields if k != "timestamp" and k != "symbol"}
    }

    write_header = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow(row)