import datetime
from trader.trace import log_trade_event
from trader.config.accounts import get_account_config
from broker_api import sync_account_status  # abstracted broker sync

def validate_trade(symbol, size, price, broker, account, session):
    config = get_account_config(broker, account)
    status = sync_account_status(broker, account)

    buying_power = status.get("buying_power", 0)
    margin = config.get("margin", False)
    pdt = config.get("pdt", False)

    cost = price * size
    if not margin and cost > buying_power:
        return False, f"Insufficient buying power: {cost} > {buying_power}"

    if pdt and session == "regular":
        # Optional: enforce manual review
        log_trade_event(symbol, "pdt_flagged", {
            "account": account, "cost": cost, "session": session
        })

    return True, "ok"

def get_risk_status(broker, account):
    return sync_account_status(broker, account)