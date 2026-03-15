# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in broker credentials
```

Always use `.venv/bin/python` — never the system Python.

## Running Scripts

Every script is standalone and runs independently:

```bash
.venv/bin/python stock_data/main_indicators_streamlit.py
streamlit run stock_data/main_indicators_streamlit.py   # Streamlit web UI
.venv/bin/python portfolio_strategies/trading_bot.py    # broker-agnostic trading bot
.venv/bin/python refresh_tickers.py                     # regenerate Indian market CSVs
```

There is no build system, test suite, or linter configured for this project.

## Architecture

The repo is organized as a **research toolkit** — 150+ standalone scripts grouped by purpose. There is no central application entry point or shared state.

```
Finance/
├── .env                     # All credentials (gitignored)
├── ta_functions.py          # Shared: 40+ technical indicator calculations
├── tickers.py               # Shared: Indian market ticker fetchers (NSE/BSE)
├── refresh_tickers.py       # Regenerates nifty50/nse/sensex CSV files from live data
├── config/                  # Per-broker settings, all loaded from .env via python-dotenv
├── brokers/                 # Broker abstraction layer (see below)
├── stock_data/              # Data collection — APIs and web scraping
├── find_stocks/             # Stock screening by technical/fundamental criteria
├── stock_analysis/          # DCF valuation, backtesting, sentiment, regression
├── machine_learning/        # Predictive models: LSTM, Prophet, ARIMA, sklearn
├── portfolio_strategies/    # Trading strategies, portfolio optimization, Monte Carlo
└── technical_indicators/    # Visualization of individual indicators (one file per indicator)
```

### Shared utilities

Scripts in subdirectories import shared utilities via `sys.path.append` to reach the repo root, then import `ta_functions` and `tickers` directly. When editing these shared files, be aware that changes affect all callers across every module.

### Broker abstraction layer

`brokers/` and `config/` provide a unified multi-broker trading interface:

```
config/
├── broker_config.py     # Reads ACTIVE_BROKER from .env ("fyers", "dhan", "robinhood")
├── fyers_config.py      # Fyers credentials loaded from .env
├── dhan_config.py       # Dhan credentials loaded from .env
└── robinhood_config.py  # Robinhood credentials loaded from .env

brokers/
├── base_broker.py       # Abstract interface: login, get_holdings, buy_market, sell_market, cancel_all_orders
├── fyers_broker.py      # Fyers implementation (fyers-apiv3)
├── dhan_broker.py       # Dhan implementation (dhanhq 2.x)
├── robinhood_broker.py  # Robinhood implementation (robin_stocks)
├── fyers_auth.py        # TOTP-based auto-login — no manual token needed
└── __init__.py          # get_broker() factory — returns the active broker instance
```

**Switching brokers:** change `ACTIVE_BROKER` in `.env` — no code changes needed.

**Fyers auth** runs automatically via TOTP (`pyotp`) each session. Credentials needed in `.env`: `APP_ID`, `FYERS_TOTP_KEY`, `SECRET_KEY`, `FYERS_ID`, `PIN`, `REDIRECT_URI`. No manual OAuth or daily token copy-paste.

**Dhan auth** uses a static access token generated from [api.dhan.co](https://api.dhan.co). Set `DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN` in `.env`. Regenerate the token from the portal when it expires.

`get_holdings()` returns a normalised DataFrame: `ticker`, `security_id`, `quantity`, `average_buy_price`, `current_price`, `percent_change`. Dhan orders require `security_id` (numeric ID from holdings); Fyers uses the full symbol string (`NSE:INFY-EQ`); Robinhood uses the plain ticker.

### Data sources

- **yfinance** — primary source for historical OHLCV and fundamental data
- **Fyers (fyers-apiv3)** — live trading, Indian markets; credentials in `.env`
- **Dhan (dhanhq)** — live trading, Indian markets; credentials in `.env`
- **Robinhood (robin_stocks)** — live trading, US markets; credentials in `.env`
- **Financial Modeling Prep API** — income statements, cash flow (requires API key)
- **Finviz** — web-scraped screening and fundamental data
- **PRAW / Tweepy** — Reddit and Twitter sentiment (require API credentials)
- **Twilio** — SMS alerts (requires API key)

### Output patterns

Scripts output to one or more of: matplotlib/mplfinance plots, CSV files, Streamlit dashboards, console prints, or SMS via Twilio.
