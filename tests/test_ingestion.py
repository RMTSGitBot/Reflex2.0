import unittest
from ingestion.bar_builder import build_minute_bar
from shared_mem.buffers import DoubleRingBuffer, symbol_buffers
from shared_mem.registry import registry

class TestIngestion(unittest.TestCase):
    def setUp(self):
        symbol = "TEST"
        buf = DoubleRingBuffer()
        for i in range(5):
            buf.append({"price": i, "size": 10, "timestamp": f"2025-08-27T09:30:{i:02d}"})
        symbol_buffers[symbol] = buf  # ✅ This line initializes the buffer
        registry[symbol] = {"buffer": buf}

    def test_minute_bar_build(self):
        bar = build_minute_bar("TEST")
        self.assertEqual(bar["open"], 0)
        self.assertEqual(bar["close"], 4)
        self.assertEqual(bar["volume"], 50)

if __name__ == "__main__":
    unittest.main()