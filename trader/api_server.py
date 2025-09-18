from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
import os
from common.timeutils import get_current_session
from shared_mem.registry import registry
from common.config import DB_PARAMS, REPLAY_CONFIG, BROKER_CONFIG, API_KEYS

app = Flask(__name__, static_folder="trader/static")

# --- Static cockpit panels ---
@app.route("/")
def home():
    return send_from_directory(app.static_folder, "cockpit_home.html")

@app.route("/<path:filename>")
def static_file(filename):
    return send_from_directory(app.static_folder, filename)

# --- System heartbeat ---
@app.route("/heartbeat", methods=["GET"])
def get_heartbeat():
    return jsonify({
        "session": get_current_session(),
        "symbol_count": len(registry),
        "timestamp": datetime.utcnow().isoformat()
    })

# --- Symbol registry ---
@app.route("/symbols", methods=["GET"])
def get_symbols():
    return jsonify([{"symbol": s} for s in registry.keys()])

# --- Model status / intent viewer ---
@app.route("/model_status", methods=["GET"])
def get_model_status():
    symbol = request.args.get("symbol")
    model = registry[symbol]["model"]
    snapshot = registry[symbol]["snapshot"]
    return jsonify({"model": model, "snapshot": snapshot})

# --- Trade execution ---
@app.route("/command", methods=["POST"])
def handle_command():
    from trader.execute import handle_trade
    data = request.get_json()
    if data.get("type") == "manual_trade":
        return jsonify(handle_trade(
            data["symbol"],
            data["payload"]["action"],
            data["payload"]["size"],
            data["payload"]["price"],
            data["payload"]["broker"],
            data["payload"]["account"],
            data["payload"].get("order_type", "limit"),
            data["payload"].get("tif", "DAY")
        ))
    return jsonify({"status": "error", "message": "Unknown command type"})

# --- Portfolio and orders ---
@app.route("/portfolio_status", methods=["GET"])
def get_portfolio_status():
    from trader.portfolio import get_portfolio
    return jsonify(get_portfolio())

@app.route("/live_orders", methods=["GET"])
def get_live_orders():
    from trader.orders import get_live_orders
    return jsonify(get_live_orders())

@app.route("/trade_log", methods=["GET"])
def get_trade_log():
    from trader.trace import get_trade_log
    return jsonify(get_trade_log())

# --- Emergency stop ---
@app.route("/emergency_trigger", methods=["POST"])
def trigger_emergency():
    from trader.emergency import emergency_liquidate
    result = emergency_liquidate()
    return jsonify({"status": "triggered", "result": result})

# --- Market conditions ---
@app.route("/market_conditions", methods=["GET"])
def get_market_conditions():
    from diagnostics.market_monitor import get_conditions
    return jsonify(get_conditions())

# --- Risk status (optional) ---
@app.route("/risk_status", methods=["GET"])
def get_risk_status():
    broker = request.args.get("broker")
    account = request.args.get("account")
    from trader.risk import get_risk_status
    return jsonify(get_risk_status(broker, account))

# --- Replay engine: single or multi-day ---
@app.route("/launch_replay", methods=["POST"])
def launch_replay():
    import json
    from replay_engine.runner import run_single_day, run_day_range
    config = request.get_json()
    mode = config.get("mode", "single")

    if mode == "range":
        start = config["start_date"]
        end = config["end_date"]
        config_template = {k: v for k, v in config.items() if k not in ["start_date", "end_date", "mode"]}
        run_day_range(start, end, config_template)
    else:
        with open("replay_engine/config.json", "w") as f:
            json.dump(config, f)
        run_single_day(config)

    return jsonify({"status": "completed"})

@app.route("/replay_metrics", methods=["GET"])
def get_replay_metrics():
    from replay_engine.metrics import get_metrics
    return jsonify(get_metrics())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)