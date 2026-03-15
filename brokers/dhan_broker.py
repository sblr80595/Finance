import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
from dhanhq import dhanhq

from brokers.base_broker import BaseBroker
from config.dhan_config import (
    CLIENT_ID,
    ACCESS_TOKEN,
    DEFAULT_EXCHANGE,
    DEFAULT_PRODUCT_TYPE,
    DEFAULT_ORDER_TYPE,
)

# Map config strings to dhanhq constants
_EXCHANGE_MAP = {
    "NSE_EQ": dhanhq.NSE,
    "BSE_EQ": dhanhq.BSE,
    "NSE_FNO": dhanhq.NSE_FNO,
    "BSE_FNO": dhanhq.BSE_FNO,
}

_PRODUCT_MAP = {
    "INTRADAY": dhanhq.INTRA,
    "CNC": dhanhq.CNC,
    "MARGIN": dhanhq.MARGIN,
}

_ORDER_TYPE_MAP = {
    "MARKET": dhanhq.MARKET,
    "LIMIT": dhanhq.LIMIT,
    "STOP_LOSS": dhanhq.SL,           # dhanhq 2.x renamed STOP_LOSS → SL
    "STOP_LOSS_MARKET": dhanhq.SLM,   # dhanhq 2.x renamed STOP_LOSS_MARKET → SLM
}


class DhanBroker(BaseBroker):
    """
    Dhan broker implementation using the dhanhq library.

    Notes:
    - Dhan identifies instruments by numeric security_id, not just ticker symbols.
      buy_market / sell_market require a valid security_id (available in the
      holdings DataFrame returned by get_holdings).
    - Credentials must be set in config/dhan_config.py.
    - Access tokens are session-based. Generate a fresh token from
      https://api.dhan.co before each trading session.
    """

    def __init__(self):
        self._client = None

    def login(self) -> None:
        self._client = dhanhq(CLIENT_ID, ACCESS_TOKEN)
        print(f"Dhan client initialised for client_id={CLIENT_ID}.")

    def _ensure_logged_in(self):
        if self._client is None:
            self.login()

    def get_holdings(self) -> pd.DataFrame:
        self._ensure_logged_in()
        response = self._client.get_holdings()
        records = response.get("data", [])

        rows = []
        for item in records:
            avg_price = float(item.get("avgCostPrice", 0))
            ltp = float(item.get("lastTradedPrice", 0))
            pct = (ltp - avg_price) / avg_price if avg_price else 0.0
            rows.append({
                "ticker": item.get("tradingSymbol", ""),
                "security_id": str(item.get("securityId", "")),
                "quantity": float(item.get("totalQty", 0)),
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
        response = self._client.get_order_list()
        orders = response.get("data", [])
        return [o for o in orders if o.get("orderStatus") in ("PENDING", "TRANSIT", "PART_TRADED")]

    def cancel_all_orders(self) -> None:
        self._ensure_logged_in()
        open_orders = self.get_open_orders()
        for order in open_orders:
            order_id = order.get("orderId")
            if order_id:
                self._client.cancel_order(order_id)
        print(f"Cancelled {len(open_orders)} open order(s) on Dhan.")

    def buy_market(self, ticker: str, quantity: int, security_id: str = "") -> dict:
        self._ensure_logged_in()
        if not security_id:
            raise ValueError(
                f"security_id is required for Dhan orders. "
                f"Use the security_id column from get_holdings() for '{ticker}'."
            )
        return self._client.place_order(
            security_id=security_id,
            exchange_segment=_EXCHANGE_MAP.get(DEFAULT_EXCHANGE, dhanhq.NSE),
            transaction_type=dhanhq.BUY,
            quantity=quantity,
            order_type=_ORDER_TYPE_MAP.get(DEFAULT_ORDER_TYPE, dhanhq.MARKET),
            product_type=_PRODUCT_MAP.get(DEFAULT_PRODUCT_TYPE, dhanhq.INTRA),
            price=0,
        )

    def sell_market(self, ticker: str, quantity: int, security_id: str = "") -> dict:
        self._ensure_logged_in()
        if not security_id:
            raise ValueError(
                f"security_id is required for Dhan orders. "
                f"Use the security_id column from get_holdings() for '{ticker}'."
            )
        return self._client.place_order(
            security_id=security_id,
            exchange_segment=_EXCHANGE_MAP.get(DEFAULT_EXCHANGE, dhanhq.NSE),
            transaction_type=dhanhq.SELL,
            quantity=quantity,
            order_type=_ORDER_TYPE_MAP.get(DEFAULT_ORDER_TYPE, dhanhq.MARKET),
            product_type=_PRODUCT_MAP.get(DEFAULT_PRODUCT_TYPE, dhanhq.INTRA),
            price=0,
        )
