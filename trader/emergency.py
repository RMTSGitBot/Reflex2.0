from trader.brokers import alpaca, ibkr, webull
from trader.trace import log_trade_event

def emergency_liquidate():
    for broker in ["alpaca", "ibkr", "webull"]:
        accounts = get_all_accounts(broker)
        for account in accounts:
            try:
                positions = get_positions(broker, account)
                for pos in positions:
                    symbol = pos["symbol"]
                    size = pos["qty"]
                    action = "sell" if size > 0 else "buy"
                    result = send_market_order(broker, symbol, action, abs(size), account)
                    log_trade_event(symbol, "emergency_liquidate", {
                        "broker": broker, "account": account,
                        "action": action, "size": size, "result": result
                    })
            except Exception as e:
                log_trade_event("system", "emergency_error", {
                    "broker": broker, "account": account, "error": str(e)
                })

def send_market_order(broker, symbol, action, size, account):
    if broker == "alpaca":
        return alpaca.send_order(symbol, action, size, price=None, tif="DAY", session="regular", account=account, order_type="market")
    elif broker == "ibkr":
        return ibkr.send_order(symbol, action, size, price=None, tif="DAY", session="regular", account=account, order_type="market")
    elif broker == "webull":
        return webull.send_order(symbol, action, size, price=None, tif="DAY", session="regular", account=account, order_type="market")