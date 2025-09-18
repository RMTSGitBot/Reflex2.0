# dbmanager/precalc_engine.py

def run_precalc(df):
    df["volatility_score"] = df["average_true_range"] / df["market_cap"]
    df["risk_flag"] = df["volatility_score"] > 0.00001
    return df