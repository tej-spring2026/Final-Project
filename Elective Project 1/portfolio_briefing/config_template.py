"""
config_template.py — Portfolio Intelligence Briefing System
Central configuration: portfolio holdings, constants, and API settings.
"""

import os

# ============================================================================
# PORTFOLIO HOLDINGS
# Format: ticker -> {shares, avg_cost (per share)}
# ============================================================================

PORTFOLIO = {
    # === MEGA-CAP TECH (CORE) ===
    # Replace with your actual tickers, share counts, and average cost basis
    "TICKER1": {"shares": 100,    "avg_cost": 100.00},
    "TICKER2": {"shares": 50,     "avg_cost": 200.00},
    "TICKER3": {"shares": 75,     "avg_cost": 150.00},
    "TICKER4": {"shares": 60,     "avg_cost": 175.00},
    "TICKER5": {"shares": 200,    "avg_cost": 80.00},
    "TICKER6": {"shares": 120,    "avg_cost": 300.00},
    "TICKER7": {"shares": 30,     "avg_cost": 250.00},

    # === SEMI EQUIPMENT ===
    "TICKER8": {"shares": 40,     "avg_cost": 120.00},
    "TICKER9": {"shares": 15,     "avg_cost": 500.00},
    "TICKER10": {"shares": 10,    "avg_cost": 600.00},
    "TICKER11": {"shares": 200,   "avg_cost": 10.00},

    # === FINTECH / GROWTH ===
    "TICKER12": {"shares": 100,   "avg_cost": 90.00},
    "TICKER13": {"shares": 150,   "avg_cost": 15.00},
    "TICKER14": {"shares": 200,   "avg_cost": 20.00},

    # === CRYPTO PROXIES (all tracked via yfinance; enriched with CoinGecko context) ===
    "GBTC": {"shares": 100,       "avg_cost": 30.00},
    "ETHE": {"shares": 100,       "avg_cost": 25.00},
    "MSTR": {"shares": 10,        "avg_cost": 200.00},
    "BTC":  {"shares": 50,        "avg_cost": 20.00},   # ETF shares, not coins
    "ETH":  {"shares": 50,        "avg_cost": 30.00},   # ETF shares, not coins

    # === HEALTHCARE / OTHER ===
    "TICKER15": {"shares": 10,    "avg_cost": 700.00},
    "TICKER16": {"shares": 50,    "avg_cost": 90.00},
    "TICKER17": {"shares": 100,   "avg_cost": 50.00},

    # === AI / COMPUTE ===
    "TICKER18": {"shares": 40,    "avg_cost": 100.00},
    "TICKER19": {"shares": 30,    "avg_cost": 150.00},
    "TICKER20": {"shares": 100,   "avg_cost": 40.00},
    "TICKER21": {"shares": 100,   "avg_cost": 50.00},
    "TICKER22": {"shares": 80,    "avg_cost": 30.00},

    # === ETFs ===
    "SPY":  {"shares": 10,        "avg_cost": 500.00},
    "ARKK": {"shares": 50,        "avg_cost": 130.00},
    "ARKW": {"shares": 50,        "avg_cost": 155.00},
    "IWF":  {"shares": 20,        "avg_cost": 400.00},
}

# All portfolio tickers fetched via yfinance
EQUITY_TICKERS = list(PORTFOLIO.keys())

# Crypto proxy ETFs — all yfinance tickers that move with BTC/ETH price
# CoinGecko data is pulled separately to provide crypto macro context
CRYPTO_PROXIES = ["GBTC", "ETHE", "MSTR", "BTC", "ETH"]

# Macro benchmarks fetched alongside portfolio (not held positions)
BENCHMARKS = ["SPY", "QQQ", "^VIX", "^TNX"]

# ============================================================================
# FINNHUB NEWS SETTINGS
# ============================================================================

# How many days back to look for news
FINNHUB_NEWS_DAYS = 7

# Max articles returned per ticker
FINNHUB_NEWS_PER_TICKER = 4

# Tickers to fetch news for (skip benchmarks, ETFs, direct crypto, micro-caps
# with limited Finnhub coverage)
FINNHUB_NEWS_TICKERS = [
    # Replace with your actual tickers (skip benchmarks, ETFs, and micro-caps
    # with limited Finnhub coverage)
    "TICKER1", "TICKER2", "TICKER3", "TICKER4", "TICKER5", "TICKER6", "TICKER7",
    "TICKER8", "TICKER9", "TICKER10", "TICKER11",
    "TICKER12", "TICKER13", "TICKER14",
    "GBTC", "ETHE", "MSTR",
    "TICKER15", "TICKER16", "TICKER17",
    "TICKER18", "TICKER20", "TICKER22",
    "SPY", "ARKK",
]

# ============================================================================
# CLAUDE API SETTINGS
# ============================================================================

CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS = 1500

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "briefings")
