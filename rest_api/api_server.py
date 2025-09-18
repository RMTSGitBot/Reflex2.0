from flask import Flask, jsonify, request
from shared_mem.registry import registry
from diagnostics.model_logger import get_recent_events
from pubsub.event_bus import publish_event
from datetime import datetime

app = Flask(__name__)

@app.route("/symbols", methods=["GET"])
def get_symbols():
    """
    Returns state table for all symbols in registry.
    """
    data = []
    now = datetime.utcnow()
    for sym, info in registry.items():
        state = info.get("state", "COLD")
        last_change = info.get("last_state_change")
        time_in_state = None
        if last_change:
            delta = now - last_change
            time_in_state = str(delta).split(".")[0]  # HH:MM:SS

        snapshot = info.get("snapshot", {})
        data.append({
            "symbol": sym,
            "state": state,
            "time_in_state": time_in_state,
            "volatility": snapshot.get("volatility"),
            "volume": snapshot.get("volume"),
            "momentum": snapshot.get("momentum"),
            "filter_status": snapshot.get("filter_pass"),
            "last_price": info.get("last_price"),
            "last_update": snapshot.get("timestamp")
        })
    return jsonify(data)

@app.route("/buffers", methods=["GET"])
def get_buffers():
    """
    Returns buffer stats for all symbols.
    """
    data = {}
    for sym, info in registry.items():
        trades_stats = info["buffers"]["trades"].stats()
        quotes_stats = info["buffers"]["quotes"].stats()
        data[sym] = {
            "trades_short": trades_stats,
            "quotes_short": quotes_stats
        }
    return jsonify(data)

@app.route("/events", methods=["GET"])
def get_events():
    """
    Returns recent model/evaluator events.
    """
    limit = int(request.args.get("limit", 50))
    events = get_recent_events(limit=limit)
    return jsonify(events)

@app.route("/command", methods=["POST"])
def send_command():
    """
    Publishes a cockpit command into the event bus.
    """
    payload = request.json
    event_type = payload.get("type")
    symbol = payload.get("symbol")
    data = payload.get("payload", {})
    publish_event(event_type, symbol=symbol, payload=data, source="cockpit")
    return jsonify({"status": "ok", "event": event_type, "symbol": symbol})

@app.route("/heartbeat", methods=["GET"])
def get_heartbeat():
    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "status": "alive"
    })
    
@app.route("/model_status", methods=["GET"])
def get_model_status():
    symbol = request.args.get("symbol")
    model = registry[symbol]["model"]
    snapshot = registry[symbol]["snapshot"]
    return jsonify({
        "model": model,
        "snapshot": snapshot
    })  
  
@app.route("/trade_signals", methods=["GET"])
def get_trade_signals():
    # Return live evaluator triggers
    ...

@app.route("/trade_log", methods=["GET"])
def get_trade_log():
    # Return executed trades
    ...

    
@app.route("/symbols", methods=["GET"])
def get_symbols():
    # Returns registry state + snapshot metrics
    ...

@app.route("/buffers", methods=["GET"])
def get_buffers():
    # Returns buffer stats
    ...

@app.route("/events", methods=["GET"])
def get_events():
    # Returns recent evaluator/model events
    ...

@app.route("/heartbeat", methods=["GET"])
def get_heartbeat():
    return jsonify({"status": "alive", "timestamp": datetime.utcnow().isoformat()})

@app.route("/command", methods=["POST"])
def send_command():
    # Accepts replay speed, date, manual overrides
    ...
    
@app.route("/model_status", methods=["GET"])
def get_model_status():
    symbol = request.args.get("symbol")
    model = registry[symbol]["model"]
    snapshot = registry[symbol]["snapshot"]
    return jsonify({"model": model, "snapshot": snapshot})

@app.route("/trade_signals", methods=["GET"])
def get_trade_signals():
    # Return list of live evaluator triggers
    ...

@app.route("/trade_log", methods=["GET"])
def get_trade_log():
    # Return list of executed trades
    ...