from shared_mem.buffers import symbol_buffers
import pandas as pd

def compute_volatility(symbol, lookback=20):
    """
    Computes volatility as the standard deviation of returns over the last N ticks.
    Scaled by sqrt(N) to approximate annualized volatility for short-term data.
    """
    buffer = symbol_buffers.get(symbol, {}).get("trades")
    if not buffer or buffer.is_empty():
        return 0.0

    ticks = buffer.get_last_n(lookback)
    prices = [t["price"] for t in ticks]
    if len(prices) < 2:
        return 0.0

    returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    if not returns:
        return 0.0

    return float(pd.Series(returns).std() * (len(returns) ** 0.5))
def compute_vwap(symbol):
    buffer = symbol_buffers.get(symbol)
    ticks = buffer.get_last_n(50) if buffer else []
    total_volume = sum(t["size"] for t in ticks)
    return sum(t["price"] * t["size"] for t in ticks) / total_volume if total_volume else 0

def compute_atr(symbol):
    buffer = symbol_buffers.get(symbol)
    ticks = buffer.get_last_n(14) if buffer else []
    ranges = [abs(t["high"] - t["low"]) for t in ticks if "high" in t and "low" in t]
    return sum(ranges) / len(ranges) if ranges else 0

def compute_rsi(symbol):
    buffer = symbol_buffers.get(symbol)
    ticks = buffer.get_last_n(14) if buffer else []
    gains = [t["price"] - ticks[i-1]["price"] for i, t in enumerate(ticks[1:], 1) if t["price"] > ticks[i-1]["price"]]
    losses = [ticks[i-1]["price"] - t["price"] for i, t in enumerate(ticks[1:], 1) if t["price"] < ticks[i-1]["price"]]
    avg_gain = sum(gains) / len(gains) if gains else 0.01
    avg_loss = sum(losses) / len(losses) if losses else 0.01
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))