# Finance

A collection of 150+ Python programs for Indian stock market analysis, trading strategies, and quantitative finance. Covers everything from data collection and technical indicators to machine learning predictions, portfolio optimization, and live order execution via Fyers and Dhan.

> **Disclaimer:** This repository is for educational purposes only and should not be considered professional investment advice.

---

## Table of Contents

- [Setup](#setup)
- [Broker Configuration](#broker-configuration)
  - [Fyers](#fyers)
  - [Dhan](#dhan)
  - [Robinhood (US markets)](#robinhood-us-markets)
  - [Switching Brokers](#switching-brokers)
- [Running the Trading Bot](#running-the-trading-bot)
- [Project Structure](#project-structure)
- [Module Overview](#module-overview)
- [Indian Market Tickers](#indian-market-tickers)

---

## Setup

**Requirements:** Python 3.12+

```bash
git clone https://github.com/shashankvemuri/Finance.git
cd Finance

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Install openscreener (local package for Screener.in data)
pip install ./openscreener-0.1.0

# Install Playwright browser binaries (one-time, ~90 MB)
playwright install chromium
```

Copy the environment template and fill in your credentials:

```bash
cp .env.example .env   # then edit .env with your broker credentials
```

---

## Broker Configuration

All credentials live in `.env` at the project root. The file is gitignored — never commit it.

### Fyers

Authentication is fully automated via TOTP — no manual browser login or daily token copy-paste required.

**Steps:**
1. Log in at [myapi.fyers.in](https://myapi.fyers.in) and create an app to get your `APP_ID` and `SECRET_KEY`.
2. Go to **My Account → Security → 2FA**, set up TOTP authenticator, and save the 32-character secret as `FYERS_TOTP_KEY`.
3. Fill in `.env`:

```env
APP_ID=QVK3WHLJ1W-100
SECRET_KEY=your_secret_key
FYERS_TOTP_KEY=your_32char_totp_secret
REDIRECT_URI=https://www.google.com/
FYERS_ID=your_fyers_client_id
PIN=your_4digit_pin
```

### Dhan

1. Log in at [api.dhan.co](https://api.dhan.co), create an app, and generate an access token.
2. Fill in `.env`:

```env
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token
```

> Access tokens on Dhan are session-based. Generate a fresh one from the portal before each trading day.

### Robinhood (US markets)

```env
RH_USERNAME=your_username
RH_PASSWORD=your_password
RH_MFA_CODE=                # leave empty if MFA is not enabled
```

### Switching Brokers

Change one line in `.env`:

```env
ACTIVE_BROKER=fyers    # or: dhan, robinhood
```

No code changes needed anywhere else.

---

## Running the Trading Bot

```bash
source .venv/bin/activate
python portfolio_strategies/trading_bot.py
```

The bot reads `ACTIVE_BROKER` from `.env`, authenticates with the configured broker, fetches your holdings, applies buy/sell criteria, and places market orders. Edit the criteria block in `trading_bot.py` to match your strategy.

---

## Project Structure

```
Finance/
│
├── .env                        # Credentials (gitignored — never commit)
│
├── config/                     # Per-broker settings, all loaded from .env
│   ├── broker_config.py        # ACTIVE_BROKER selector
│   ├── fyers_config.py         # Fyers credentials & order defaults
│   ├── dhan_config.py          # Dhan credentials & order defaults
│   └── robinhood_config.py     # Robinhood credentials
│
├── brokers/                    # Broker abstraction layer
│   ├── base_broker.py          # Abstract interface
│   ├── fyers_broker.py         # Fyers implementation
│   ├── dhan_broker.py          # Dhan implementation
│   ├── robinhood_broker.py     # Robinhood implementation
│   ├── fyers_auth.py           # TOTP-based Fyers auto-login
│   └── __init__.py             # get_broker() factory
│
├── openscreener-0.1.0/         # Local package — Screener.in scraper (Playwright-based)
├── ta_functions.py             # 40+ shared technical indicator functions
├── tickers.py                  # Indian market ticker fetchers (NSE/BSE)
├── refresh_tickers.py          # Regenerates ticker CSV files from live data
│
├── stock_data/                 # Data collection via APIs and web scraping
├── find_stocks/                # Stock screeners (technical & fundamental)
├── stock_analysis/             # DCF valuation, backtesting, sentiment, regression
├── machine_learning/           # LSTM, Prophet, ARIMA, sklearn models
├── portfolio_strategies/       # Trading strategies, portfolio optimization
└── technical_indicators/       # Individual indicator visualizations
```

---

## Module Overview

| Module | What it does |
|---|---|
| `stock_data/` | Fetch OHLCV data, dividends, earnings, intraday data, send SMS alerts |
| `find_stocks/` | Screen stocks by RSI, Minervini criteria, fundamentals, sentiment |
| `stock_analysis/` | DCF valuation, CAPM, Kelly criterion, VaR, backtesting all indicators |
| `machine_learning/` | Price prediction with LSTM, Prophet, ARIMA, K-means clustering, PCA |
| `portfolio_strategies/` | Pairs trading, Markowitz optimization, Monte Carlo, moving average strategies |
| `technical_indicators/` | Standalone charts for MACD, RSI, Bollinger Bands, VWAP, ATR, OBV, and more |
| `openscreener-0.1.0/` | Playwright-based scraper for Screener.in — summary, P&L, balance sheet, cash flow, ratios, shareholding |

Every script is standalone — run any of them directly:

```bash
python stock_data/main_indicators_streamlit.py     # Streamlit web UI
streamlit run stock_data/main_indicators_streamlit.py
```

---

## Indian Market Tickers

`tickers.py` provides functions to fetch NSE/BSE ticker lists. To refresh the CSV files:

```bash
python refresh_tickers.py
```

| CSV file | Contents |
|---|---|
| `nifty50_tickers.csv` | Nifty 50 constituents (50 symbols) |
| `nifty500_tickers.csv` | Nifty 500 constituents (500 symbols) |
| `nifty_next50_tickers.csv` | Nifty Next 50 constituents (50 symbols) |
| `nse_tickers.csv` | All NSE-listed equities, EQ series (~2100 symbols) |
| `sensex_tickers.csv` | BSE Sensex 30 constituents (30 symbols) |

Symbols are plain NSE trading symbols (e.g. `INFY`, `RELIANCE`). Append `.NS` for yfinance or use them directly with the Fyers/Dhan broker implementations.

---

## Screener.in Data (openscreener)

`openscreener` is a local Playwright-based package that scrapes structured financial data from [Screener.in](https://www.screener.in/).

```python
from openscreener import Stock, Index

# Single stock — summary, ratios, P&L, balance sheet, cash flow, shareholding
stock = Stock("TCS")
print(stock.summary()["current_price"])
print(stock.ratios()["roce_percent"])
frame = stock.to_dataframe("cash_flow")

# Batch fetch
batch = Stock.batch(["TCS", "INFY", "RELIANCE"])
ratios = batch.fetch("ratios")
print(ratios["INFY"]["roce_percent"])

# Index constituents
index = Index("CNX500")
constituents = index.constituents(limit=100)
```

Available sections: `summary`, `pros_cons`, `peers`, `quarterly_results`, `profit_loss`, `balance_sheet`, `cash_flow`, `ratios`, `shareholding`.
