import datetime
from trader.trace import log_trade_event, analyze_slippage
from trader.portfolio import update_portfolio
from trader.orders import track_order, remove_order
from trader.risk import validate_trade
from trader.brokers import alpaca, ibkr, webull
from common.timeutils import get_current_session
from shared_mem.registry import registry

def handle_trade(symbol, action, size, price, broker, account, order_type="limit", tif="DAY"):
    session = get_current_session()
    quote = registry[symbol].get("last_quote", {})
    arrival_price = (quote.get("bid", 0) + quote.get("ask", 0)) / 2

    # Sanity + risk checks
    ok, reason = validate_trade(symbol, size, price, broker, account, session)
    if not ok:
        return {"status": "rejected", "reason": reason}

    # Log intent
    log_trade_event(symbol, "intent", {
        "action": action, "size": size, "price": price,
        "broker": broker, "account": account,
        "session": session, "arrival": arrival_price,
        "order_type": order_type, "tif": tif
    })

    # Dispatch to broker
    if broker == "alpaca":
        result = alpaca.send_order(symbol, action, size, price, tif, session, account)
    elif broker == "ibkr":
        result = ibkr.send_order(symbol, action, size, price, tif, session, account)
    elif broker == "webull":
        result = webull.send_order(symbol, action, size, price, tif, session, account)
    else:
        return {"status": "error", "reason": "Unknown broker"}

    # Log confirmation
    log_trade_event(symbol, "confirm", result)
    track_order(symbol, result.get("order_id"), result)

    # Slippage analysis
    analyze_slippage(symbol, arrival_price, price, result.get("fill_price"), result.get("status"))

    # Portfolio update
    update_portfolio(symbol, action, size, result.get("fill_price"), broker, account)

    # Cleanup if filled
    if result.get("status") == "filled":
        remove_order(symbol, result.get("order_id"))

    return result