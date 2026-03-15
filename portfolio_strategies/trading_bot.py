"""
Broker-agnostic trading bot.

Reads ACTIVE_BROKER from config/broker_config.py and routes all
order and portfolio calls through the matching broker implementation.

Supported brokers: robinhood, dhan, fyers
Configure the active broker and credentials before running:
  - config/broker_config.py  — set ACTIVE_BROKER
  - config/dhan_config.py    — Dhan credentials (if using Dhan)
  - config/fyers_config.py   — Fyers credentials (if using Fyers)
  - config/robinhood_config.py — Robinhood credentials (if using Robinhood)

For Fyers, generate a fresh token first:
  python brokers/fyers_auth.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from brokers import get_broker
from config.broker_config import ACTIVE_BROKER, DEFAULT_QUANTITY

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

# ── Initialise broker ──────────────────────────────────────────────────────────
print(f"Using broker: {ACTIVE_BROKER}")
broker = get_broker()
broker.login()

# ── Fetch holdings ─────────────────────────────────────────────────────────────
df = broker.get_holdings()
print(f"\nPortfolio ({len(df)} positions):")
print(df)

# ── Buy / sell criteria ────────────────────────────────────────────────────────
# Adjust these thresholds to match your strategy.
buy_criteria = (
    (df["average_buy_price"] <= 25.00)
    & (df["quantity"] == 1.00)
    & (df["percent_change"] <= -0.50)
)
sell_criteria = (
    (df["quantity"] == 5.00)
    & (df["percent_change"] >= 0.50)
)

df_buy = df[buy_criteria]
df_sell = df[sell_criteria]

print(f"\nStocks to buy ({len(df_buy)}):")
print(df_buy)
print(f"\nStocks to sell ({len(df_sell)}):")
print(df_sell)

# ── Cancel open orders ─────────────────────────────────────────────────────────
open_orders = broker.get_open_orders()
print(f"\n{len(open_orders)} open order(s) — cancelling all.")
broker.cancel_all_orders()

# ── Execute sells ──────────────────────────────────────────────────────────────
if df_sell.empty:
    print("\nNothing to sell right now.")
else:
    for _, row in df_sell.iterrows():
        response = broker.sell_market(
            ticker=row["ticker"],
            quantity=DEFAULT_QUANTITY,
            security_id=row["security_id"],
        )
        print(f"SELL {row['ticker']}: {response}")

# ── Execute buys ───────────────────────────────────────────────────────────────
if df_buy.empty:
    print("\nNothing to buy right now.")
else:
    for _, row in df_buy.iterrows():
        response = broker.buy_market(
            ticker=row["ticker"],
            quantity=DEFAULT_QUANTITY,
            security_id=row["security_id"],
        )
        print(f"BUY {row['ticker']}: {response}")
