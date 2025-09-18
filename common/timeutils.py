# common/timeutils.py
import os
from datetime import datetime, timedelta
from datetime import datetime, time

REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"
REPLAY_DATE_STR = os.getenv("REFLEXION_REPLAY_DATE")

def get_current_session():
    now = datetime.now().time()

    if time(4, 0) <= now < time(9, 30):
        return "premarket"
    elif time(9, 30) <= now < time(16, 0):
        return "regular"
    elif time(16, 0) <= now < time(20, 0):
        return "afterhours"
    else:
        return "closed"

def get_session_anchor():
    """
    Returns the datetime to use as 'now' for hydration/ingestion.
    In replay mode, this is the replay start date at 09:30 ET (13:30 UTC).
    In live mode, it's the current UTC time.
    """
    if REPLAY_MODE and REPLAY_DATE_STR:
        replay_date = datetime.strptime(REPLAY_DATE_STR, "%Y-%m-%d")
        return datetime(replay_date.year, replay_date.month, replay_date.day, 13, 30)
    return datetime.utcnow()

def get_date_range(days_back):
    """
    Returns (start_date, end_date) for historical loads.
    In replay mode, end_date is the replay anchor date.
    In live mode, end_date is today.
    """
    anchor = get_session_anchor()
    start = anchor - timedelta(days=days_back)
    return start.date(), anchor.date()

REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"
REPLAY_DATE_STR = os.getenv("REFLEXION_REPLAY_DATE")

def get_session_anchor():
    if REPLAY_MODE and REPLAY_DATE_STR:
        dt = datetime.strptime(REPLAY_DATE_STR, "%Y-%m-%d")
        return datetime(dt.year, dt.month, dt.day, 13, 30)
    return datetime.utcnow()

def get_date_range(days_back):
    anchor = get_session_anchor()
    start = anchor - timedelta(days=days_back)
    return start.date(), anchor.date()