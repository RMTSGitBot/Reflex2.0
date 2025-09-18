import json
import os
import time
from datetime import datetime
from shared_mem.registry import registry

def load_quotes(date, symbol):
    path = f"history/{date}/{symbol}_quotes.json"
    with open(path) as f:
        return json.load(f)

def stream_quotes(symbol, quotes, speed):
    for q in quotes:
        registry[symbol]["snapshot"] = q
        time.sleep(1.0 / speed)