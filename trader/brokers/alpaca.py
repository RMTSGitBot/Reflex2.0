from alpaca_trade_api.rest import REST
from trader.config.accounts import get_account_config

def send_order(symbol, action, size, price, tif, session, account, order_type="limit"):
    creds = get_account_config("alpaca", account)
    client = REST(creds["key"], creds["secret"], base_url="https://paper-api.alpaca.markets" if creds["paper"] else "https://api.alpaca.markets")

    side = "buy" if action == "buy" else "sell"
    extended = session != "regular"

    order = client.submit_order(
        symbol=symbol,
        qty=size,
        side=side,
        type=order_type,
        time_in_force=tif,
        limit_price=price if order_type == "limit" else None,
        extended_hours=extended
    )

    return {
        "order_id": order.id,
        "status": order.status,
        "fill_price": getattr(order, "filled_avg_price", None)
    }

def get_positions(account):
    creds = get_account_config("alpaca", account)
    client = REST(creds["key"], creds["secret"], base_url="https://paper-api.alpaca.markets" if creds["paper"] else "https://api.alpaca.markets")
    return [{"symbol": p.symbol, "qty": float(p.qty)} for p in client.list_positions()]

def sync_account_status(broker, account):
    creds = get_account_config("alpaca", account)
    client = REST(creds["key"], creds["secret"], base_url="https://paper-api.alpaca.markets" if creds["paper"] else "https://api.alpaca.markets")
    a = client.get_account()
    return {
        "buying_power": float(a.buying_power),
        "margin": a.margin_available != "0",
        "pdt": a.pattern_day_trader
    }