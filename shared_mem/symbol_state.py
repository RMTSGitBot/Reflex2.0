# --- shared_mem/symbol_state.py ---
from datetime import datetime
from diagnostics.model_logger import log_model_decision
from shared_mem.registry import registry

def update_symbol_state(symbol):
    """
    Updates the state (COLD/WARM/HOT) of a symbol based on buffer depths and quote depth.
    Uses separate trade/quote buffers from the upgraded registry.
    """
    trades_buf = registry[symbol]['buffers']['trades']
    quotes_buf = registry[symbol]['buffers']['quotes']

    snapshot_ready = bool(registry[symbol]['snapshot'])
    reflexive_depth = len(trades_buf.get_short())
    contextual_depth = len(trades_buf.get_long())

    # Derive quote depth from latest quote buffer entry if available
    latest_quote = quotes_buf.get_short()[-1] if quotes_buf.get_short() else {}
    depth = registry[symbol].get('quote_depth') or latest_quote.get('depth', 0) or 0

    prev_state = registry[symbol]['state']

    if not snapshot_ready:
        new_state = 'COLD'
    elif contextual_depth >= 100 and depth >= 5:
        new_state = 'HOT'
    elif reflexive_depth >= 30 and depth >= 1:
        new_state = 'WARM'
    else:
        new_state = 'WARM'

    registry[symbol]['state'] = new_state

    # Timestamp state change
    if new_state != prev_state:
        registry[symbol]['last_state_change'] = datetime.utcnow()
        log_model_decision(
            symbol,
            f"state_change_{prev_state}_to_{new_state}",
            registry[symbol].get("model", {}),
            registry[symbol].get("snapshot", {}),
            registry[symbol].get("flags", {})
        )