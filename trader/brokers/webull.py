def send_order(symbol, action, size, price, tif, session, account, order_type="limit"):
    # Placeholder for Webull SDK or API integration
    return {
        "order_id": f"webull-{symbol}-{action}",
        "status": "simulated",
        "fill_price": price
    }

def get_positions(account):
    # Simulated positions
    return [{"symbol": "AAPL", "qty": 100}, {"symbol": "TSLA", "qty": -50}]

def sync_account_status(broker, account):
    # Simulated account status
    return {
        "buying_power": 100000,
        "margin": False,
        "pdt": True
    }