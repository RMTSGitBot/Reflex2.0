import unittest
from evaluator.evaluator import apply_filter

class TestEvaluator(unittest.TestCase):
    def test_numeric_filter_pass(self):
        filters = [{"field": "market_cap", "type": "numeric", "operator": "<=", "value": 500000000}]
        data = {"market_cap": 400000000}
        self.assertTrue(apply_filter("TEST", data, filters))

    def test_numeric_filter_fail(self):
        filters = [{"field": "market_cap", "type": "numeric", "operator": "<=", "value": 500000000}]
        data = {"market_cap": 600000000}
        self.assertFalse(apply_filter("TEST", data, filters))

    def test_categorical_filter_pass(self):
        filters = [{"field": "exchange", "type": "categorical", "operator": "in", "value": ["NASDAQ", "NYSE"]}]
        data = {"exchange": "NASDAQ"}
        self.assertTrue(apply_filter("TEST", data, filters))

    def test_categorical_filter_fail(self):
        filters = [{"field": "exchange", "type": "categorical", "operator": "in", "value": ["NASDAQ", "NYSE"]}]
        data = {"exchange": "OTC"}
        self.assertFalse(apply_filter("TEST", data, filters))

if __name__ == "__main__":
    unittest.main()