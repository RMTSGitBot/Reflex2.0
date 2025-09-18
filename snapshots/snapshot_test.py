def test_momentum():
    ticks = [{"price": 100}, {"price": 105}]
    assert round((ticks[-1]["price"] - ticks[0]["price"]) / ticks[0]["price"], 4) == 0.05

def test_vwap():
    ticks = [{"price": 100, "size": 10}, {"price": 102, "size": 20}]
    total_volume = 30
    expected_vwap = (100*10 + 102*20) / total_volume
    assert round(expected_vwap, 2) == 101.33