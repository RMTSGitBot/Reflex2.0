# --- Reflexion Trade Queue ---
# Purpose: Shared memory queue for evaluator → trader signaling

from queue import Queue

trade_queue = Queue()