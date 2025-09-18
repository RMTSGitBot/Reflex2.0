from ib_insync import IB, Stock, LimitOrder
from trader.config.accounts import get_account_config

def send_order(symbol, action, size, price, tif, session, account, order_type="limit"):
    creds = get_account_config("ibkr", account)
    ib = IB()
    ib.connect(creds["host"], creds["port"], clientId=creds["client_id"])

    contract = ib.qualifyContracts(Stock(symbol))[0]
    order = LimitOrder(action.upper(), size, price)
    order.tif = tif
    order.outsideRth = session != "regular"

    trade = ib.placeOrder(contract, order)
    ib.sleep(1)
    status = trade.orderStatus.status
    fill_price = trade.orderStatus.avgFillPrice
    ib.disconnect()

    return {
        "order_id": trade.order.orderId,
        "status": status,
        "fill_price": fill_price
    }

def get_positions(account):
    creds = get_account_config("ibkr", account)
    ib = IB()
    ib.connect(creds["host"], creds["port"], clientId=creds["client_id"])
    positions = ib.positions()
    ib.disconnect()
    return [{"symbol": p.contract.symbol, "qty": p.position} for p in positions]

def sync_account_status(broker, account):
    creds = get_account_config("ibkr", account)
    ib = IB()
    ib.connect(creds["host"], creds["port"], clientId=creds["client_id"])
    account_summary = ib.accountSummary()
    ib.disconnect()
    return {
        "buying_power": float(account_summary.get("BuyingPower", 0)),
        "margin": True,
        "pdt": False  # IBKR doesn't expose PDT flag directly
    }