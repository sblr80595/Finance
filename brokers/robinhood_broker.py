import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import robin_stocks as r

from brokers.base_broker import BaseBroker
from config.robinhood_config import USERNAME, PASSWORD, MFA_CODE


class RobinhoodBroker(BaseBroker):
    """Robinhood broker implementation using robin_stocks."""

    def login(self) -> None:
        kwargs = {}
        if MFA_CODE:
            kwargs["mfa_code"] = MFA_CODE
        r.login(USERNAME, PASSWORD, **kwargs)
        print("Logged in to Robinhood.")

    def get_holdings(self) -> pd.DataFrame:
        raw = r.build_holdings()
        df = pd.DataFrame(raw).T
        df["ticker"] = df.index
        df = df.reset_index(drop=True)

        numeric_cols = df.columns.drop(["id", "type", "name", "pe_ratio", "ticker"], errors="ignore")
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        # Robinhood already returns average_buy_price and percent_change fields.
        # Add security_id as an alias for ticker (Robinhood doesn't use numeric IDs).
        df["security_id"] = df["ticker"]
        df["current_price"] = pd.to_numeric(df.get("last_trade_price", df.get("equity_price", None)), errors="coerce")

        # percent_change in Robinhood holdings is a fraction (e.g. 0.05 = 5%)
        # Rename for consistency with our schema
        if "percent_change" not in df.columns and "average_buy_price" in df.columns:
            df["percent_change"] = (df["current_price"] - df["average_buy_price"]) / df["average_buy_price"]

        return df[["ticker", "security_id", "quantity", "average_buy_price", "current_price", "percent_change"]]

    def get_open_orders(self) -> list:
        return r.orders.get_all_open_orders()

    def cancel_all_orders(self) -> None:
        r.orders.cancel_all_open_orders()

    def buy_market(self, ticker: str, quantity: int, security_id: str = "") -> dict:
        return r.orders.order_buy_market(ticker, quantity, timeInForce="gfd")

    def sell_market(self, ticker: str, quantity: int, security_id: str = "") -> dict:
        return r.orders.order_sell_market(ticker, quantity, timeInForce="gfd")
