def detect_bull_flag(snapshot):
    return snapshot["momentum"] > 0.01 and snapshot["volume"] > 10000

def detect_last_bar_cross(snapshot):
    return snapshot["last_price"] > snapshot.get("prev_bar_high", 0)