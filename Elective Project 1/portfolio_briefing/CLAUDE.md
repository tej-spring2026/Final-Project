# Portfolio Intelligence Briefing System
**Owner:** Tej | Boston, MA
**Built:** March 2026 | OIM 3640 Elective Project 1

---

## What This App Does
Pulls live market data for a personal equity + crypto portfolio, feeds everything to Claude (Sonnet 4.6), and produces a concise six-section intelligence briefing. Runs on-demand or auto-scheduled at end-of-day. Every briefing is saved to `~/portfolio_briefings/`.

---

## Architecture: Three Layers

```
data_fetcher.py  →  synthesizer.py  →  output_handler.py
   (fetch)             (Claude)            (print + save)
        ↑                                       ↑
     main.py ——————— orchestrates all three ————┘
```

**data_fetcher.py** — All external API calls. No logic beyond shaping data.
**synthesizer.py** — Builds the structured prompt, calls Claude API. No fetching.
**output_handler.py** — Prints to terminal, saves to file. Stubs for email/Slack/iMessage (Phase 2).
**main.py** — CLI entry point. Parses flags, runs the pipeline.
**config.py** — Single source of truth: portfolio holdings, constants, model settings.

---

## Environment Variables

| Variable | Where to Get It |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `FINNHUB_API_KEY` | finnhub.io/register (free, 30 sec) |

Keys live in `.env` (git-ignored). Never commit `.env`.

---

## Data Sources

| Source | What It Provides | Auth |
|---|---|---|
| yfinance | Prices, P&L, analyst targets | None |
| Finnhub | News, earnings calendar | `FINNHUB_API_KEY` |
| CoinGecko | BTC/ETH price + dominance | None |
| Anthropic | Briefing synthesis | `ANTHROPIC_API_KEY` |

---

## Key Config Values (config.py)
- `CLAUDE_MODEL` = `claude-sonnet-4-6`
- `CLAUDE_MAX_TOKENS` = `1500`
- `FINNHUB_NEWS_DAYS` = `7`
- `FINNHUB_NEWS_PER_TICKER` = `4`
- `OUTPUT_DIR` = `~/portfolio_briefings/`
- `CRYPTO_PROXIES` = `["GBTC", "ETHE", "MSTR"]` — yfinance tickers enriched with CoinGecko context
- `CRYPTO_HOLDINGS` = `{"BTC": ..., "ETH": ...}` — direct crypto, priced via CoinGecko

---

## Known Quirks

**yfinance multi-ticker grouping:** `yf.download()` with multiple tickers returns a MultiIndex DataFrame; single-ticker returns a flat DataFrame. `get_price_data()` handles both cases.

**Finnhub rate limit:** Free tier is 60 req/min. `get_finnhub_news()` sleeps 0.5s between requests. Don't remove the sleep.

**CoinGecko rate limit:** Free tier is 30 req/min. Two calls are made (prices + global). The 0.5s sleep between them is required.

**Direct crypto P&L:** BTC and ETH are held directly. Their CoinGecko prices are injected into `price_data` in `main.py` before calling `get_portfolio_pnl()`, using the 24hr change to back-calculate prev_close.

**Windows strftime:** `%-d` and `%-I` (no-padding format) may not work on Windows. Use `%d` and `%I` and `.lstrip("0")` if you see formatting issues on the terminal header.

**Small-cap tickers:** CRWV, CRCL, BMNR may have limited yfinance/Finnhub coverage. Failures are logged but don't crash the run.

---

## CLI Usage

```bash
python main.py                  # intraday briefing (default)
python main.py --eod            # end-of-day recap
python main.py --ticker PLTR    # single-stock deep dive
python main.py --history        # list saved briefings
python main.py --no-save        # run without saving
python main.py --debug          # print prompt before Claude call
```

---

## Phase 2 Roadmap (not yet built)
- `output_handler.email_briefing()` — Gmail SMTP or SendGrid
- `output_handler.slack_briefing()` — Slack/Discord webhook
- `output_handler.imessage_briefing()` — AppleScript integration
- SEC EDGAR 8-K monitoring
- Earnings calendar auto-flag
- Streamlit dashboard for briefing history

---

## Current Status
**Phase 1–4 complete.** App is fully functional end-to-end.
All five modules built and wired. Tests in `tests/test_data_fetcher.py`.
