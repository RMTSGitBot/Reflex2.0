# --- shared_mem/registry.py ---
from datetime import datetime
from shared_mem.buffers import DoubleRingBuffer

registry = {}

def initialize_registry(symbols):
    """
    Initializes the registry for a list of symbols.
    Each symbol gets separate trade/quote buffers, default state, and metadata.
    """
    registry.clear()

    for symbol in symbols:
        sym = symbol.upper()
        registry[sym] = {
            # Separate buffers for trades and quotes
            "buffers": {
                "trades": DoubleRingBuffer(),
                "quotes": DoubleRingBuffer()
            },
            # Snapshot and model
            "snapshot": {},
            "model": {},
            # State and timestamps
            "state": "COLD",
            "last_state_change": datetime.utcnow(),
            "last_hydrated": None,
            "last_filtered": None,
            # Market data quick access
            "quote": {},
            "quote_depth": 0,
            "last_price": None,
            "last_bar": None,
            "daily_bars_updated": False,
            # Evaluator flags
            "flags": {
                "entry_triggered": False,
                "exit_triggered": False,
                "add_count": 0
            },
            # Optional metadata for cockpit
            "description": "",
            "tags": []
        }