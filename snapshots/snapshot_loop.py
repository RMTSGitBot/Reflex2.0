import time
from shared_mem.registry import registry
from snapshots.snapshot_builder import build_snapshot
from snapshots.snapshot_fields import enrich_snapshot
from snapshots.snapshot_logger import log_snapshot

def start_snapshot_loop():
    print("[🖼️] Snapshot loop started...")
    interval = 0.5

    while True:
        start = time.time()
        for symbol in list(registry.keys()):
            snapshot = build_snapshot(symbol)
            enriched = enrich_snapshot(symbol, snapshot)
            registry[symbol]["snapshot"] = enriched
            log_snapshot(symbol, enriched)
        time.sleep(max(0, interval - (time.time() - start)))