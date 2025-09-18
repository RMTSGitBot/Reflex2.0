METRICS = {}

def log_trade(symbol, action, size, price, snapshot):
    if symbol not in METRICS:
        METRICS[symbol] = []
    METRICS[symbol].append({
        "timestamp": snapshot["timestamp"],
        "action": action,
        "size": size,
        "price": price,
        "bid": snapshot["bid"],
        "ask": snapshot["ask"],
        "spread": snapshot["ask"] - snapshot["bid"]
    })

def get_metrics():
    return METRICS