from trader.trace import log_trade_event
from trader.portfolio import update_portfolio

def simulate_fill(symbol, action, size, snapshot):
    price = snapshot["ask"] if action == "buy" else snapshot["bid"]
    log_trade_event(symbol, "simulated_fill", {
        "action": action, "size": size, "price": price
    })
    update_portfolio(symbol, action, size, price, "simulated", "backtest")
    return price