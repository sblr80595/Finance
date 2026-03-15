import sys
import os

# Ensure project root is on sys.path so config/ and brokers/ are importable
# regardless of working directory (e.g. when launched via streamlit run)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from brokers.base_broker import BaseBroker


def get_broker() -> BaseBroker:
    """Return the broker instance for the currently configured ACTIVE_BROKER."""
    from config.broker_config import ACTIVE_BROKER
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
