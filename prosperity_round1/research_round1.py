from pathlib import Path

import pandas as pd


ROUND1_DIR = Path("/Users/neilnair/Downloads/ROUND1")
PRICE_FILES = [
    ROUND1_DIR / "prices_round_1_day_-2.csv",
    ROUND1_DIR / "prices_round_1_day_-1.csv",
    ROUND1_DIR / "prices_round_1_day_0.csv",
]
TRADE_FILES = [
    ROUND1_DIR / "trades_round_1_day_-2.csv",
    ROUND1_DIR / "trades_round_1_day_-1.csv",
    ROUND1_DIR / "trades_round_1_day_0.csv",
]


def load_frames():
    prices = pd.concat((pd.read_csv(path, sep=";") for path in PRICE_FILES), ignore_index=True)
    trades = pd.concat((pd.read_csv(path, sep=";") for path in TRADE_FILES), ignore_index=True)
    return prices, trades


def summarize_prices(prices: pd.DataFrame) -> None:
    prices = prices[prices["mid_price"] > 0].copy()

    for product in sorted(prices["product"].unique()):
        df = prices[prices["product"] == product].sort_values(["day", "timestamp"]).copy()
        spread = df["ask_price_1"] - df["bid_price_1"]
        print(f"\n=== {product} ===")
        print(
            "mid mean/std",
            round(df["mid_price"].mean(), 4),
            round(df["mid_price"].std(), 4),
            "spread mean",
            round(spread.mean(), 4),
        )
        print(
            "lag1 autocorr",
            round(df["mid_price"].autocorr(1), 4),
            "diff autocorr",
            round(df["mid_price"].diff().autocorr(1), 4),
        )
        for day in sorted(df["day"].unique()):
            dd = df[df["day"] == day]
            print(
                "day",
                day,
                "start/end",
                dd["mid_price"].iloc[0],
                dd["mid_price"].iloc[-1],
                "mean",
                round(dd["mid_price"].mean(), 4),
            )


def summarize_trades(trades: pd.DataFrame) -> None:
    print("\n=== Trades ===")
    print(trades.groupby("symbol").size().to_string())
    summary = trades.groupby("symbol").agg(
        price_mean=("price", "mean"),
        price_std=("price", "std"),
        quantity_mean=("quantity", "mean"),
    )
    print(summary.round(4).to_string())


if __name__ == "__main__":
    prices_frame, trades_frame = load_frames()
    summarize_prices(prices_frame)
    summarize_trades(trades_frame)
