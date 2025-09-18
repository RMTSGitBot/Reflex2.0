import csv

def write_results(metrics, output_file):
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Symbol", "Time", "Action", "Size", "Price", "Bid", "Ask", "Spread"])
        for symbol, trades in metrics.items():
            for t in trades:
                writer.writerow([
                    symbol, t["timestamp"], t["action"], t["size"],
                    t["price"], t["bid"], t["ask"], t["spread"]
                ])