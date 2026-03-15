from abc import ABC, abstractmethod
import pandas as pd


class BaseBroker(ABC):
    """
    Abstract interface that every broker implementation must satisfy.

    Holdings DataFrame schema (returned by get_holdings):
        ticker          str   — trading symbol (e.g. "INFY", "RELIANCE")
        security_id     str   — broker-internal ID; may equal ticker for some brokers
        quantity        float — total shares held
        average_buy_price float — average cost per share
        current_price   float — last traded / current market price
        percent_change  float — (current_price - average_buy_price) / average_buy_price
    """

    @abstractmethod
    def login(self) -> None:
        """Authenticate with the broker. Raises on failure."""

    @abstractmethod
    def get_holdings(self) -> pd.DataFrame:
        """
        Return current portfolio holdings as a normalised DataFrame.
        Columns: ticker, security_id, quantity, average_buy_price,
                 current_price, percent_change.
        """

    @abstractmethod
    def get_open_orders(self) -> list:
        """Return a list of raw open order objects from the broker API."""

    @abstractmethod
    def cancel_all_orders(self) -> None:
        """Cancel every open order in the account."""

    @abstractmethod
    def buy_market(self, ticker: str, quantity: int, security_id: str = "") -> dict:
        """
        Place a market buy order.

        Args:
            ticker:      Trading symbol (e.g. "INFY").
            quantity:    Number of shares to buy.
            security_id: Broker-internal ID required by some brokers (e.g. Dhan).

        Returns:
            Raw order response dict from the broker API.
        """

    @abstractmethod
    def sell_market(self, ticker: str, quantity: int, security_id: str = "") -> dict:
        """
        Place a market sell order.

        Args:
            ticker:      Trading symbol (e.g. "INFY").
            quantity:    Number of shares to sell.
            security_id: Broker-internal ID required by some brokers (e.g. Dhan).

        Returns:
            Raw order response dict from the broker API.
        """
