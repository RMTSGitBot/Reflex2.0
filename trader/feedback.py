from trader.trace import log_trade_event

MODEL_FEEDBACK = {}

def update_model_feedback(symbol, broker, account, slippage, latency, fill_status):
    key = f"{broker}:{account}:{symbol}"
    if key not in MODEL_FEEDBACK:
        MODEL_FEEDBACK[key] = {"slippage": [], "latency": [], "adjustments": []}

    MODEL_FEEDBACK[key]["slippage"].append(slippage)
    MODEL_FEEDBACK[key]["latency"].append(latency)

    # Adaptive logic (example)
    if slippage > 0.5:
        MODEL_FEEDBACK[key]["adjustments"].append("widen_limit")
    if latency > 2.0:
        MODEL_FEEDBACK[key]["adjustments"].append("reduce_size")

    log_trade_event(symbol, "feedback", {
        "slippage": slippage,
        "latency": latency,
        "adjustments": MODEL_FEEDBACK[key]["adjustments"]
    })

def get_model_feedback(symbol, broker, account):
    key = f"{broker}:{account}:{symbol}"
    return MODEL_FEEDBACK.get(key, {})