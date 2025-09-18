import requests
import pandas as pd
import pytz
from dateutil import parser
from decimal import Decimal
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from datetime import datetime, time as dt_time, date, timezone
from typing import Union, Optional
from common.app_logging import setup_logger
from common.config import POLYGON_API_KEY

log = setup_logger(__name__, level="INFO")
eastern = pytz.timezone("US/Eastern")

def poly_fetch_fundamentals(symbol: str) -> pd.DataFrame:
    url = f"https://api.polygon.io/v3/reference/tickers/{symbol}"
    params = {
        "apiKey": POLYGON_API_KEY
    }

    log.info(f"[🌐] Fetching fundamentals for {symbol} from Polygon API")
    log.debug(f"[🔗] URL: {url} | Params: {params}")

    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()

        results = data.get("results")
        if not isinstance(results, dict):
            log.warning(f"[⚠️] Unexpected format for fundamentals: {type(results)}")
            return pd.DataFrame()

        log.info(f"[📥] Polygon raw results for {symbol}: {results}")

        fund_dict = {
            "symbol": symbol.upper(),
            "company": results.get("name", "N/A"),
            "sector": results.get("sector", "N/A"),
            "industry": results.get("industry", "N/A"),
            "country": results.get("locale", "N/A").title(),
            "exchange": results.get("primary_exchange", "N/A"),
            "market_cap": results.get("market_cap"),
            "pe_ratio": results.get("weighted_unified_pe"),
            "shares_float": results.get("share_class_shares_outstanding"),
            "float_percent": None,  # Placeholder — enrich later if needed
            "insider_transactions": None,
            "short_float": None,
            "average_true_range": None,
            "last_updated": pd.Timestamp.now(tz="UTC")  # Reflect API fetch time
        }

        df = pd.DataFrame([fund_dict])
        df = sanitize_numeric_fields(df, numeric_fields)
        return df

    except Exception as e:
        log.error(f"[❌] Polygon fundamentals fetch failed for {symbol}: {e}")
        return pd.DataFrame()


def poly_fetch_symbols():
    url = "https://api.polygon.io/v3/reference/tickers"
    params = {
        "active": "true",
        "sort": "ticker",
        "order": "asc",
        "limit": 1000,
        "apiKey": POLYGON_API_KEY
    }
    symbols = []
    try:
        while True:
            r = requests.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            if not results:
                break
            symbols.extend([item['ticker'] for item in results])
            next_url = data.get("next_url")
            if not next_url:
                break
            url = next_url
    except Exception as e:
        log.error(f"[ERROR] fetch_symbols failed: {e}")
    return symbols

def fetch_quote_history(symbol):
    url = f"https://api.polygon.io/v3/quotes/{symbol}?limit=500&apiKey={POLYGON_API_KEY}"
    resp = requests.get(url)
    data = resp.json().get("results", [])
    return [{
        "bid": q.get("bid_price", 0.0),
        "ask": q.get("ask_price", 0.0),
        "spread": round(q.get("ask_price", 0.0) - q.get("bid_price", 0.0), 4),
        "timestamp": q.get("sip_timestamp")
    } for q in data]
    
# === Time Utilities ===

def to_unix_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)

def to_unix_ns(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1e9)

def convert_to_utc_unix(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    dt = dt.replace(second=0, microsecond=0)
    return int(dt.timestamp())

def normalize_datetime(
    raw: Union[str, datetime, date],
    is_start: bool = True,
    start_time: Optional[dt_time] = None,
    end_time: Optional[dt_time] = None
) -> Optional[datetime]:
    try:
        if isinstance(raw, str):
            dt = parser.parse(raw, fuzzy=True)
        elif isinstance(raw, (datetime, date)):
            dt = raw if isinstance(raw, datetime) else datetime.combine(raw, dt_time.min)
        else:
            raise TypeError("Unsupported input type for datetime normalization")

        if dt.time() == dt_time(0, 0):
            override = start_time if is_start else end_time
            dt = dt.replace(
                hour=override.hour if override else (0 if is_start else 23),
                minute=override.minute if override else (1 if is_start else 59),
                second=override.second if override else (0 if is_start else 59)
            )

        if dt.tzinfo is None:
            dt = eastern.localize(dt)
        else:
            dt = dt.astimezone(eastern)

        return dt

    except Exception as e:
        log.error(f"[❌] Failed to normalize datetime '{raw}': {e}")
        return None

# === Polygon API Utilities ===

def attach_api_key_to_next_url(next_url: str, api_key: str) -> str:
    parsed = urlparse(next_url)
    query = parse_qs(parsed.query)
    query["apiKey"] = [api_key]
    rebuilt_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=rebuilt_query))

def fetch_safe_start_date(symbol: str) -> Optional[str]:
    url = f"https://api.polygon.io/v1/meta/symbols/{symbol}/company"
    params = {"apiKey": POLYGON_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        return data.get("listdate") or data.get("start_date")
    except Exception as e:
        log.warning(f"[❌] Metadata fetch failed for {symbol}: {e}")
        return None

# === Data Fetchers ===

def poly_fetch_daily_bars(symbol: str, from_dt: datetime, to_dt: datetime) -> pd.DataFrame:
    safe_start = fetch_safe_start_date(symbol)
    if safe_start:
        safe_dt = datetime.strptime(safe_start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        from_dt = max(from_dt, safe_dt)

    from_ts = to_unix_ms(from_dt)
    to_ts = to_unix_ms(to_dt)
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{from_ts}/{to_ts}"
    params = {
        "adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": POLYGON_API_KEY
    }

    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        bars = data.get("results", [])
        if not bars:
            return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(bars).rename(columns={
            't': 'timestamp', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df['symbol'] = symbol.upper()
        return df[["symbol", "timestamp", "open", "high", "low", "close", "volume"]]

    except Exception as e:
        log.error(f"[❌] Daily bar fetch failed for {symbol}: {e}")
        return pd.DataFrame(columns=["symbol", "timestamp", "open", "high", "low", "close", "volume"])

def poly_fetch_minute_bars(symbol: str, from_dt: datetime, to_dt: datetime) -> pd.DataFrame:
    from_ts = to_unix_ms(from_dt)
    to_ts = to_unix_ms(to_dt)
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/{from_ts}/{to_ts}"
    params = {
        "adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": POLYGON_API_KEY
    }

    expected = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']

    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        bars = data.get("results", [])
        if not bars:
            return pd.DataFrame(columns=expected)

        df = pd.DataFrame(bars).rename(columns={
            't': 'timestamp', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df['symbol'] = symbol.upper()
        return df[expected]

    except Exception as e:
        log.error(f"[❌] Minute bar fetch failed for {symbol}: {e}")
        return pd.DataFrame(columns=expected)

def poly_fetch_ticks(symbol: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    from_ts = to_unix_ns(start_dt)
    to_ts = to_unix_ns(end_dt)
    url = f"https://api.polygon.io/v3/trades/{symbol.upper()}"
    params = {
        "timestamp.gte": from_ts,
        "timestamp.lt": to_ts,
        "limit": 50000,
        "order": "asc",
        "apiKey": POLYGON_API_KEY
    }

    expected = [
        "symbol", "timestamp", "sip_timestamp", "price", "size",
        "exchange", "conditions", "tape", "participant_id", "is_trade_through"
    ]

    all_rows = []
    next_url = url

    while next_url:
        try:
            r = requests.get(next_url, params=params if next_url == url else None)
            r.raise_for_status()
            data = r.json()
            trades = data.get("results", [])
            if not trades:
                break

            for trade in trades:
                all_rows.append({
                    "symbol": symbol.upper(),
                    "timestamp": pd.to_datetime(trade.get("participant_timestamp"), unit="ns", utc=True),
                    "sip_timestamp": int(trade.get("sip_timestamp", 0)),
                    "price": trade.get("price"),
                    "size": trade.get("size"),
                    "exchange": trade.get("exchange"),
                    "conditions": trade.get("conditions", []),
                    "tape": trade.get("tape"),
                    "participant_id": trade.get("participant_id"),
                    "is_trade_through": trade.get("trade_through_exempt", False)
                })

            next_url = data.get("next_url")
            if next_url:
                next_url = attach_api_key_to_next_url(next_url, POLYGON_API_KEY)
                params = None

        except Exception as e:
            log.error(f"[❌] Tick fetch failed for {symbol}: {e}")
            break

    if not all_rows:
        return pd.DataFrame(columns=expected)

    df = pd.DataFrame(all_rows)
    df.sort_values("timestamp", inplace=True)
    return df[expected]

# === Fundamentals ===

numeric_fields = [
    "market_cap", "pe_ratio", "shares_float", "float_percent",
    "insider_transactions", "short_float", "average_true_range"
]

def sanitize_numeric_fields(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return