import os
from dotenv import load_dotenv

# Resolve .env relative to this file so it loads correctly regardless of CWD
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path)

# ============================================================
# Fyers API Credentials  (set values in .env)
# ============================================================
# Documentation : https://myapi.fyers.in/docsv3
#
# Authentication uses TOTP-based auto-login — no manual OAuth
# needed. The login flow runs automatically each session using
# the TOTP key from your Fyers 2FA setup.
#
# To get your TOTP key:
#   1. Go to Fyers → My Account → Security → 2FA
#   2. Set up TOTP authenticator and note the secret key

APP_ID          = os.getenv("APP_ID", "")          # e.g. "XXXXXX-100"
FYERS_TOTP_KEY  = os.getenv("FYERS_TOTP_KEY", "")  # 32-char TOTP secret
SECRET_KEY      = os.getenv("SECRET_KEY", "")
REDIRECT_URI    = os.getenv("REDIRECT_URI", "https://127.0.0.1")
FYERS_ID        = os.getenv("FYERS_ID", "")         # Your Fyers client ID
PIN             = os.getenv("PIN", "")               # 4-digit login PIN


# ============================================================
# Default Order Settings
# ============================================================
# Symbol format: "NSE:RELIANCE-EQ", "BSE:TCS-EQ"
DEFAULT_EXCHANGE = "NSE"

# Order type: 1=Limit, 2=Market, 3=Stop-Loss, 4=Stop-Limit
DEFAULT_ORDER_TYPE = 2  # Market

# Product type: "CNC"=delivery, "INTRADAY"=intraday, "MARGIN"=margin
DEFAULT_PRODUCT_TYPE = "INTRADAY"

# Validity: "DAY" or "IOC"
DEFAULT_VALIDITY = "DAY"
