"""
Fyers TOTP-based auto-authentication.

Handles the full 3-step login flow automatically using the TOTP key
stored in .env — no manual browser login or token copy-paste required.

The access token is refreshed on every call to connect_to_fyers(), so
just call it at the start of each trading session.

Credentials required in .env:
    APP_ID          — Fyers app ID (format: XXXXXX-100)
    FYERS_TOTP_KEY  — 32-char secret from Fyers 2FA setup
    SECRET_KEY      — Fyers app secret key
    REDIRECT_URI    — Redirect URI registered in your Fyers app
    FYERS_ID        — Your Fyers client ID (login username)
    PIN             — Your Fyers 4-digit login PIN
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
import pyotp
from urllib.parse import parse_qs, urlparse
from fyers_apiv3 import fyersModel

from config.fyers_config import (
    APP_ID, FYERS_TOTP_KEY, SECRET_KEY,
    REDIRECT_URI, FYERS_ID, PIN,
)

_BASE_URL   = "https://api-t2.fyers.in/vagator/v2"
_BASE_URL_2 = "https://api-t1.fyers.in/api/v3"

_URL_SEND_LOGIN_OTP    = _BASE_URL   + "/send_login_otp"
_URL_VERIFY_TOTP       = _BASE_URL   + "/verify_otp"
_URL_VERIFY_PIN        = _BASE_URL   + "/verify_pin"
_URL_TOKEN             = _BASE_URL_2 + "/token"


def _send_login_otp(fy_id: str, app_id: str = "2"):
    try:
        resp = requests.post(_URL_SEND_LOGIN_OTP, json={"fy_id": fy_id, "app_id": app_id})
        if resp.status_code != 200:
            return [False, resp.text]
        return [True, resp.json()["request_key"]]
    except Exception as e:
        return [False, e]


def _verify_totp(request_key: str, totp: str):
    try:
        resp = requests.post(_URL_VERIFY_TOTP, json={"request_key": request_key, "otp": totp})
        if resp.status_code != 200:
            return [False, resp.text]
        return [True, resp.json()["request_key"]]
    except Exception as e:
        return [False, e]


def get_access_token() -> str | None:
    """
    Run the full TOTP-based Fyers login flow and return a fresh access token.
    Returns None if any step fails.
    """
    # Step 1 — send login OTP
    otp_result = _send_login_otp(fy_id=FYERS_ID)
    if not otp_result[0]:
        print(f"send_login_otp failed: {otp_result[1]}")
        return None
    print("send_login_otp OK")

    # Step 2 — verify TOTP
    totp = pyotp.TOTP(FYERS_TOTP_KEY).now()
    totp_result = _verify_totp(request_key=otp_result[1], totp=totp)
    if not totp_result[0]:
        print(f"verify_totp failed: {totp_result[1]}")
        return None
    print("verify_totp OK")

    # Step 3 — verify PIN
    ses = requests.Session()
    res_pin = ses.post(_URL_VERIFY_PIN, json={
        "request_key": totp_result[1],
        "identity_type": "pin",
        "identifier": PIN,
        "recaptcha_token": "",
    }).json()

    if res_pin.get("s") != "ok":
        print(f"verify_pin failed: {res_pin}")
        return None
    print("verify_pin OK")

    ses.headers.update({"authorization": f"Bearer {res_pin['data']['access_token']}"})

    # Parse APP_ID into base and type (e.g. "QVK3WHLJ1W-100" → base="QVK3WHLJ1W", type="100")
    parts = APP_ID.split("-")
    if len(parts) != 2:
        print(f"Invalid APP_ID format '{APP_ID}'. Expected APPID-APPTYPE (e.g. XXXXXX-100).")
        return None
    app_id_base, app_type = parts

    auth_resp = ses.post(_URL_TOKEN, json={
        "fyers_id": FYERS_ID,
        "app_id": app_id_base,
        "redirect_uri": REDIRECT_URI,
        "appType": app_type,
        "code_challenge": "",
        "state": "None",
        "scope": "",
        "nonce": "",
        "response_type": "code",
        "create_cookie": True,
    })

    try:
        auth_data = auth_resp.json()
    except Exception:
        print(f"Failed to parse token response: {auth_resp.text}")
        return None

    if auth_data.get("s") != "ok":
        print(f"token request failed: {auth_data}")
        return None

    auth_code = parse_qs(urlparse(auth_data["Url"]).query)["auth_code"][0]

    # Exchange auth_code for access token via Fyers SDK
    session = fyersModel.SessionModel(
        client_id=APP_ID,
        redirect_uri=REDIRECT_URI,
        response_type="code",
        state="sample",
        secret_key=SECRET_KEY,
        grant_type="authorization_code",
    )
    session.set_token(auth_code)
    token_resp = session.generate_token()

    if token_resp.get("s") != "ok":
        print(f"generate_token failed: {token_resp}")
        return None

    return token_resp["access_token"]


def connect_to_fyers() -> fyersModel.FyersModel | None:
    """
    Authenticate with Fyers and return a ready-to-use FyersModel client.
    Returns None if authentication fails.
    """
    access_token = get_access_token()
    if not access_token:
        return None

    client = fyersModel.FyersModel(
        token=access_token,
        is_async=False,
        client_id=APP_ID,
        log_path="",
    )
    # Expose raw token for websocket use if needed
    client.access_token = access_token
    return client


if __name__ == "__main__":
    client = connect_to_fyers()
    if client:
        print("Connection successful!")
        print(client.get_profile())
    else:
        print("Failed to connect to Fyers.")
