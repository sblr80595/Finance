import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Robinhood Credentials  (set values in .env)
# ============================================================
# Sign up / manage credentials at: https://robinhood.com
#
# Two-factor authentication (MFA):
#   If your account has MFA enabled, set RH_MFA_CODE to the current
#   6-digit TOTP code, or leave it empty to be prompted interactively.

USERNAME = os.getenv("RH_USERNAME", "")
PASSWORD = os.getenv("RH_PASSWORD", "")
MFA_CODE = os.getenv("RH_MFA_CODE", "")
