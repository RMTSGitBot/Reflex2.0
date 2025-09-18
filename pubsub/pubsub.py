import time
import os
from pubsub.event_bus import listen_for_events
from ingestion.cold_hydration import hydrate_symbol
from diagnostics.model_logger import log_model_decision
from shared_mem.registry import registry

REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"

def start_pubsub_loop():
    print("[📢] PubSub loop started...")
    for event in listen_for_events():
        try:
            event_type = event.get("type")
            symbol = event.get("symbol")
            timestamp = event.get("timestamp", time.time())

            # Log every event for diagnostics
            log_model_decision(
                symbol or "N/A",
                f"pubsub_event_{event_type}",
                registry.get(symbol, {}).get("model", {}),
                registry.get(symbol, {}).get("snapshot", {}),
                registry.get(symbol, {}).get("flags", {})
            )

            if event_type == "hydrate":
                if REPLAY_MODE:
                    print(f"[⏪] Replay mode: ignoring hydrate event for {symbol}")
                else:
                    print(f"[💾] Hydrating {symbol} from event bus...")
                    hydrate_symbol(symbol, event.get("date"))

            elif event_type == "set_state":
                if symbol in registry:
                    new_state = event.get("state")
                    registry[symbol]["state"] = new_state
                    print(f"[🛠️] {symbol} state set to {new_state} via PubSub")

            elif event_type == "override_model":
                if symbol in registry:
                    registry[symbol]["model"] = event.get("model")
                    registry[symbol]["flags"] = {}
                    print(f"[🧠] Model override applied to {symbol} via PubSub")

            elif event_type == "manual_trade":
                # Placeholder for cockpit-triggered manual trade
                print(f"[✋] Manual trade event received for {symbol}: {event.get('action')}")

            else:
                print(f"[⚠️] Unknown event type: {event_type}")

        except Exception as e:
            print(f"[❌] Error processing event {event}: {e}")

        time.sleep(1)