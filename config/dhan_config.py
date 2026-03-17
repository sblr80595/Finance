import os
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path)

# ============================================================
# Dhan API Credentials  (set values in .env)
# ============================================================
# Documentation : https://dhanhq.co/docs/v2/
#
# Steps to get credentials:
#   1. Log in at https://api.dhan.co
#   2. Go to My Apps → Create App to get CLIENT_ID
#   3. Generate an access token from the same portal
#   4. Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in .env

CLIENT_ID    = os.getenv("DHAN_CLIENT_ID", "")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")

# Dhan REST API base URL
DHAN_API_BASE_URL = "https://api.dhan.co/v2"


# ============================================================
# Default Order Settings
# ============================================================
# Exchange segment: "NSE_EQ" (NSE equities), "BSE_EQ" (BSE equities)
DEFAULT_EXCHANGE = "NSE_EQ"

# Product type: "INTRADAY"=same-day, "CNC"=delivery, "MARGIN"=margin
DEFAULT_PRODUCT_TYPE = "INTRADAY"

# Order type: "MARKET", "LIMIT", "STOP_LOSS", "STOP_LOSS_MARKET"
DEFAULT_ORDER_TYPE = "MARKET"
