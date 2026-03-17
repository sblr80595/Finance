"""
Market Pulse — Two-tab technical dashboard with AI analysis.

Tab 1: Single index deep-dive  (price snapshot → indicators → AI)
Tab 2: Nifty 50 stocks screener (colour-coded table + AI breadth)

Run:
    streamlit run stock_data/market_pulse.py
"""

import sys, os, datetime, math

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import ta_functions as ta
from data_provider import get_history

load_dotenv(os.path.join(parent_dir, ".env"))

# ── Catalogues ────────────────────────────────────────────────────────────────

INDICES = [
    ("NIFTY 50",           "NSE:NIFTY50-INDEX"),
    ("NIFTY BANK",         "NSE:NIFTYBANK-INDEX"),
    ("NIFTY IT",           "NSE:NIFTYIT-INDEX"),
    ("NIFTY MIDCAP 100",   "NSE:NIFTYMIDCAP100-INDEX"),
    ("NIFTY SMALLCAP 100", "NSE:NIFTYSMALLCAP100-INDEX"),
    ("NIFTY FMCG",         "NSE:NIFTYFMCG-INDEX"),
    ("NIFTY PHARMA",       "NSE:NIFTYPHARMA-INDEX"),
    ("NIFTY AUTO",         "NSE:NIFTYAUTO-INDEX"),
    ("NIFTY REALTY",       "NSE:NIFTYREALTY-INDEX"),
    ("SENSEX",             "BSE:SENSEX-INDEX"),
]

TIMEFRAMES = {
    "1 Min":  ("1",   3,   60),
    "5 Min":  ("5",   10,  60),
    "15 Min": ("15",  40,  60),
    "30 Min": ("30",  60,  60),
    "1 Hour": ("60",  100, 60),
    "2 Hour": ("120", 100, 60),
    "Day":    ("D",   365, 260),
}

DURATION_OPTIONS = {
    "1 Min":  [("1 Day", 1), ("2 Days", 2), ("3 Days", 3)],
    "5 Min":  [("1 Week", 7), ("2 Weeks", 14), ("1 Month", 30), ("3 Months", 90)],
    "15 Min": [("1 Week", 7), ("2 Weeks", 14), ("1 Month", 30), ("3 Months", 90), ("6 Months", 180)],
    "30 Min": [("1 Month", 30), ("3 Months", 90), ("6 Months", 180), ("1 Year", 365)],
    "1 Hour": [("1 Month", 30), ("3 Months", 90), ("6 Months", 180), ("1 Year", 365), ("2 Years", 730)],
    "2 Hour": [("1 Month", 30), ("3 Months", 90), ("6 Months", 180), ("1 Year", 365), ("2 Years", 730)],
    "Day":    [("1 Month", 30), ("3 Months", 90), ("6 Months", 180), ("1 Year", 365), ("2 Years", 730), ("5 Years", 1825)],
}

DURATION_DEFAULT = {
    "1 Min": 2, "5 Min": 2, "15 Min": 2, "30 Min": 1,
    "1 Hour": 2, "2 Hour": 2, "Day": 3,
}

# key → (display label, category, format string)
INDICATOR_META = {
    "rsi":         ("RSI (14)",       "Momentum",      "{:.1f}"),
    "macd_hist":   ("MACD Histogram", "Momentum",      "{:.2f}"),
    "stoch_k":     ("Stochastic %K",  "Momentum",      "{:.1f}"),
    "bb_pct":      ("BB %B",          "Volatility",    "{:.1f}%"),
    "atr_pct":     ("ATR % Price",    "Volatility",    "{:.2f}%"),
    "cci":         ("CCI (14)",       "Oscillator",    "{:.1f}"),
    "willr":       ("Williams %R",    "Oscillator",    "{:.1f}"),
    "adx":         ("ADX (14)",       "Trend Str.",    "{:.1f}"),
    "sma20_bias":  ("vs SMA 20",      "Trend",         "{:+.2f}%"),
    "sma50_bias":  ("vs SMA 50",      "Trend",         "{:+.2f}%"),
    "sma200_bias": ("vs SMA 200",     "Trend",         "{:+.2f}%"),
    "ema20_bias":  ("vs EMA 20",      "Trend",         "{:+.2f}%"),
    "ema50_bias":  ("vs EMA 50",      "Trend",         "{:+.2f}%"),
}

DEFAULT_INDICATORS = ["rsi", "macd_hist", "stoch_k", "bb_pct", "cci", "adx", "sma50_bias"]


# ── Symbol helpers ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_nifty50_symbols() -> list[str]:
    csv = os.path.join(parent_dir, "nifty50_tickers.csv")
    if os.path.exists(csv):
        df = pd.read_csv(csv)
        return df[df.columns[0]].str.strip().tolist()
    return []


# ── Indicator computation ─────────────────────────────────────────────────────

def _v(s) -> float | None:
    s = s.dropna()
    return float(s.iloc[-1]) if not s.empty else None


def compute_indicators(df: pd.DataFrame) -> dict:
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    price = _v(c)
    prev  = float(c.iloc[-2]) if len(c) >= 2 else None

    sma20  = ta.SMA(c, 20);  s20  = _v(sma20)
    sma50  = ta.SMA(c, 50);  s50  = _v(sma50)
    sma200 = ta.SMA(c, 200); s200 = _v(sma200)
    ema20  = ta.EMA(c, 20);  e20  = _v(ema20)
    ema50  = ta.EMA(c, 50);  e50  = _v(ema50)

    bb_up, bb_mid, bb_dn = ta.BBANDS(c, 20)
    macd, macd_sig, macd_hist = ta.MACD(c)
    slowk, slowd = ta.STOCH(h, l, c)
    atr_val = _v(ta.ATR(h, l, c, 14))

    def bias(ma):
        return ((price - ma) / ma * 100) if (price and ma) else None

    bbu, bbd = _v(bb_up), _v(bb_dn)
    bb_pct_val = ((price - bbd) / (bbu - bbd) * 100
                  if None not in (price, bbu, bbd) and bbu != bbd else None)

    return {
        "price":       price,
        "prev":        prev,
        "last_open":   float(df["Open"].iloc[-1]),
        "last_high":   float(h.iloc[-1]),
        "last_low":    float(l.iloc[-1]),
        "last_vol":    float(v.iloc[-1]),
        "avg_vol20":   float(v.tail(20).mean()),
        "high_period": float(h.max()),
        "low_period":  float(l.min()),
        # MAs (raw values)
        "sma20": s20, "sma50": s50, "sma200": s200,
        "ema20": e20, "ema50": e50,
        # MA biases (% price is above/below MA)
        "sma20_bias":  bias(s20),  "sma50_bias":  bias(s50),
        "sma200_bias": bias(s200), "ema20_bias":  bias(e20),
        "ema50_bias":  bias(e50),
        # Bollinger
        "bb_up": bbu, "bb_mid": _v(bb_mid), "bb_dn": bbd,
        "bb_pct": bb_pct_val,
        # Momentum
        "rsi":       _v(ta.RSI(c, 14)),
        "macd":      _v(macd),
        "macd_sig":  _v(macd_sig),
        "macd_hist": _v(macd_hist),
        "stoch_k":   _v(slowk),
        "stoch_d":   _v(slowd),
        # Oscillators
        "cci":   _v(ta.CCI(h, l, c, 14)),
        "willr": _v(ta.WILLR(h, l, c, 14)),
        # Trend strength & volatility
        "adx":     _v(ta.ADX(h, l, c, 14)),
        "atr":     atr_val,
        "atr_pct": (atr_val / price * 100) if (atr_val and price) else None,
        # Volume
        "obv": _v(ta.OBV(c, v)),
    }


# ── Signal logic ──────────────────────────────────────────────────────────────

_G  = "background-color:#d4edda;color:#155724"   # green
_R  = "background-color:#f8d7da;color:#721c24"   # red
_Y  = "background-color:#fff3cd;color:#856404"   # yellow
_B  = "background-color:#d0e8ff;color:#0a4f8a"   # blue
_NA = ""


def get_signal(key: str, val) -> tuple[str, str, str]:
    """Return (emoji, label, css_background) for an indicator value."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "–", "N/A", _NA

    if key == "rsi":
        if val >= 70: return "🔴", "Overbought", _R
        if val <= 30: return "🟢", "Oversold",   _G
        return "🟡", "Neutral", _Y

    if key == "macd_hist":
        return ("🟢", "Bullish", _G) if val > 0 else ("🔴", "Bearish", _R)

    if key == "stoch_k":
        if val >= 80: return "🔴", "Overbought", _R
        if val <= 20: return "🟢", "Oversold",   _G
        return "🟡", "Neutral", _Y

    if key == "bb_pct":
        if val >= 100: return "🔴", "Above Upper", _R
        if val <= 0:   return "🟢", "Below Lower", _G
        if val >= 80:  return "🟠", "Near Upper",  "background-color:#ffe5d0;color:#7d3f0a"
        if val <= 20:  return "🟢", "Near Lower",  _G
        return "🟡", "Within Bands", _Y

    if key == "cci":
        if val >= 100:  return "🔴", "Overbought", _R
        if val <= -100: return "🟢", "Oversold",   _G
        return "🟡", "Neutral", _Y

    if key == "willr":
        if val >= -20: return "🔴", "Overbought", _R
        if val <= -80: return "🟢", "Oversold",   _G
        return "🟡", "Neutral", _Y

    if key == "adx":
        if val >= 25: return "🔵", "Strong Trend",  _B
        return "🟡", "Weak / Sideways", _Y

    if key in ("sma20_bias", "sma50_bias", "sma200_bias", "ema20_bias", "ema50_bias"):
        if val > 1:  return "🟢", "Above MA", _G
        if val < -1: return "🔴", "Below MA", _R
        return "🟡", "Near MA", _Y

    if key == "atr_pct":
        return "⚪", f"{val:.2f}% vol", _NA

    return "–", str(val), _NA


def overall_signal(ind: dict, chosen: list[str]) -> str:
    bulls, bears = 0, 0
    for key in chosen:
        emoji, _, _ = get_signal(key, ind.get(key))
        if emoji == "🟢": bulls += 1
        elif emoji == "🔴": bears += 1
    total = bulls + bears
    if total == 0: return "🟡 Neutral"
    r = bulls / total
    if r >= 0.6: return "🟢 Bullish"
    if r <= 0.4: return "🔴 Bearish"
    return "🟡 Mixed"


# ── AI helpers ────────────────────────────────────────────────────────────────

def build_prompt(symbol: str, ind: dict, tf_label: str,
                 duration_label: str, chosen_keys: list[str]) -> str:
    price, prev = ind["price"], ind["prev"]
    chg_pct = ((price - prev) / prev * 100) if (price and prev) else None

    lines = [
        f"You are an expert Indian equity market technical analyst.",
        f"Analyse the following snapshot for {symbol} and provide an actionable summary.",
        f"",
        f"Symbol: {symbol}  |  Timeframe: {tf_label}  |  Duration: {duration_label}",
        f"Price: {price:,.2f}" + (f"  |  Change: {chg_pct:+.2f}%" if chg_pct else ""),
        f"Session OHLC: O={ind['last_open']:.2f}  H={ind['last_high']:.2f}"
        f"  L={ind['last_low']:.2f}  C={price:.2f}",
        f"Period High: {ind['high_period']:.2f}  |  Period Low: {ind['low_period']:.2f}",
        f"Volume: {ind['last_vol']:,.0f}  (20-period avg: {ind['avg_vol20']:,.0f})",
        "",
        "=== Selected Indicators ===",
    ]
    for key in chosen_keys:
        if key not in INDICATOR_META:
            continue
        label, _, fmt = INDICATOR_META[key]
        val = ind.get(key)
        if val is None:
            lines.append(f"{label}: N/A")
        else:
            emoji, sig, _ = get_signal(key, val)
            try:
                formatted = fmt.format(val)
            except Exception:
                formatted = str(val)
            lines.append(f"{label}: {formatted}  →  {emoji} {sig}")

    lines += [
        "",
        "Please provide:",
        "1. **Overall Bias** — Bullish / Bearish / Neutral (1 sentence)",
        "2. **Key Signals** — most important indicators and what they indicate (3-5 bullets)",
        "3. **Caution Flags** — conflicting signals or risks (2-3 bullets)",
        "4. **Short-term outlook** — what to watch for next (2-3 bullets)",
        "",
        "Be concise, analytical, and avoid generic disclaimers.",
    ]
    return "\n".join(lines)


@st.cache_data(ttl=300, show_spinner=False)
def get_ai_analysis(cache_key: str, prompt: str) -> str:
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "⚠️ ANTHROPIC_API_KEY not found in .env"
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ── Data loading with batch progress ─────────────────────────────────────────

def load_data(fyers_sym: str, start, end, resolution: str,
              label: str, prog_slot, status_slot) -> pd.DataFrame:
    def _on_chunk(done, total):
        if total > 1:
            status_slot.caption(f"Fetching {label}: batch {done}/{total}…")
            prog_slot.progress(done / total)

    df = get_history(fyers_sym, str(start), str(end),
                     resolution=resolution, on_chunk=_on_chunk)
    status_slot.empty()
    prog_slot.empty()
    return df


# ── Tab 1: Index Analysis ─────────────────────────────────────────────────────

def render_index_tab(resolution, days, warmup, chosen_keys, tf_label, duration_label):
    # Index selector at top of tab
    idx_labels = [lbl for lbl, _ in INDICES]
    idx_syms   = [sym for _, sym in INDICES]
    sel = st.selectbox(
        "Select Index",
        options=range(len(idx_labels)),
        index=0,
        format_func=lambda i: idx_labels[i],
        key="tab1_symbol",
        help="Type to search. All major NSE/BSE indices included.",
    )
    symbol_label = idx_labels[sel]
    symbol_fyers = idx_syms[sel]

    today = datetime.date.today()
    start = today - datetime.timedelta(days=days + warmup)
    end   = today

    prog_slot, status_slot = st.empty(), st.empty()
    try:
        df = load_data(symbol_fyers, start, end, resolution,
                       symbol_label, prog_slot, status_slot)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return

    if df.empty:
        st.error(f"No data returned for {symbol_fyers}.")
        return

    st.caption(
        f"Cached: **{df.index[0].strftime('%Y-%m-%d %H:%M')}** → "
        f"**{df.index[-1].strftime('%Y-%m-%d %H:%M')}**  ({len(df)} candles)"
    )

    ind = compute_indicators(df)
    price, prev = ind["price"], ind["prev"]
    chg   = (price - prev) if (price and prev) else None
    chg_p = (chg / prev * 100) if (chg is not None and prev) else None

    # ── Section A: Base Data ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📌 Base Data")

    r1 = st.columns(5)
    r1[0].metric("Last Price",
                 f"{price:,.2f}" if price else "–",
                 delta=f"{chg:+.2f} ({chg_p:+.2f}%)" if chg is not None else None)
    r1[1].metric("Open",   f"{ind['last_open']:,.2f}")
    r1[2].metric("High",   f"{ind['last_high']:,.2f}")
    r1[3].metric("Low",    f"{ind['last_low']:,.2f}")
    vol, avg = ind["last_vol"], ind["avg_vol20"]
    r1[4].metric("Volume",
                 f"{vol/1e6:.2f}M" if vol > 1e6 else f"{vol:,.0f}",
                 delta=f"vs 20-avg: {(vol/avg - 1)*100:+.1f}%" if avg else None)

    r2 = st.columns(3)
    ph, pl = ind["high_period"], ind["low_period"]
    r2[0].metric("Period High", f"{ph:,.2f}" if ph else "–")
    r2[1].metric("Period Low",  f"{pl:,.2f}" if pl else "–")
    dist = ((price - ph) / ph * 100) if (price and ph) else None
    r2[2].metric("From Period High", f"{dist:.1f}%" if dist is not None else "–")

    # MA summary table (always shown)
    st.markdown("**Moving Averages**")
    ma_defs = [
        ("SMA 20",  "sma20",  "sma20_bias"),
        ("SMA 50",  "sma50",  "sma50_bias"),
        ("SMA 200", "sma200", "sma200_bias"),
        ("EMA 20",  "ema20",  "ema20_bias"),
        ("EMA 50",  "ema50",  "ema50_bias"),
    ]
    ma_rows = []
    for name, val_key, bias_key in ma_defs:
        val  = ind.get(val_key)
        bias = ind.get(bias_key)
        emoji, sig, _ = get_signal(bias_key, bias)
        ma_rows.append({
            "MA":       name,
            "Value":    f"{val:,.2f}" if val else "–",
            "Bias":     f"{bias:+.2f}%" if bias is not None else "–",
            "Signal":   f"{emoji} {sig}",
        })
    st.dataframe(pd.DataFrame(ma_rows), hide_index=True, use_container_width=True)

    # BB row
    bbu, bbm, bbd = ind["bb_up"], ind["bb_mid"], ind["bb_dn"]
    bb_p = ind["bb_pct"]
    st.markdown("**Bollinger Bands (20, 2)**")
    bc = st.columns(4)
    bc[0].metric("Upper", f"{bbu:,.2f}" if bbu else "–")
    bc[1].metric("Middle", f"{bbm:,.2f}" if bbm else "–")
    bc[2].metric("Lower",  f"{bbd:,.2f}" if bbd else "–")
    if bb_p is not None:
        emoji, sig, _ = get_signal("bb_pct", bb_p)
        bc[3].metric("BB %B", f"{bb_p:.1f}%", delta=f"{emoji} {sig}", delta_color="off")
    else:
        bc[3].metric("BB %B", "–")

    # ── Section B: Indicator Analysis ────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Indicator Analysis")

    if not chosen_keys:
        st.info("No indicators selected. Use the sidebar multiselect to add indicators.")
    else:
        # Group by category
        by_cat: dict[str, list[str]] = {}
        for key in chosen_keys:
            if key in INDICATOR_META:
                _, cat, _ = INDICATOR_META[key]
                by_cat.setdefault(cat, []).append(key)

        for cat, keys in by_cat.items():
            st.markdown(f"**{cat}**")
            n = min(len(keys), 4)
            cols = st.columns(n)
            for col, key in zip(cols, keys):
                label, _, fmt = INDICATOR_META[key]
                val = ind.get(key)
                if val is None:
                    col.metric(label, "N/A")
                else:
                    emoji, sig, _ = get_signal(key, val)
                    try:
                        formatted = fmt.format(val)
                    except Exception:
                        formatted = str(val)
                    col.metric(label, formatted,
                               delta=f"{emoji} {sig}", delta_color="off")

        # Consolidated indicator table
        with st.expander("View all selected indicators as table"):
            rows = []
            for key in chosen_keys:
                if key not in INDICATOR_META:
                    continue
                label, cat, fmt = INDICATOR_META[key]
                val = ind.get(key)
                if val is not None:
                    emoji, sig, _ = get_signal(key, val)
                    try:
                        formatted = fmt.format(val)
                    except Exception:
                        formatted = str(val)
                    rows.append({
                        "Category": cat,
                        "Indicator": label,
                        "Value": formatted,
                        "Signal": f"{emoji} {sig}",
                    })
                else:
                    rows.append({
                        "Category": cat,
                        "Indicator": label,
                        "Value": "N/A",
                        "Signal": "–",
                    })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # ── Section C: AI Analysis ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🤖 AI Analysis")

    if st.button("Get AI Analysis", key="tab1_ai", use_container_width=True,
                 type="primary"):
        if not chosen_keys:
            st.warning("Select at least one indicator in the sidebar before running AI analysis.")
        else:
            prompt    = build_prompt(symbol_label, ind, tf_label, duration_label, chosen_keys)
            cache_key = f"{symbol_fyers}|{resolution}|{days}|{'_'.join(sorted(chosen_keys))}"
            with st.spinner("Asking Claude…"):
                analysis = get_ai_analysis(cache_key, prompt)
            st.markdown(analysis)
            with st.expander("View prompt sent to Claude"):
                st.code(prompt)
    else:
        st.info("Click **Get AI Analysis** above after selecting indicators.")


# ── Tab 2: Nifty 50 Stocks Screener ──────────────────────────────────────────

def _fmt(val, fmt_str: str) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "–"
    try:
        return fmt_str.format(val)
    except Exception:
        return str(val)


def render_stocks_tab(resolution, days, warmup, chosen_keys, tf_label, duration_label):
    stocks = load_nifty50_symbols()
    if not stocks:
        st.error("Could not load Nifty 50 tickers. Check nifty50_tickers.csv.")
        return

    today = datetime.date.today()
    start = today - datetime.timedelta(days=days + warmup)
    end   = today

    st.caption(
        f"**{len(stocks)} Nifty 50 stocks**  ·  {tf_label}  ·  {duration_label}  "
        f"·  Period: {start} → {end}"
    )

    prog   = st.progress(0)
    status = st.empty()
    rows   = []

    for i, sym in enumerate(stocks):
        status.caption(f"Loading {sym} ({i+1}/{len(stocks)})…")
        prog.progress((i + 1) / len(stocks))
        try:
            df = get_history(f"NSE:{sym}-EQ", str(start), str(end),
                             resolution=resolution)
            if df.empty:
                rows.append({"Stock": sym, "Price": None, "Chg %": None,
                             **{k: None for k in chosen_keys}, "Signal": "–"})
                continue
            ind   = compute_indicators(df)
            price = ind["price"]
            prev  = ind["prev"]
            chg_p = ((price - prev) / prev * 100) if (price and prev) else None
            row   = {"Stock": sym, "Price": price, "Chg %": chg_p}
            for key in chosen_keys:
                row[key] = ind.get(key)
            row["Signal"] = overall_signal(ind, chosen_keys)
            rows.append(row)
        except Exception:
            rows.append({"Stock": sym, "Price": None, "Chg %": None,
                         **{k: None for k in chosen_keys}, "Signal": "⚠️ Error"})

    status.empty()
    prog.empty()

    if not rows:
        st.warning("No data loaded.")
        return

    df_raw = pd.DataFrame(rows)

    # ── Indicator table ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Indicators — All Nifty 50 Stocks")

    # Build display DataFrame
    col_rename = {"Stock": "Stock", "Price": "Price", "Chg %": "Chg %", "Signal": "Signal"}
    for key in chosen_keys:
        if key in INDICATOR_META:
            col_rename[key] = INDICATOR_META[key][0]

    df_disp = df_raw.rename(columns=col_rename).copy()

    # Format columns
    if "Price" in df_disp.columns:
        df_disp["Price"] = df_disp["Price"].apply(lambda v: _fmt(v, "{:,.2f}"))
    if "Chg %" in df_disp.columns:
        df_disp["Chg %"] = df_disp["Chg %"].apply(lambda v: _fmt(v, "{:+.2f}%"))
    for key in chosen_keys:
        if key in INDICATOR_META:
            col = INDICATOR_META[key][0]
            if col in df_disp.columns:
                df_disp[col] = df_raw[key].apply(
                    lambda v, f=INDICATOR_META[key][2]: _fmt(v, f)
                )

    # Style helper — parses the formatted string back to float for coloring
    def _parse(s: str) -> float | None:
        if s in ("–", "", None):
            return None
        try:
            return float(s.replace("%", "").replace("+", "").replace(",", ""))
        except ValueError:
            return None

    def _col_style(series: pd.Series, key: str):
        out = []
        for v in series:
            num = _parse(str(v))
            _, _, css = get_signal(key, num)
            out.append(css)
        return out

    def _chg_style(series: pd.Series):
        out = []
        for v in series:
            num = _parse(str(v))
            if num is None:
                out.append("")
            elif num > 0:
                out.append(_G)
            elif num < 0:
                out.append(_R)
            else:
                out.append("")
        return out

    styler = df_disp.style
    if "Chg %" in df_disp.columns:
        styler = styler.apply(_chg_style, subset=["Chg %"])
    for key in chosen_keys:
        if key in INDICATOR_META:
            col = INDICATOR_META[key][0]
            if col in df_disp.columns:
                styler = styler.apply(_col_style, key=key, subset=[col])

    st.dataframe(
        styler,
        use_container_width=True,
        hide_index=True,
        height=min(len(rows) * 36 + 40, 700),
    )

    # ── Market Breadth ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📈 Market Breadth")

    signal_counts = df_raw["Signal"].value_counts()
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("🟢 Bullish", int(signal_counts.get("🟢 Bullish", 0)))
    b2.metric("🔴 Bearish", int(signal_counts.get("🔴 Bearish", 0)))
    b3.metric("🟡 Mixed",   int(signal_counts.get("🟡 Mixed",   0)))
    b4.metric("Total Loaded", len(rows))

    # Per-indicator breadth breakdown
    if chosen_keys:
        with st.expander("Indicator-wise signal distribution"):
            bread_rows = []
            for key in chosen_keys:
                if key not in INDICATOR_META:
                    continue
                label = INDICATOR_META[key][0]
                g = r = y = 0
                for row in rows:
                    v = row.get(key)
                    emoji, _, _ = get_signal(key, v)
                    if emoji == "🟢":   g += 1
                    elif emoji == "🔴": r += 1
                    elif emoji in ("🟡", "🔵"): y += 1
                bread_rows.append({
                    "Indicator": label,
                    "🟢 Bull": g,
                    "🔴 Bear": r,
                    "🟡 Neutral": y,
                    "Bull %": f"{g/len(rows)*100:.0f}%" if rows else "–",
                })
            st.dataframe(pd.DataFrame(bread_rows), hide_index=True,
                         use_container_width=True)

    # ── AI Breadth Analysis ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🤖 AI Breadth Analysis")

    if st.button("Analyse Nifty 50 with AI", key="tab2_ai",
                 use_container_width=True, type="primary"):
        ind_names = ", ".join(
            INDICATOR_META[k][0] for k in chosen_keys if k in INDICATOR_META
        ) or "none"
        bull_n = int(signal_counts.get("🟢 Bullish", 0))
        bear_n = int(signal_counts.get("🔴 Bearish", 0))
        mix_n  = int(signal_counts.get("🟡 Mixed",   0))

        summary_lines = [
            f"Nifty 50 Stocks — Technical Breadth Snapshot",
            f"Timeframe: {tf_label}  |  Duration: {duration_label}",
            f"Indicators used: {ind_names}",
            f"",
            f"Overall: {bull_n} Bullish, {bear_n} Bearish, {mix_n} Mixed "
            f"(out of {len(rows)} stocks)",
            "",
            "Stock-by-stock data:",
            "Stock | Price | Chg% | " + " | ".join(
                INDICATOR_META[k][0] for k in chosen_keys[:6] if k in INDICATOR_META
            ) + " | Signal",
        ]
        for row in rows:
            parts = [row["Stock"]]
            if row.get("Price"):
                parts.append(f"{row['Price']:.1f}")
            if row.get("Chg %") is not None:
                parts.append(f"{row['Chg %']:+.1f}%")
            for key in chosen_keys[:6]:
                v = row.get(key)
                if v is not None:
                    emoji, _, _ = get_signal(key, v)
                    parts.append(f"{v:.1f}{emoji}")
                else:
                    parts.append("–")
            parts.append(row.get("Signal", ""))
            summary_lines.append("  ".join(parts))

        summary_lines += [
            "",
            "Based on this Nifty 50 breadth data please provide:",
            "1. **Market Pulse** — overall market sentiment (2-3 sentences)",
            "2. **Strong Stocks** — 3-5 stocks showing clear bullish signals",
            "3. **Weak Stocks** — 3-5 stocks showing bearish or oversold risk",
            "4. **Sector Patterns** — any theme you notice across the 50 stocks",
            "5. **Trading Outlook** — 3 actionable bullets for a swing trader",
        ]
        prompt    = "\n".join(summary_lines)
        cache_key = f"n50|{resolution}|{days}|{'_'.join(sorted(chosen_keys[:6]))}"
        with st.spinner("Asking Claude to analyse all 50 stocks…"):
            analysis = get_ai_analysis(cache_key, prompt)
        st.markdown(analysis)
        with st.expander("View data sent to Claude"):
            st.code(prompt)
    else:
        st.info("Click the button above for Claude's analysis of all 50 Nifty stocks.")


# ═════════════════════════════════════════════════════════════════════════════
# Page layout
# ═════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Market Pulse", page_icon="📊", layout="wide")
st.title("📊 Market Pulse")
st.caption("NSE Index deep-dive · Nifty 50 stocks screener · AI analysis")

# ── Shared sidebar ────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    tf_label = st.selectbox(
        "Timeframe",
        options=list(TIMEFRAMES.keys()),
        index=6,  # Day
        help="Candle size. Intraday data is fetched in batches automatically.",
    )
    resolution, _max_days, _warmup = TIMEFRAMES[tf_label]

    dur_opts   = DURATION_OPTIONS[tf_label]
    dur_labels = [l for l, _ in dur_opts]
    dur_days   = {l: d for l, d in dur_opts}
    default_d  = min(DURATION_DEFAULT[tf_label], len(dur_opts) - 1)
    duration_label = st.selectbox("Duration", options=dur_labels, index=default_d)
    days = dur_days[duration_label]

    chunks_est = max(1, math.ceil((days + _warmup) / _max_days))
    if chunks_est > 1:
        st.caption(
            f"ℹ️ ~{chunks_est} API batches needed per symbol. "
            "Cached data reused automatically."
        )

    st.divider()

    st.markdown("**📐 Choose Indicators**")
    st.caption(
        "Selected indicators appear in Tab 1 metrics and Tab 2 table columns. "
        "Changing this affects both tabs and the AI analysis."
    )
    chosen_keys = st.multiselect(
        "Indicators",
        options=list(INDICATOR_META.keys()),
        default=DEFAULT_INDICATORS,
        format_func=lambda k: f"{INDICATOR_META[k][1]} · {INDICATOR_META[k][0]}",
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("Data cached in SQLite. First load fetches from Fyers; after that instant.")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 Index Analysis", "📋 Nifty 50 Stocks"])

with tab1:
    render_index_tab(resolution, days, _warmup, chosen_keys, tf_label, duration_label)

with tab2:
    render_stocks_tab(resolution, days, _warmup, chosen_keys, tf_label, duration_label)
