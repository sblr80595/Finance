import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd

from brokers.base_broker import BaseBroker
from brokers.fyers_auth import connect_to_fyers
from config.fyers_config import (
    DEFAULT_EXCHANGE,
    DEFAULT_ORDER_TYPE,
    DEFAULT_PRODUCT_TYPE,
    DEFAULT_VALIDITY,
)


class FyersBroker(BaseBroker):
    """
    Fyers broker implementation using fyers-apiv3.

    Authentication is handled automatically via TOTP on every call to login().
    No manual token generation is required — credentials are read from .env.

    Symbol format: "NSE:INFY-EQ", "BSE:TCS-EQ". The DEFAULT_EXCHANGE prefix
    is prepended automatically when missing.
    """

    def __init__(self):
        self._client = None

    def login(self) -> None:
        self._client = connect_to_fyers()
        if not self._client:
            raise RuntimeError(
                "Fyers TOTP login failed. Check credentials in .env — "
                "APP_ID, FYERS_TOTP_KEY, SECRET_KEY, FYERS_ID, PIN, REDIRECT_URI."
            )
        profile = self._client.get_profile()
        name = profile.get("data", {}).get("name", "")
        print(f"Logged in to Fyers{' as ' + name if name else ''}.")

    def _ensure_logged_in(self):
        if self._client is None:
            self.login()

    def _full_symbol(self, ticker: str) -> str:
        """Ensure the symbol has the exchange prefix (e.g. 'NSE:INFY-EQ')."""
        if ":" in ticker:
            return ticker
        return f"{DEFAULT_EXCHANGE}:{ticker}-EQ"

    def get_holdings(self) -> pd.DataFrame:
        self._ensure_logged_in()
        response = self._client.holdings()
        records = response.get("holdings", [])

        rows = []
        for item in records:
            avg_price = float(item.get("avg_price", 0))
            ltp = float(item.get("ltp", 0))
            pct = (ltp - avg_price) / avg_price if avg_price else 0.0
            symbol = item.get("symbol", "")
            # Strip exchange prefix for the normalised ticker column
            ticker = symbol.split(":")[-1].replace("-EQ", "").replace("-BE", "")
            rows.append({
                "ticker": ticker,
                "security_id": symbol,   # Full Fyers symbol used for orders
                "quantity": float(item.get("qty", 0)),
                "average_buy_price": avg_price,
                "current_price": ltp,
                "percent_change": pct,
            })

        return pd.DataFrame(rows, columns=[
            "ticker", "security_id", "quantity",
            "average_buy_price", "current_price", "percent_change",
        ])

    def get_open_orders(self) -> list:
        self._ensure_logged_in()
        response = self._client.orderbook()
        orders = response.get("orderBook", [])
        # Status 6 = pending, 1 = transit
        return [o for o in orders if o.get("status") in (1, 6)]

    def cancel_all_orders(self) -> None:
        self._ensure_logged_in()
        open_orders = self.get_open_orders()
        for order in open_orders:
            order_id = order.get("id")
            if order_id:
                self._client.cancel_order(data={"id": order_id})
        print(f"Cancelled {len(open_orders)} open order(s) on Fyers.")

    def buy_market(self, ticker: str, quantity: int, security_id: str = "") -> dict:
        self._ensure_logged_in()
        symbol = self._full_symbol(security_id or ticker)
        data = {
            "symbol": symbol,
            "qty": quantity,
            "type": DEFAULT_ORDER_TYPE,
            "side": 1,  # 1 = Buy
            "productType": DEFAULT_PRODUCT_TYPE,
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": DEFAULT_VALIDITY,
            "disclosedQty": 0,
            "offlineOrder": False,
        }
        return self._client.place_order(data=data)

    def sell_market(self, ticker: str, quantity: int, security_id: str = "") -> dict:
        self._ensure_logged_in()
        symbol = self._full_symbol(security_id or ticker)
        data = {
            "symbol": symbol,
            "qty": quantity,
            "type": DEFAULT_ORDER_TYPE,
            "side": -1,  # -1 = Sell
            "productType": DEFAULT_PRODUCT_TYPE,
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": DEFAULT_VALIDITY,
            "disclosedQty": 0,
            "offlineOrder": False,
        }
        return self._client.place_order(data=data)
