import pandas as pd

def validate_schema(df):
    required_columns = ["timestamp", "price", "volume", "vwap", "delta"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df