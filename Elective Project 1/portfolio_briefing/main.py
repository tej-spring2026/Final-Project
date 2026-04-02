"""
main.py — Portfolio Intelligence Briefing System
Entry point: CLI flags, orchestrates fetch -> synthesize -> output.

Usage:
    python main.py                  # intraday briefing
    python main.py --eod            # end-of-day recap mode
    python main.py --ticker PLTR    # single-stock deep dive
    python main.py --history        # list saved briefings
    python main.py --no-save        # run without saving to file
    python main.py --debug          # print prompt before API call
"""

import argparse
import sys
import io

# Force UTF-8 output on Windows so news text with special characters doesn't crash
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from data_fetcher import (
    get_price_data,
    get_portfolio_pnl,
    get_macro_data,
    get_finnhub_news,
    get_analyst_signals,
    get_crypto_data,
)
from synthesizer import build_prompt, synthesize_with_claude
from output_handler import print_briefing, save_briefing, list_saved_briefings
from config import EQUITY_TICKERS, BENCHMARKS, FINNHUB_NEWS_TICKERS


def run_briefing(mode="intraday", ticker=None, no_save=False, debug=False):
    """
    Orchestrates the full fetch -> synthesize -> output pipeline.

    Args:
        mode:    "intraday" or "eod"
        ticker:  single ticker string for deep-dive mode, or None for full portfolio
        no_save: if True, skip writing to file
        debug:   if True, print the prompt before calling Claude
    """
    # --- Determine which tickers to fetch ---
    if ticker:
        # Single-ticker deep-dive: fetch just that ticker + macro benchmarks
        fetch_tickers = [ticker.upper()] + BENCHMARKS
        news_tickers  = [ticker.upper()]
        analyst_tickers = [ticker.upper()]
    else:
        fetch_tickers   = EQUITY_TICKERS + [t for t in BENCHMARKS if t not in EQUITY_TICKERS]
        news_tickers    = FINNHUB_NEWS_TICKERS
        analyst_tickers = None  # defaults to all non-ETF equity tickers in get_analyst_signals

    # ---------------------------------------------------------------
    # STEP 1: Fetch all data
    # ---------------------------------------------------------------
    print("[1/4] Fetching price data...")
    price_data = get_price_data(fetch_tickers)

    if not price_data:
        print("[Error] Could not fetch any price data. Check your internet connection.")
        sys.exit(1)

    # CoinGecko provides BTC/ETH macro context for the briefing (dominance, market cap)
    # BTC/ETH portfolio positions are ETF shares priced via yfinance like all other tickers
    print("[1/4] Fetching crypto market data...")
    crypto = get_crypto_data()

    print("[2/4] Calculating P&L...")
    pnl   = get_portfolio_pnl(price_data)
    macro = get_macro_data(price_data)

    print("[2/4] Fetching news...")
    news = get_finnhub_news(news_tickers)

    print("[2/4] Fetching analyst signals...")
    analyst = get_analyst_signals(analyst_tickers)

    # ---------------------------------------------------------------
    # STEP 2: Build prompt and call Claude
    # ---------------------------------------------------------------
    print("[3/4] Building prompt and calling Claude...")
    prompt   = build_prompt(pnl, macro, news, analyst, crypto, mode=mode)
    briefing = synthesize_with_claude(prompt, debug=debug)

    if briefing.startswith("[Error]"):
        print(f"\n{briefing}")
        sys.exit(1)

    # ---------------------------------------------------------------
    # STEP 3: Output
    # ---------------------------------------------------------------
    print("[4/4] Delivering briefing...\n")
    print_briefing(briefing, mode=mode)

    if not no_save:
        saved_path = save_briefing(briefing, mode=mode)
        if saved_path:
            print(f"[Saved] {saved_path}")


def show_history():
    """Print a numbered list of all saved briefings."""
    entries = list_saved_briefings()
    if not entries:
        print("No saved briefings found.")
        print("Briefings are saved to: ~/portfolio_briefings/")
        return

    print(f"\nSaved briefings ({len(entries)} total):\n")
    for i, entry in enumerate(entries, 1):
        print(f"  {i:>3}.  {entry['modified']}  {entry['filename']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Portfolio Intelligence Briefing System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                  Run intraday briefing for full portfolio
  python main.py --eod            End-of-day recap mode
  python main.py --ticker PLTR    Single-stock deep dive
  python main.py --history        List all saved briefings
  python main.py --no-save        Run without saving to file
  python main.py --debug          Print the prompt before calling Claude
        """,
    )
    parser.add_argument("--eod",      action="store_true", help="End-of-day recap mode")
    parser.add_argument("--no-save",  action="store_true", help="Skip saving briefing to file")
    parser.add_argument("--debug",    action="store_true", help="Print prompt before Claude call")
    parser.add_argument("--history",  action="store_true", help="List saved briefings and exit")
    parser.add_argument("--ticker",   type=str,            help="Single-ticker deep-dive mode")

    args = parser.parse_args()

    if args.history:
        show_history()
        return

    mode = "eod" if args.eod else "intraday"
    run_briefing(
        mode=mode,
        ticker=args.ticker,
        no_save=args.no_save,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
