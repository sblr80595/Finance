import os
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path)

# ============================================================
# Broker Selection  (set ACTIVE_BROKER in .env)
# ============================================================
# Supported values: "fyers", "dhan", "robinhood"
ACTIVE_BROKER = os.getenv("ACTIVE_BROKER", "fyers")

# ============================================================
# Common Trading Parameters
# ============================================================
# Default number of shares per order (used in trading_bot.py)
DEFAULT_QUANTITY = 4
