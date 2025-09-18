LIVE_ORDERS = {}

def track_order(symbol, order_id, details):
    LIVE_ORDERS[order_id] = {
        "symbol": symbol,
        "submitted": datetime.datetime.utcnow().isoformat(),
        "details": details
    }

def remove_order(symbol, order_id):
    if order_id in LIVE_ORDERS:
        del LIVE_ORDERS[order_id]

def get_live_orders():
    return list(LIVE_ORDERS.values())