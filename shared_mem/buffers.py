# shared_mem/buffers.py
class RingBuffer:
    def __init__(self, size): self.size = size; self.buffer = []
    def append(self, item): self.buffer.append(item); self.buffer = self.buffer[-self.size:]
    def clear(self): self.buffer.clear()
    def get(self): return list(self.buffer)

class DoubleRingBuffer:
    def __init__(self, short_len=60, long_len=300):
        self.short = RingBuffer(short_len)
        self.long = RingBuffer(long_len)
    def append(self, tick): self.short.append(tick); self.long.append(tick)
    def clear(self): self.short.clear(); self.long.clear()
    def get_short(self): return self.short.get()
    def get_long(self): return self.long.get()

symbol_buffers = {}
registry = {}

def initialize_memory():
    symbol_buffers.clear()
    registry.clear()