import os
from dotenv import load_dotenv

load_dotenv()

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
