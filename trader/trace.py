TRADE_EVENTS = []

def log_trade_event(symbol, event_type, data):
    TRADE_EVENTS.append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "symbol": symbol,
        "event": event_type,
        "data": data
    })

def analyze_slippage(symbol, arrival, limit, fill, status):
    if fill is None:
        return
    slippage = fill - arrival
    log_trade_event(symbol, "slippage", {
        "arrival": arrival,
        "limit": limit,
        "fill": fill,
        "slippage": slippage,
        "status": status
    })

def get_trade_log():
    return TRADE_EVENTS[-100:]