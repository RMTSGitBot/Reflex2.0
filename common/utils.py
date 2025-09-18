import os
import sys
from datetime import datetime, time, timezone
from typing import Union, Optional
import pytz
import pandas as pd
from dateutil.parser import parse
from common.app_logging import setup_logger

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Constants ---
EASTERN = pytz.timezone("US/Eastern")

# --- Logger ---
log = setup_logger("utils", level="INFO")

# === Datetime Normalization ===

def normalize_datetime(
    raw: Union[str, datetime],
    is_start: bool = True,
    start_time: Optional[time] = None,
    end_time: Optional[time] = None
) -> Optional[datetime]:
    """
    Normalize a date or datetime string to Eastern timezone.
    Applies default start/end times if time component is missing.
    """
    try:
        dt = raw if isinstance(raw, datetime) else parse(raw)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        dt = dt.astimezone(EASTERN)

        if dt.time() == time(0, 0):
            override = start_time if is_start else end_time
            dt = dt.replace(
                hour=override.hour if override else (0 if is_start else 23),
                minute=override.minute if override else (0 if is_start else 59),
                second=override.second if override else (0 if is_start else 59),
                microsecond=0 if is_start else 999999
            )

        return dt

    except Exception as e:
        log.warning(f"[⚠️] Failed to normalize datetime: {raw} ({e})")
        return None

def normalize_daily_timestamp(ts: Union[datetime, pd.Timestamp]) -> datetime:
    """
    Normalize timestamp to UTC. Supports both datetime and pandas Timestamp.
    """
    if isinstance(ts, pd.Timestamp):
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
    elif isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)