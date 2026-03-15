import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.broker_config import ACTIVE_BROKER
from brokers.base_broker import BaseBroker


def get_broker() -> BaseBroker:
    """Return the broker instance for the currently configured ACTIVE_BROKER."""
    broker = ACTIVE_BROKER.strip().lower()

    if broker == "robinhood":
        from brokers.robinhood_broker import RobinhoodBroker
        return RobinhoodBroker()
    elif broker == "dhan":
        from brokers.dhan_broker import DhanBroker
        return DhanBroker()
    elif broker == "fyers":
        from brokers.fyers_broker import FyersBroker
        return FyersBroker()
    else:
        raise ValueError(
            f"Unknown broker '{ACTIVE_BROKER}'. "
            "Set ACTIVE_BROKER in config/broker_config.py to one of: robinhood, dhan, fyers"
        )
