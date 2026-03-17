"""
Market data provider backed by Fyers API with SQLite caching.

Single public function for most use cases:
    get_history(symbol, start, end, resolution="D") -> pd.DataFrame

Cache behaviour
---------------
Data is stored in data_cache.sqlite at the project root.
On every call:
  1. The max cached date for (symbol, resolution) is checked.
  2. Only the missing tail (new trading days) is fetched from Fyers.
  3. The full requested range is then read back from cache.

This means the first call fetches from Fyers; every subsequent call
for the same symbol serves from cache, with only the daily delta
triggering a new API call.

Symbol format
-------------
Pass a plain NSE symbol ("RELIANCE") or full Fyers format
("NSE:RELIANCE-EQ"). Plain symbols are auto-converted.
"""

import logging
import sqlite3
import sys
import os
import time
from datetime import datetime, date
from pathlib import Path
from typing import Union

import pandas as pd

# Ensure project root is on sys.path so brokers/ and config/ are importable
# when this module is imported from a subdirectory (e.g. stock_data/)
_project_root = str(Path(__file__).parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

log = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent / "data_cache.sqlite"

# Max trading days Fyers returns per history call per resolution
_MAX_DAYS_PER_CALL = {
    "D": 365, "W": 2000, "M": 5000,
    "120": 100, "60": 100, "30": 60, "15": 40, "5": 10, "1": 3,
}

# Module-level Fyers client — authenticated once per session
_fyers_client = None


# ── Symbol helpers ─────────────────────────────────────────────────────────────

def to_fyers_symbol(symbol: str) -> str:
    """Return Fyers-formatted symbol. "RELIANCE" → "NSE:RELIANCE-EQ"."""
    symbol = symbol.strip().upper()
    if ":" in symbol:
        return symbol
    return f"NSE:{symbol}-EQ"


# ── Fyers connection ───────────────────────────────────────────────────────────

def _get_client():
    global _fyers_client
    if _fyers_client is None:
        from brokers.fyers_auth import connect_to_fyers
        _fyers_client = connect_to_fyers()
        if not _fyers_client:
            raise RuntimeError(
                "Fyers authentication failed. "
                "Check APP_ID, FYERS_TOTP_KEY, SECRET_KEY, FYERS_ID, PIN in .env"
            )
    return _fyers_client


# ── SQLite cache ───────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            symbol     TEXT    NOT NULL,
            resolution TEXT    NOT NULL,
            ts         INTEGER NOT NULL,
            dt         TEXT    NOT NULL,
            open       REAL    NOT NULL,
            high       REAL    NOT NULL,
            low        REAL    NOT NULL,
            close      REAL    NOT NULL,
            volume     INTEGER NOT NULL,
            PRIMARY KEY (symbol, resolution, ts)
        );
        CREATE INDEX IF NOT EXISTS idx_ohlcv ON ohlcv(symbol, resolution, ts);
    """)
    return conn


def _max_cached_ts(symbol: str, resolution: str) -> int | None:
    """Return the max cached Unix timestamp for (symbol, resolution), or None."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(ts) FROM ohlcv WHERE symbol=? AND resolution=?",
            (symbol, resolution),
        ).fetchone()
    return row[0] if row and row[0] else None


def _read_cache(symbol: str, resolution: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    with _get_conn() as conn:
        return pd.read_sql_query(
            """SELECT dt, open, high, low, close, volume
               FROM ohlcv
               WHERE symbol=? AND resolution=? AND ts>=? AND ts<=?
               ORDER BY ts""",
            conn,
            params=(symbol, resolution, start_ts, end_ts),
        )


def _write_cache(symbol: str, resolution: str, candles: list) -> None:
    if not candles:
        return
    rows = [
        (
            symbol, resolution, int(c[0]),
            datetime.utcfromtimestamp(c[0]).strftime("%Y-%m-%d %H:%M:%S"),
            float(c[1]), float(c[2]), float(c[3]), float(c[4]), int(c[5]),
        )
        for c in candles
    ]
    with _get_conn() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO ohlcv
               (symbol, resolution, ts, dt, open, high, low, close, volume)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        conn.commit()
    log.info("Cached %d candles for %s (%s)", len(rows), symbol, resolution)


# ── Fyers fetch with chunking + rate-limit backoff ────────────────────────────

def _fetch_candles(
    symbol: str,
    start_ts: int,
    end_ts: int,
    resolution: str,
    on_chunk=None,          # optional callback(done: int, total: int)
) -> list:
    """
    Fetch candles from Fyers, chunking the request if the range exceeds
    the per-call limit. Returns the full raw candle list.

    on_chunk, if provided, is called after each chunk completes with
    (chunks_done, total_chunks) so callers can show a progress bar.
    """
    import math as _math
    client = _get_client()
    chunk_secs = _MAX_DAYS_PER_CALL.get(resolution, 365) * 86400
    total_chunks = max(1, _math.ceil((end_ts - start_ts) / chunk_secs))
    all_candles: list = []
    chunk_start = start_ts
    chunks_done = 0

    while chunk_start < end_ts:
        chunk_end = min(chunk_start + chunk_secs, end_ts)
        payload = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "0",          # Unix timestamps
            "range_from": str(chunk_start),
            "range_to": str(chunk_end),
            "cont_flag": 1,
        }

        resp = {}
        for attempt in range(3):
            resp = client.history(data=payload)
            if resp.get("code") == 429:
                delay = 2 ** (attempt + 1)
                log.warning("Rate limit hit for %s — retrying in %ss", symbol, delay)
                time.sleep(delay)
            else:
                break

        s = resp.get("s")
        if s == "no_data":
            # Chunk covers a period with no trading data (e.g. weekend, holiday range)
            log.debug("No data for %s chunk %s→%s — skipping", symbol, chunk_start, chunk_end)
            chunk_start = chunk_end + 1
            chunks_done += 1
            if on_chunk:
                on_chunk(chunks_done, total_chunks)
            continue
        if s != "ok":
            log.error("Fyers history error for %s: %s", symbol, resp)
            break

        candles = resp.get("candles", [])
        all_candles.extend(candles)
        chunks_done += 1
        log.info("Fetched %d candles for %s chunk %d/%d",
                 len(candles), symbol, chunks_done, total_chunks)

        if on_chunk:
            on_chunk(chunks_done, total_chunks)

        chunk_start = chunk_end + 1

    return all_candles


# ── Public API ─────────────────────────────────────────────────────────────────

def get_history(
    symbol: str,
    start:  Union[str, date, datetime],
    end:    Union[str, date, datetime],
    resolution: str = "D",
    on_chunk=None,          # optional callback(done: int, total: int)
) -> pd.DataFrame:
    """
    Return historical OHLCV data as a DataFrame.

    Serves from local SQLite cache where possible; fetches only the
    missing tail from Fyers API.

    Args:
        symbol:     NSE symbol ("RELIANCE") or Fyers format ("NSE:RELIANCE-EQ").
        start:      Start date — str "YYYY-MM-DD", date, or datetime.
        end:        End date.
        resolution: Candle size — "D" daily (default), "W" weekly, "M" monthly,
                    "120" 2-hour, "60" 1-hour, "30" 30-min, "15" 15-min,
                    "5" 5-min, "1" 1-min.
        on_chunk:   Optional callback(done, total) called after each API chunk
                    completes. Useful for showing a progress bar in UIs.

    Returns:
        DataFrame indexed by datetime with columns:
            Open, High, Low, Close, Volume, Adj Close (alias for Close).
        Returns an empty DataFrame when no data is available.
    """
    sym      = to_fyers_symbol(symbol)
    start_dt = pd.to_datetime(start).normalize()
    end_dt   = pd.to_datetime(end).normalize()
    start_ts = int(start_dt.timestamp())
    end_ts   = int(end_dt.timestamp()) + 86399   # include full end day

    # Determine how much is already in cache
    max_cached = _max_cached_ts(sym, resolution)

    if max_cached is None or max_cached < end_ts:
        # Fetch only the delta we don't have yet
        fetch_from = (max_cached + 1) if max_cached else start_ts
        fetch_from = max(fetch_from, start_ts)
        candles = _fetch_candles(sym, fetch_from, end_ts, resolution, on_chunk=on_chunk)
        _write_cache(sym, resolution, candles)

    df = _read_cache(sym, resolution, start_ts, end_ts)

    if df.empty:
        return pd.DataFrame()

    df["dt"] = pd.to_datetime(df["dt"])
    df = df.set_index("dt")
    df.index.name = "Date"
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    df["Adj Close"] = df["Close"]   # backward-compat alias
    return df


def get_quote(symbol: str) -> dict:
    """
    Fetch a live quote for a symbol.

    Returns the raw Fyers response dict with current price data.
    Does not use the cache — always hits Fyers API.
    """
    sym    = to_fyers_symbol(symbol)
    client = _get_client()
    resp   = client.quotes({"symbols": sym})
    if resp.get("s") != "ok":
        raise RuntimeError(f"Quote fetch failed for {sym}: {resp}")
    return resp


def cache_info() -> pd.DataFrame:
    """Return a summary of what's stored in data_cache.sqlite."""
    with _get_conn() as conn:
        return pd.read_sql_query(
            """SELECT symbol, resolution,
                      COUNT(*)  AS candles,
                      MIN(dt)   AS first_date,
                      MAX(dt)   AS last_date
               FROM ohlcv
               GROUP BY symbol, resolution
               ORDER BY symbol""",
            conn,
        )
