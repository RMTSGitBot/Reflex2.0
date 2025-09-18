import queue
import threading
import time
import os
from datetime import datetime
from diagnostics.model_logger import log_model_decision
from shared_mem.registry import registry

# Thread-safe event queue
_event_queue = queue.Queue()

# Replay mode awareness
REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"

def publish_event(event_type, symbol=None, payload=None):
    """Publish an event into the bus."""
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": event_type,
        "symbol": symbol,
        "payload": payload or {}
    }
    _event_queue.put(event)

    # Log for diagnostics
    log_model_decision(
        symbol or "N/A",
        f"event_published_{event_type}",
        registry.get(symbol, {}).get("model", {}),
        registry.get(symbol, {}).get("snapshot", {}),
        registry.get(symbol, {}).get("flags", {})
    )

def listen_for_events():
    """Generator that yields events as they arrive."""
    while True:
        try:
            event = _event_queue.get(timeout=1)
            yield event
        except queue.Empty:
            # No events — yield a noop to keep loops alive
            yield {"type": "noop", "timestamp": datetime.utcnow().isoformat()}