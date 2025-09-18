from trader.execute import handle_trade

def evaluate_model(symbol, snapshot, model_name, broker, account):
    model = registry[symbol]["model"]
    filters = model["entry_model"]["filters"]
    passed = all(eval(f"{snapshot[f['field']]} {f['operator']} {f['threshold']}") for f in filters)
    if not passed:
        return None

    action = "buy"
    size = model["entry_model"]["size"]
    price = snapshot["ask"]
    return handle_trade(symbol, action, size, price, broker, account, "limit", "DAY")