import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import pandas_market_calendars as mcal
from common.config import POLYGON_API
from diagnostics.model_logger import log_model_decision
from shared_mem.registry import registry

REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"

def get_last_market_day(reference_date=None):
    if reference_date is None:
        reference_date = datetime.utcnow().date()
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(
        start_date=reference_date - timedelta(days=7),
        end_date=reference_date
    )
    last_open = schedule.index[-1].date()
    return last_open.strftime("%Y-%m-%d")

def fetch_daily_bars(symbol, date=None):
    if date is None:
        date = get_last_market_day()

    now = datetime.utcnow()
    if date == now.strftime("%Y-%m-%d") and now.hour < 21:
        print(f"[⏳] Skipping daily bar fetch for {symbol}—market still open")
        return None

    if REPLAY_MODE:
        # In replay, load from local historical store
        path = f"replay_data/daily/{symbol}_{date}.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            _log_fetch(symbol, "daily_bar_replay")
            return df
        else:
            print(f"[⚠️] No replay daily bar file for {symbol} on {date}")
            return None

    url = f"{POLYGON_API['BASE_URL']}/v1/open-close/{symbol}/{date}?apiKey={POLYGON_API['API_KEY']}"
    r = requests.get(url, timeout=POLYGON_API['TIMEOUT'])

    if r.status_code != 200:
        print(f"[⚠️] Polygon API error for {symbol} on {date}: {r.status_code}")
        return None

    data = r.json()
    required_keys = ["open", "close", "volume"]
    if not all(k in data for k in required_keys):
        print(f"[⚠️] Missing keys in daily bar data for {symbol} on {date}")
        return None

    df = pd.DataFrame([{
        "symbol": symbol,
        "date": date,
        "open": data["open"],
        "close": data["close"],
        "volume": data["volume"]
    }])
    _log_fetch(symbol, "daily_bar_live")
    return df

def fetch_minute_bars(symbol, date):
    if REPLAY_MODE:
        path = f"replay_data/minute/{symbol}_{date}.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            _log_fetch(symbol, "minute_bar_replay")
            return df
        else:
            print(f"[⚠️] No replay minute bar file for {symbol} on {date}")
            return pd.DataFrame()

    url = f"{POLYGON_API['BASE_URL']}/v2/aggs/ticker/{symbol}/range/1/minute/{date}/{date}?apiKey={POLYGON_API['API_KEY']}"
    r = requests.get(url, timeout=POLYGON_API['TIMEOUT'])
    if r.status_code != 200:
        print(f"[⚠️] Polygon API error for minute bars {symbol} on {date}: {r.status_code}")
        return pd.DataFrame()

    data = r.json().get("results", [])
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "symbol": symbol,
        "timestamp": datetime.utcfromtimestamp(bar["t"]/1000),
        "open": bar["o"],
        "high": bar["h"],
        "low": bar["l"],
        "close": bar["c"],
        "volume": bar["v"]
    } for bar in data])
    _log_fetch(symbol, "minute_bar_live")
    return df

def fetch_ticks(symbol, date):
    if REPLAY_MODE:
        path = f"replay_data/ticks/{symbol}_{date}.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            _log_fetch(symbol, "ticks_replay")
            return df
        else:
            print(f"[⚠️] No replay tick file for {symbol} on {date}")
            return pd.DataFrame()

    url = f"{POLYGON_API['BASE_URL']}/v3/trades/{symbol}?timestamp.gte={date}T09:30:00Z&timestamp.lte={date}T16:00:00Z&limit=50000&apiKey={POLYGON_API['API_KEY']}"
    r = requests.get(url, timeout=POLYGON_API['TIMEOUT'])
    if r.status_code != 200:
        print(f"[⚠️] Polygon API error for ticks {symbol} on {date}: {r.status_code}")
        return pd.DataFrame()

    data = r.json().get("results", [])
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "timestamp": t["sip_timestamp"],
        "price": t["price"],
        "size": t["size"],
        "side": "buy" if t.get("conditions", [""])[0] in ("@", "T") else "sell"
    } for t in data])
    _log_fetch(symbol, "ticks_live")
    return df

def _log_fetch(symbol, action):
    log_model_decision(
        symbol,
        action,
        registry.get(symbol, {}).get("model", {}),
        registry.get(symbol, {}).get("snapshot", {}),
        registry.get(symbol, {}).get("flags", {})
    )