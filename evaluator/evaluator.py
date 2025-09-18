# --- evaluator/evaluator.py ---
# Reflexion Evaluator: Modular, model-driven, replay-aware, cockpit-controllable

import time
import os
from shared_mem.registry import registry
from model_loader import load_model_config, validate_model_config
from filter_logic import run_model_filter
from entry_logic import run_entry_logic
from exit_logic import run_exit_logic
from add_logic import run_add_logic
from diagnostics.model_logger import log_model_decision

# Load default model
DEFAULT_MODEL = load_model_config()
validate_model_config(DEFAULT_MODEL)

# Replay mode toggle
REPLAY_MODE = os.getenv("REFLEXION_REPLAY", "false").lower() == "true"

def start_evaluator():
    print("[🧠] Evaluator loop started...")
    loop_interval = 0.2  # 5Hz scan rate

    while True:
        start = time.time()

        for symbol in list(registry.keys()):
            state = registry[symbol].get('state', 'COLD')
            snapshot = registry[symbol].get('snapshot', {})
            model = registry[symbol].get('model') or DEFAULT_MODEL
            flags = registry[symbol].setdefault('flags', {})

            # COLD → WARM transition
            if state == 'COLD':
                run_model_filter(symbol, model)
                log_model_decision(symbol, "filter_applied", model, snapshot, flags)

            # HOT state logic
            elif state == 'HOT' and snapshot:
                if snapshot.get('entry_ready') and not flags.get('entry_triggered'):
                    flags['seeking_trade'] = True
                    run_entry_logic(symbol, snapshot, model, flags)
                    log_model_decision(symbol, "entry_triggered", model, snapshot, flags)

                if flags.get('entry_triggered') and not flags.get('exit_triggered'):
                    run_exit_logic(symbol, snapshot, model, flags)
                    log_model_decision(symbol, "exit_checked", model, snapshot, flags)

                if flags.get('entry_triggered') and not flags.get('position_maxed'):
                    run_add_logic(symbol, snapshot, model, flags)
                    log_model_decision(symbol, "add_checked", model, snapshot, flags)

        time.sleep(max(0, loop_interval - (time.time() - start)))