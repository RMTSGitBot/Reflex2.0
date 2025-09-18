PORTFOLIO = {}

def update_portfolio(symbol, action, size, price, broker, account):
    key = f"{broker}:{account}"
    if key not in PORTFOLIO:
        PORTFOLIO[key] = {}
    if symbol not in PORTFOLIO[key]:
        PORTFOLIO[key][symbol] = {"position": 0, "avg_price": 0.0, "closed": []}

    pos = PORTFOLIO[key][symbol]["position"]
    avg = PORTFOLIO[key][symbol]["avg_price"]

    if action == "buy":
        new_pos = pos + size
        new_avg = ((avg * pos) + (price * size)) / max(1, new_pos)
        PORTFOLIO[key][symbol]["position"] = new_pos
        PORTFOLIO[key][symbol]["avg_price"] = new_avg
    elif action == "sell":
        PORTFOLIO[key][symbol]["position"] -= size
        pnl = (price - avg) * size
        PORTFOLIO[key][symbol]["closed"].append({
            "size": size, "price": price, "pnl": pnl
        })

def get_portfolio():
    return PORTFOLIO