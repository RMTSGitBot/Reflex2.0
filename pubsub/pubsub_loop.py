# pubsub/pubsub_loop.py
import os
from pubsub.event_bus import listen_for_events
from ingestion.cold_hydration import hydrate_symbol
from shared_mem.registry import registry
from diagnostics.model_logger import log_model_decision

REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"

def send_to_cockpit(message_type, payload):
    """
    Placeholder for pushing updates back to the cockpit UI.
    Replace with WebSocket emit, REST POST, etc.
    """
    print(f"[📤] Cockpit update: {message_type} -> {payload}")

def start_pubsub_loop():
    """
    Listens for cockpit/replay events and applies them to the registry or triggers actions.
    """
    print("[📢] PubSub loop started...")
    for event in listen_for_events():
        try:
            event_type = event.get("type")
            symbol = event.get("symbol")
            payload = event.get("payload", {})

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
                    hydrate_symbol(symbol, payload.get("date"))
                    send_to_cockpit("hydrated", {"symbol": symbol})

            elif event_type == "set_state":
                if symbol in registry:
                    new_state = payload.get("state")
                    prev_state = registry[symbol]["state"]
                    registry[symbol]["state"] = new_state
                    print(f"[🛠️] {symbol} state changed {prev_state} -> {new_state} via PubSub")
                    send_to_cockpit("state_change", {"symbol": symbol, "state": new_state})

            elif event_type == "override_model":
                if symbol in registry:
                    registry[symbol]["model"] = payload.get("model", {})
                    registry[symbol]["flags"] = {}
                    print(f"[🧠] Model override applied to {symbol} via PubSub")
                    send_to_cockpit("model_override", {"symbol": symbol, "model": registry[symbol]["model"]})

            elif event_type == "manual_trade":
                print(f"[✋] Manual trade event for {symbol}: {payload.get('action')}")
                send_to_cockpit("manual_trade", {"symbol": symbol, "action": payload.get("action")})

            elif event_type != "noop":
                print(f"[⚠️] Unknown event type: {event_type}")

        except Exception as e:
            print(f"[❌] Error processing event {event}: {e}")