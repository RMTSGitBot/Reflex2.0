from shared_mem.registry import registry
from shared_mem.buffers import symbol_buffers

def build_snapshot(symbol):
    buffer = symbol_buffers.get(symbol)
    quote = registry[symbol].get("quote", {})

    if not buffer or buffer.is_empty():
        return {}

    ticks = buffer.get_last_n(50)

    snapshot = {
        "last_price": ticks[-1]["price"],
        "volume": sum(t["size"] for t in ticks),
        "tick_count": len(ticks),
        "momentum": compute_momentum(ticks),
        "tape_pressure": compute_tape_pressure(ticks),
        "bid": quote.get("bid", 0),
        "ask": quote.get("ask", 0),
        "bid_size": quote.get("bid_size", 0),
        "ask_size": quote.get("ask_size", 0),
        "spread": abs(quote.get("ask", 0) - quote.get("bid", 0)),
        "quote_depth": registry[symbol].get("quote_depth", 0),
        "entry_price": registry[symbol].get("entry_price", 0),
        "prev_bar_high": registry[symbol].get("prev_bar_high", 0)
    }

    return snapshot

def compute_momentum(ticks):
    return (ticks[-1]["price"] - ticks[0]["price"]) / ticks[0]["price"] if len(ticks) >= 2 else 0

def compute_tape_pressure(ticks):
    buys = sum(1 for t in ticks if t.get("side") == "buy")
    return buys / len(ticks) if ticks else 0