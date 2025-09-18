from datetime import datetime, timedelta
from replay_engine.reader import load_quotes
from replay_engine.model_driver import evaluate_model
from replay_engine.simulator import simulate_fill
from replay_engine.metrics import log_trade, get_metrics, reset_metrics
from replay_engine.export import write_results

def run_single_day(config):
    date = config["date"]
    symbol_list = get_all_symbols(date)
    reset_metrics()

    for symbol in symbol_list:
        quotes = load_quotes(date, symbol)
        for snapshot in quotes:
            result = evaluate_model(symbol, snapshot, config["model"], config["broker"], config["account"])
            if result and result.get("status") == "filled":
                fill_price = result["fill_price"]
                log_trade(symbol, result["action"], result["size"], fill_price, snapshot)

    write_results(get_metrics(), config["output"])

def run_day_range(start_date, end_date, config_template):
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        config = config_template.copy()
        config["date"] = date_str
        config["output"] = f"results_{date_str}.xlsx"
        run_single_day(config)
        current += timedelta(days=1)