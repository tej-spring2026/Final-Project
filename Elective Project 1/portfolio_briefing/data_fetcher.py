"""
data_fetcher.py — Portfolio Intelligence Briefing System
Data layer: all external API calls. No synthesis logic lives here.

Functions:
    get_price_data(tickers)       — yfinance: prices, day change, 2-day history
    get_portfolio_pnl(price_data) — per-position and total P&L from PORTFOLIO config
    get_macro_data(price_data)    — SPY, QQQ, VIX, ^TNX snapshots
    get_finnhub_news(tickers)     — Finnhub REST: top N articles per ticker, last 7 days
    get_analyst_signals(tickers)  — yfinance: mean/high/low targets + recommendation key
    get_crypto_data()             — CoinGecko: BTC + ETH price, 24hr change, dominance
"""

import os
import time
import datetime
import requests
import yfinance as yf
from dotenv import load_dotenv

from config import (
    PORTFOLIO,
    EQUITY_TICKERS,
    CRYPTO_PROXIES,
    BENCHMARKS,
    FINNHUB_NEWS_DAYS,
    FINNHUB_NEWS_PER_TICKER,
    FINNHUB_NEWS_TICKERS,
)

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


# ============================================================================
# PRICE DATA  (yfinance)
# ============================================================================

def get_price_data(tickers):
    """
    Fetch current price and 1-day change for a list of equity tickers.

    Uses a 5-day window so we always have at least 2 trading-day closes,
    then extracts the two most recent closes to compute the day change.

    Args:
        tickers: list of ticker strings (e.g. ["TSLA", "NVDA", "SPY"])

    Returns:
        dict: {
            ticker: {
                "current_price": float,
                "prev_close":    float,
                "day_change":    float,   # dollars
                "day_change_pct": float,  # percent, e.g. -1.23
            },
            ...
        }
        Tickers that fail to fetch are silently omitted.
    """
    result = {}
    if not tickers:
        return result

    try:
        # Download 5 days so weekends/holidays don't leave us with only 1 row
        raw = yf.download(
            tickers,
            period="5d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        print(f"[data_fetcher] yfinance download error: {e}")
        return result

    if raw.empty:
        print("[data_fetcher] yfinance returned empty data.")
        return result

    # yfinance returns a MultiIndex when multiple tickers are passed,
    # but a flat DataFrame for a single ticker.
    close = raw["Close"] if "Close" in raw.columns else raw

    # Normalise to a dict-of-Series regardless of single vs multi ticker
    if hasattr(close, "columns"):
        # Multiple tickers → DataFrame; each column is one ticker
        series_map = {col: close[col].dropna() for col in close.columns}
    else:
        # Single ticker → Series
        series_map = {tickers[0]: close.dropna()}

    for ticker, series in series_map.items():
        if len(series) < 2:
            continue
        current_price = float(series.iloc[-1])
        prev_close    = float(series.iloc[-2])
        day_change    = current_price - prev_close
        day_change_pct = (day_change / prev_close * 100) if prev_close else 0.0

        result[ticker] = {
            "current_price":  round(current_price, 4),
            "prev_close":     round(prev_close, 4),
            "day_change":     round(day_change, 4),
            "day_change_pct": round(day_change_pct, 4),
        }

    return result


# ============================================================================
# PORTFOLIO P&L  (derived from price_data + PORTFOLIO config)
# ============================================================================

def get_portfolio_pnl(price_data):
    """
    Calculate per-position and total portfolio P&L for the day.

    For direct crypto holdings (BTC, ETH) this function expects their
    prices to be included in price_data (populated from get_crypto_data).

    Args:
        price_data: dict returned by get_price_data (and augmented with
                    crypto prices before calling this function)

    Returns:
        dict: {
            "positions": [
                {
                    "ticker":           str,
                    "shares":           float,
                    "avg_cost":         float,
                    "current_price":    float,
                    "market_value":     float,
                    "cost_basis":       float,
                    "unrealized_gain":  float,
                    "unrealized_pct":   float,
                    "day_change_dollar": float,
                    "day_change_pct":   float,
                },
                ...  sorted by abs(day_change_dollar) descending
            ],
            "total_market_value":     float,
            "total_cost_basis":       float,
            "total_unrealized_gain":  float,
            "total_unrealized_pct":   float,
            "total_day_change_dollar": float,
            "total_day_change_pct":   float,
        }
    """
    positions = []
    total_market_value = 0.0
    total_cost_basis   = 0.0
    total_day_change   = 0.0

    for ticker, cfg in PORTFOLIO.items():
        shares   = cfg["shares"]
        avg_cost = cfg["avg_cost"]

        if ticker not in price_data:
            # Ticker failed to fetch; skip silently
            continue

        pd_entry    = price_data[ticker]
        cur_price   = pd_entry["current_price"]
        day_chg_pct = pd_entry["day_change_pct"]

        market_value     = shares * cur_price
        cost_basis       = shares * avg_cost
        unrealized_gain  = market_value - cost_basis
        unrealized_pct   = (unrealized_gain / cost_basis * 100) if cost_basis else 0.0
        day_change_dollar = shares * pd_entry["day_change"]

        positions.append({
            "ticker":             ticker,
            "shares":             shares,
            "avg_cost":           avg_cost,
            "current_price":      cur_price,
            "market_value":       round(market_value, 2),
            "cost_basis":         round(cost_basis, 2),
            "unrealized_gain":    round(unrealized_gain, 2),
            "unrealized_pct":     round(unrealized_pct, 2),
            "day_change_dollar":  round(day_change_dollar, 2),
            "day_change_pct":     round(day_chg_pct, 2),
        })

        total_market_value += market_value
        total_cost_basis   += cost_basis
        total_day_change   += day_change_dollar

    # Sort by absolute day dollar impact (biggest movers first)
    positions.sort(key=lambda x: abs(x["day_change_dollar"]), reverse=True)

    total_unrealized     = total_market_value - total_cost_basis
    total_unrealized_pct = (total_unrealized / total_cost_basis * 100) if total_cost_basis else 0.0
    total_day_pct        = (total_day_change / (total_market_value - total_day_change) * 100) \
                           if (total_market_value - total_day_change) else 0.0

    return {
        "positions":               positions,
        "total_market_value":      round(total_market_value, 2),
        "total_cost_basis":        round(total_cost_basis, 2),
        "total_unrealized_gain":   round(total_unrealized, 2),
        "total_unrealized_pct":    round(total_unrealized_pct, 2),
        "total_day_change_dollar": round(total_day_change, 2),
        "total_day_change_pct":    round(total_day_pct, 2),
    }


# ============================================================================
# MACRO DATA  (extracted from price_data)
# ============================================================================

def get_macro_data(price_data):
    """
    Extract macro benchmark snapshots from price_data.

    Benchmarks: SPY (S&P 500 proxy), QQQ (Nasdaq proxy), VIX, ^TNX (10yr yield).
    SPY and QQQ are also held positions; we use the same price_data dict.

    Args:
        price_data: dict returned by get_price_data (must include BENCHMARKS)

    Returns:
        dict: {
            "SPY":  {"current_price": float, "day_change_pct": float},
            "QQQ":  {...},
            "VIX":  {"current_price": float, "day_change_pct": float},
            "TNX":  {"current_price": float, "day_change_pct": float},  # 10yr yield %
        }
    """
    macro = {}
    label_map = {"^TNX": "TNX", "^VIX": "VIX"}  # clean up carets for display

    for ticker in BENCHMARKS:
        label = label_map.get(ticker, ticker)
        if ticker in price_data:
            entry = price_data[ticker]
            macro[label] = {
                "current_price":  entry["current_price"],
                "day_change_pct": entry["day_change_pct"],
            }
        else:
            print(f"[data_fetcher] Macro ticker not in price_data: {ticker}")

    return macro


# ============================================================================
# FINNHUB NEWS
# ============================================================================

def get_finnhub_news(tickers=None):
    """
    Fetch recent company news from Finnhub for a list of tickers.

    Uses a 7-day look-back window. Returns up to FINNHUB_NEWS_PER_TICKER
    articles per ticker. Sleeps 0.5s between requests to respect the
    60 req/min free-tier rate limit.

    For crypto proxy tickers (GBTC, ETHE, MSTR) the function also fetches
    BTC and ETH news from Finnhub's crypto news endpoint to provide
    additional context on what is driving those positions.

    Args:
        tickers: list of tickers (defaults to FINNHUB_NEWS_TICKERS from config)

    Returns:
        dict: {
            ticker: [
                {
                    "headline": str,
                    "summary":  str,
                    "source":   str,
                    "url":      str,
                    "datetime": str,  # ISO format
                },
                ...
            ],
            ...
        }
    """
    if not FINNHUB_API_KEY:
        print("[data_fetcher] FINNHUB_API_KEY not set — skipping news fetch.")
        return {}

    if tickers is None:
        tickers = FINNHUB_NEWS_TICKERS

    today      = datetime.date.today()
    from_date  = (today - datetime.timedelta(days=FINNHUB_NEWS_DAYS)).strftime("%Y-%m-%d")
    to_date    = today.strftime("%Y-%m-%d")

    news_data  = {}
    fetch_list = list(tickers)

    # Note: Finnhub free tier blocks crypto exchange symbols (BINANCE:BTCUSDT).
    # Crypto context for GBTC/ETHE/MSTR comes from CoinGecko data instead.

    for ticker in fetch_list:
        try:
            resp = requests.get(
                f"{FINNHUB_BASE_URL}/company-news",
                params={
                    "symbol": ticker,
                    "from":   from_date,
                    "to":     to_date,
                    "token":  FINNHUB_API_KEY,
                },
                timeout=10,
            )
            resp.raise_for_status()
            articles = resp.json()

            if isinstance(articles, list) and articles:
                cleaned = []
                for art in articles[:FINNHUB_NEWS_PER_TICKER]:
                    dt_str = ""
                    try:
                        dt_str = datetime.datetime.utcfromtimestamp(
                            art.get("datetime", 0)
                        ).strftime("%Y-%m-%d %H:%M UTC")
                    except Exception:
                        pass

                    cleaned.append({
                        "headline": art.get("headline", ""),
                        "summary":  art.get("summary", ""),
                        "source":   art.get("source", ""),
                        "url":      art.get("url", ""),
                        "datetime": dt_str,
                    })

                news_data[ticker] = cleaned

        except requests.exceptions.RequestException as e:
            print(f"[data_fetcher] Finnhub news error for {ticker}: {e}")

        time.sleep(0.5)  # respect 60 req/min rate limit

    return news_data


# ============================================================================
# ANALYST SIGNALS  (yfinance)
# ============================================================================

def get_analyst_signals(tickers=None):
    """
    Fetch analyst price targets and recommendation key from yfinance.

    Skips ETFs and direct crypto tickers (no analyst coverage).

    Args:
        tickers: list of tickers (defaults to EQUITY_TICKERS minus ETFs/crypto)

    Returns:
        dict: {
            ticker: {
                "target_mean":  float or None,
                "target_high":  float or None,
                "target_low":   float or None,
                "recommendation": str or None,  # e.g. "buy", "hold", "sell"
                "current_price": float or None,
                "upside_pct":    float or None,  # vs mean target
            },
            ...
        }
    """
    # ETFs and benchmarks have no analyst targets
    skip = {"SPY", "QQQ", "ARKK", "ARKW", "IWF", "VIX", "^TNX",
            "GBTC", "ETHE", "BTC", "ETH"}

    if tickers is None:
        tickers = [t for t in EQUITY_TICKERS if t not in skip]

    signals = {}

    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info

            target_mean = info.get("targetMeanPrice")
            target_high = info.get("targetHighPrice")
            target_low  = info.get("targetLowPrice")
            rec         = info.get("recommendationKey")
            cur_price   = info.get("currentPrice") or info.get("regularMarketPrice")

            upside = None
            if target_mean and cur_price:
                upside = round((target_mean - cur_price) / cur_price * 100, 1)

            signals[ticker] = {
                "target_mean":    round(target_mean, 2) if target_mean else None,
                "target_high":    round(target_high, 2) if target_high else None,
                "target_low":     round(target_low, 2)  if target_low  else None,
                "recommendation": rec,
                "current_price":  round(cur_price, 2)   if cur_price   else None,
                "upside_pct":     upside,
            }

        except Exception as e:
            print(f"[data_fetcher] Analyst signal error for {ticker}: {e}")

        time.sleep(0.3)  # gentle on Yahoo Finance

    return signals


# ============================================================================
# CRYPTO DATA  (CoinGecko — no API key required)
# ============================================================================

def get_crypto_data():
    """
    Fetch BTC and ETH price, 24hr change, and market dominance from CoinGecko.

    Also fetches market-cap dominance and total crypto market cap for macro
    context on the GBTC, ETHE, and MSTR proxy positions.

    No API key required. Respects the 30 req/min free-tier limit.

    Returns:
        dict: {
            "BTC": {
                "current_price":  float,
                "day_change_pct": float,
                "market_cap":     float,
                "dominance_pct":  float,
            },
            "ETH": {
                "current_price":  float,
                "day_change_pct": float,
                "market_cap":     float,
            },
            "total_crypto_market_cap": float,
            "btc_dominance_pct":       float,
        }
        Returns empty dict on failure.
    """
    result = {}

    # --- Price + 24hr change for BTC and ETH ---
    try:
        resp = requests.get(
            f"{COINGECKO_BASE_URL}/simple/price",
            params={
                "ids":                  "bitcoin,ethereum",
                "vs_currencies":        "usd",
                "include_24hr_change":  "true",
                "include_market_cap":   "true",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        btc = data.get("bitcoin", {})
        eth = data.get("ethereum", {})

        result["BTC"] = {
            "current_price":  btc.get("usd", 0),
            "day_change_pct": round(btc.get("usd_24h_change", 0), 2),
            "market_cap":     btc.get("usd_market_cap", 0),
        }
        result["ETH"] = {
            "current_price":  eth.get("usd", 0),
            "day_change_pct": round(eth.get("usd_24h_change", 0), 2),
            "market_cap":     eth.get("usd_market_cap", 0),
        }

    except requests.exceptions.RequestException as e:
        print(f"[data_fetcher] CoinGecko price error: {e}")
        return result

    # --- Global crypto market cap and BTC dominance ---
    try:
        time.sleep(0.5)
        resp = requests.get(f"{COINGECKO_BASE_URL}/global", timeout=10)
        resp.raise_for_status()
        global_data = resp.json().get("data", {})

        btc_dom   = global_data.get("market_cap_percentage", {}).get("btc", 0)
        total_cap = global_data.get("total_market_cap", {}).get("usd", 0)

        result["total_crypto_market_cap"] = total_cap
        result["btc_dominance_pct"]       = round(btc_dom, 1)
        if "BTC" in result:
            result["BTC"]["dominance_pct"] = round(btc_dom, 1)

    except requests.exceptions.RequestException as e:
        print(f"[data_fetcher] CoinGecko global data error: {e}")

    return result
