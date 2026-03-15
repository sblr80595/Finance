"""
Regenerate Indian market ticker CSV files.

Run this script periodically to keep the CSV files up to date:
    python refresh_tickers.py

Files written:
    nifty50_tickers.csv      — Nifty 50 constituents
    nifty500_tickers.csv     — Nifty 500 constituents
    nifty_next50_tickers.csv — Nifty Next 50 constituents
    nse_tickers.csv          — All NSE-listed equities (EQ series)
    sensex_tickers.csv       — BSE Sensex 30 constituents
    bse_tickers.csv          — All active BSE-listed equities (scrip codes)
"""

import os
import pandas as pd
import tickers as ti

TASKS = [
    ("nifty50_tickers.csv",      "Nifty 50",       ti.tickers_nifty50),
    ("nifty500_tickers.csv",     "Nifty 500",      ti.tickers_nifty500),
    ("nifty_next50_tickers.csv", "Nifty Next 50",  ti.tickers_nifty_next50),
    ("nse_tickers.csv",          "NSE all equities", ti.tickers_nse),
    ("sensex_tickers.csv",       "Sensex 30",      ti.tickers_sensex),
    ("bse_tickers.csv",          "BSE all equities", ti.tickers_bse),
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

for filename, label, fetch_fn in TASKS:
    path = os.path.join(BASE_DIR, filename)
    print(f"Fetching {label}...", end=" ", flush=True)
    try:
        symbols = fetch_fn()
        pd.DataFrame({"ticker": symbols}).to_csv(path, index=False)
        print(f"{len(symbols)} symbols → {filename}")
    except Exception as exc:
        print(f"FAILED — {exc}")

print("\nDone.")
