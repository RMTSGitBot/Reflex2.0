import unittest
import requests

BASE_URL = "http://localhost:5055"
SYMBOL = "AAPL"

class TestAPIHistorical(unittest.TestCase):

    def test_daily_bars_1_year(self):
        url = f"{BASE_URL}/snapshot/{SYMBOL}"
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        snapshot = r.json()
        print(f"[📊] Snapshot for {SYMBOL}: {snapshot}")

    def test_minute_bars_1_month(self):
        # Simulate hydration trigger (assumes pubsub route exists)
        url = f"{BASE_URL}/hydrate/{SYMBOL}?range=1mo&type=minute"
        r = requests.get(url)
        self.assertIn(r.status_code, [200, 202])
        print(f"[🕒] Minute hydration triggered for {SYMBOL}")

    def test_tick_data_5_days(self):
        url = f"{BASE_URL}/hydrate/{SYMBOL}?range=5d&type=tick"
        r = requests.get(url)
        self.assertIn(r.status_code, [200, 202])
        print(f"[🧵] Tick hydration triggered for {SYMBOL}")

    def test_symbol_listing(self):
        url = f"{BASE_URL}/symbols"
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        symbols = r.json()
        print(f"[📁] Loaded {len(symbols)} symbols")

    def test_flags_and_state(self):
        url = f"{BASE_URL}/flags/{SYMBOL}"
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        flags = r.json()
        print(f"[🚩] Flags for {SYMBOL}: {flags}")

if __name__ == "__main__":
    unittest.main()