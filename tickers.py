"""
Indian market ticker utilities.

Functions return plain NSE/BSE trading symbols (e.g. "INFY", "RELIANCE").
For use with yfinance, append ".NS" for NSE or ".BO" for BSE.

Backward-compatible aliases are provided at the bottom so existing scripts
that call tickers_sp500(), tickers_nasdaq(), etc. continue to work but now
receive Indian market symbols instead of US ones.
"""

import pandas as pd
import requests
from io import StringIO

# NSE requires browser-like headers to avoid 403
_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
    "Accept-Encoding": "gzip, deflate, br",
}


def _nse_session() -> requests.Session:
    """Return a requests.Session pre-loaded with NSE cookies."""
    s = requests.Session()
    s.headers.update(_NSE_HEADERS)
    s.get("https://www.nseindia.com", timeout=10)
    return s


def tickers_nifty50() -> list:
    """Return Nifty 50 constituent symbols from NSE archives."""
    url = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
    resp = requests.get(url, headers=_NSE_HEADERS, timeout=15)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    return df["Symbol"].str.strip().tolist()


def tickers_nifty500() -> list:
    """Return Nifty 500 constituent symbols from NSE archives."""
    url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
    resp = requests.get(url, headers=_NSE_HEADERS, timeout=15)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    return df["Symbol"].str.strip().tolist()


def tickers_nifty_next50() -> list:
    """Return Nifty Next 50 constituent symbols from NSE archives."""
    url = "https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv"
    resp = requests.get(url, headers=_NSE_HEADERS, timeout=15)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    return df["Symbol"].str.strip().tolist()


def tickers_nse() -> list:
    """
    Return all NSE-listed equity symbols (EQ series only).

    Source: NSE EQUITY_L.csv — refreshed daily by NSE.
    """
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    resp = requests.get(url, headers=_NSE_HEADERS, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    # NSE CSV has a leading space in some column names — strip them all
    df.columns = df.columns.str.strip()
    df = df[df["SERIES"].str.strip() == "EQ"]
    return df["SYMBOL"].str.strip().tolist()


def tickers_sensex() -> list:
    """
    Return BSE Sensex 30 constituent symbols scraped from Wikipedia.

    Uses a requests.Session to satisfy Wikipedia's anti-bot checks.
    """
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    resp = s.get("https://en.wikipedia.org/wiki/BSE_SENSEX", timeout=15)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))
    for df in tables:
        # Skip tables with integer column indices (non-header tables)
        str_cols = [c for c in df.columns if isinstance(c, str)]
        cols_lower = [c.lower() for c in str_cols]
        if "symbol" in cols_lower:
            col = str_cols[cols_lower.index("symbol")]
            # Wikipedia returns symbols with ".BO" suffix; strip it for clean NSE symbols
            symbols = (
                df[col].dropna()
                .str.strip()
                .str.replace(r"\.(BO|NS)$", "", regex=True)
                .tolist()
            )
            if symbols:
                return symbols
    raise ValueError("Could not locate Sensex constituents table on Wikipedia.")


def tickers_bse() -> list:
    """
    Return active BSE-listed equity scrip codes via BSE India API.

    Note:
    - Returns numeric scrip codes (e.g. "500325" for Reliance).
    - For yfinance use, append ".BO": "500325.BO".
    - The BSE API requires an active browser session; if it fails, this
      function raises a RuntimeError with instructions to use tickers_nse()
      as a fallback (most liquid Indian stocks are dual-listed on NSE).
    """
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.bseindia.com",
        "Origin": "https://www.bseindia.com",
    })
    # Load main page first to pick up CSRF cookies
    s.get("https://www.bseindia.com/", timeout=10)

    url = (
        "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
        "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
    )
    resp = s.get(url, timeout=30)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if "json" not in content_type:
        raise RuntimeError(
            "BSE API returned HTML instead of JSON — the API requires a "
            "live browser session that cannot be replicated with requests.\n"
            "Fallback: use tickers_nse() instead. Most liquid Indian stocks "
            "are dual-listed on both NSE and BSE."
        )

    data = resp.json()
    return [str(item["SCRIP_CD"]) for item in data.get("Table", [])]


# ── Backward-compatible aliases ───────────────────────────────────────────────
# Existing scripts that import tickers_sp500(), tickers_nasdaq(), etc. will
# now receive Indian market symbols automatically.

tickers_sp500 = tickers_nifty50       # ~500 large-cap  → Nifty 50
tickers_nasdaq = tickers_nse           # all NASDAQ      → all NSE equities
tickers_nyse = tickers_bse             # all NYSE        → all BSE equities
tickers_dow = tickers_sensex           # Dow 30          → Sensex 30
tickers_amex = tickers_nifty500        # AMEX            → Nifty 500
