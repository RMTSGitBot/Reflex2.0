import pandas as pd
from polygon import RESTClient
from common.config import POLYGON_API

client = RESTClient(POLYGON_API["API_KEY"])

def fetch_daily_bars(symbol, start_date, end_date):
    """
    Fetch daily OHLCV bars for a symbol between start_date and end_date.
    Returns a DataFrame with timestamp, open, high, low, close, volume.
    """
    try:
        aggs = client.get_aggs(
            symbol=symbol,
            multiplier=1,
            timespan="day",
            from_=start_date,
            to=end_date,
            limit=5000
        )
        rows = [{
            "timestamp": pd.to_datetime(bar.timestamp, unit='ms'),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        } for bar in aggs]
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"[❌] Failed to fetch daily bars for {symbol}: {e}")
        return pd.DataFrame()

def fetch_minute_bars(symbol, start_date, end_date):
    """
    Fetch minute OHLCV bars for a symbol between start_date and end_date.
    Returns a DataFrame with timestamp, open, high, low, close, volume.
    """
    try:
        aggs = client.get_aggs(
            symbol=symbol,
            multiplier=1,
            timespan="minute",
            from_=start_date,
            to=end_date,
            limit=50000
        )
        rows = [{
            "timestamp": pd.to_datetime(bar.timestamp, unit='ms'),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        } for bar in aggs]
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"[❌] Failed to fetch minute bars for {symbol}: {e}")
        return pd.DataFrame()

def fetch_ticks(symbol, start_date, end_date):
    """
    Polygon does not expose raw tick data via REST.
    For hydration purposes, we simulate ticks using minute bars.
    Returns a DataFrame with timestamp, price, size.
    """
    df = fetch_minute_bars(symbol, start_date, end_date)
    if df.empty:
        return pd.DataFrame()
    ticks = []
    for _, row in df.iterrows():
        ticks.append({
            "timestamp": row["timestamp"],
            "price": row["close"],
            "size": row["volume"]
        })
    return pd.DataFrame(ticks)

def fetch_quotes(symbol, start_date, end_date):
    """
    Polygon does not expose historical quotes via REST.
    This function returns an empty DataFrame for now.
    Quotes must be streamed live via WebSocket.
    """
    return pd.DataFrame()