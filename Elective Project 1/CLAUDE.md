# ELECTIVE PROJECT 1
Portfolio Intelligence Briefing System

AI-Powered Daily Portfolio Analysis & Market Intelligence


Tej  |  Boston, MA
Built with Claude Code  ·  VS Code
March 2026

1. Project Overview
This document is a complete build specification for Claude Code. It defines the Portfolio Intelligence Briefing System — an automated tool that aggregates real-time market data, news, analyst signals, and macro context for a personal stock portfolio, then synthesizes everything into a sharp, actionable briefing using Claude AI.

1.1  What the App Does
•	Pulls live price data, P&L, and performance for each portfolio position
•	Fetches relevant news and catalysts via the Finnhub API
•	Retrieves analyst price targets and recommendation trends
•	Captures macro context: S&P 500, Nasdaq, VIX, 10-year yield
•	Feeds all data to Claude, which synthesizes a concise intelligence briefing
•	Runs on-demand (manual trigger) and auto-schedules an end-of-day recap
•	Saves every briefing to a dated local file for historical reference

1.2  Core Portfolio
The app is pre-configured for the following holdings. Shares and cost basis are editable in the config:

Ticker	Category	Primary Data Source	Key Signal
AMZN / META 	Mega-cap Tech	yfinance + Finnhub	Price, news, sentiment
PLTR	AI / Data Analytics	yfinance + Finnhub	Earnings + catalyst news
NVDA	Semiconductors	yfinance + Finnhub	Chip cycle + analyst targets
AMAT / AMD	Semi Equipment	yfinance + Finnhub	Sector momentum
ARKK / QQQ	ETFs	yfinance	Benchmark vs holdings
BTC / ETH (proxies)	Crypto	CoinGecko API	24hr change + dominance
 
2. System Architecture
The application is structured in three clean layers that Claude Code should build and keep separate:

2.1  Data Layer  (data_fetcher.py)
Responsible for all external API calls. Each source is an isolated function. No synthesis logic lives here.
•	get_price_data(tickers) — yfinance: prices, day change, 2-day history
•	get_portfolio_pnl(price_data) — calculates per-position and total P&L from the PORTFOLIO config
•	get_macro_data(price_data) — extracts SPY, QQQ, VIX, ^TNX snapshots
•	get_finnhub_news(tickers) — Finnhub REST API: top 4 articles per ticker, last 7 days
•	get_analyst_signals(tickers) — yfinance: mean/high/low price targets + recommendation key
•	get_crypto_data() — CoinGecko free API: BTC and ETH 24hr price + change (no key required)

2.2  Synthesis Layer  (synthesizer.py)
Builds the structured prompt and calls the Claude API. This file has no data-fetching logic.
•	build_prompt(pnl, macro, news, analyst, crypto, mode) — assembles all data into a structured prompt
•	synthesize_with_claude(prompt) — POSTs to Anthropic /v1/messages, returns briefing text
The prompt instructs Claude to produce six sections: Portfolio Performance, Key Movers & Why, News That Matters, Analyst Watch, Macro Read, and One Thing to Watch.

2.3  Output Layer  (output_handler.py)
Handles all delivery and persistence. Designed to be extended (email, Slack, web) without touching the other layers.
•	print_briefing(text) — formats and prints to terminal with section headers
•	save_briefing(text, mode) — saves to ~/portfolio_briefings/briefing_<mode>_<timestamp>.txt
•	[ Phase 2 ] email_briefing(text) — Gmail SMTP or SendGrid delivery
•	[ Phase 2 ] slack_briefing(text) — Slack webhook delivery

2.4  Entry Point  (main.py)
•	Parses --eod and --no-save CLI flags
•	Orchestrates the three layers in sequence: fetch → synthesize → output
•	Handles graceful errors: missing API keys, network failures, rate limits
 
3. Data Sources & API Setup

Source	What It Provides	Auth	Cost	Rate Limit
yfinance	Prices, P&L, analyst targets, fundamentals	None needed	Free	~2 req/sec, be gentle
Finnhub	News, sentiment, earnings calendar	Free API key	Free tier	60 req/min
SEC EDGAR	10-K, 10-Q, 8-K filings	None needed	Free	10 req/sec
CoinGecko	BTC/ETH price + 24hr change	None needed	Free tier	30 req/min
Anthropic API	Briefing synthesis (Claude)	Existing key	~$0.01/run	Tier-based

3.1  Environment Variables Required
Add to ~/.zshrc or ~/.bash_profile
export ANTHROPIC_API_KEY="sk-ant-..."    # already configured export FINNHUB_API_KEY="your_key_here"     # get free at finnhub.io

3.2  Getting Your Finnhub Key
•	Visit finnhub.io/register — takes 30 seconds, no credit card
•	Copy the key from the dashboard and add it to your shell profile
•	Free tier: 60 requests/minute, company news, earnings calendar, sentiment
 
4. Step-by-Step Build Plan for Claude Code
Hand this section directly to Claude Code in VS Code. Each phase is a discrete, testable unit of work.

Phase 1 — Project Scaffold
Step	Action	File(s)	Key Detail
1	Create project directory structure	portfolio_briefing/	mkdir -p with all subdirs
2	Create requirements.txt	requirements.txt	yfinance, requests, anthropic, python-dotenv
3	Create .env template	.env.template	ANTHROPIC_API_KEY, FINNHUB_API_KEY placeholders
4	Create config.py with PORTFOLIO dict	config.py	All tickers, shares, avg_cost + BENCHMARKS list
5	Create empty module files	data_fetcher.py, synthesizer.py, output_handler.py, main.py	With docstrings only

Phase 2 — Data Layer
Step	Action	File(s)	Key Detail
6	Implement get_price_data()	data_fetcher.py	yf.download(), 2d period, handle single vs multi-ticker
7	Implement get_portfolio_pnl()	data_fetcher.py	Per-position P&L, sort by abs day dollar impact
8	Implement get_macro_data()	data_fetcher.py	Extract SPY, QQQ, VIX, ^TNX from price_data dict
9	Implement get_finnhub_news()	data_fetcher.py	REST GET, 7-day window, top 4 per ticker, 0.5s sleep
10	Implement get_analyst_signals()	data_fetcher.py	yf.Ticker().info: targetMeanPrice, recommendationKey
11	Implement get_crypto_data()	data_fetcher.py	CoinGecko /simple/price, BTC + ETH, 24h change
12	Write data layer unit tests	tests/test_data_fetcher.py	Mock API responses, test P&L math

Phase 3 — Synthesis Layer
Step	Action	File(s)	Key Detail
13	Implement build_prompt()	synthesizer.py	Format all data sections, intraday vs EOD tone switch
14	Implement synthesize_with_claude()	synthesizer.py	POST to /v1/messages, claude-opus-4-5, 1500 tokens
15	Add error handling	synthesizer.py	Missing key, HTTP errors, timeout (60s), rate limits
16	Test prompt output	synthesizer.py	Print prompt to console before API call in --debug mode

Phase 4 — Output & Entry Point
Step	Action	File(s)	Key Detail
17	Implement print_briefing()	output_handler.py	Clean terminal formatting with section separators
18	Implement save_briefing()	output_handler.py	~/portfolio_briefings/, dated filename, auto-mkdir
19	Build main.py with argparse	main.py	--eod, --no-save, --debug, --ticker flags
20	Wire all three layers in main()	main.py	fetch → synthesize → output, graceful error messages

Phase 5 — Scheduling & Polish
Step	Action	File(s)	Key Detail
21	Add cron scheduling instructions	README.md	4:05 PM ET Mon-Fri crontab entry
22	Add --ticker flag for single-stock mode	main.py	python main.py --ticker PLTR
23	Add briefing history viewer	main.py	python main.py --history (list saved briefings)
24	Write full README	README.md	Setup, usage, env vars, scheduling, phase 2 roadmap
 
5. Target File Structure
Final project layout Claude Code should produce
portfolio_briefing/ ├── main.py                  # entry point, CLI flags ├── config.py                # PORTFOLIO dict, BENCHMARKS, constants ├── data_fetcher.py          # all API calls (yfinance, Finnhub, CoinGecko) ├── synthesizer.py           # prompt builder + Claude API call ├── output_handler.py        # print, save, (later) email/Slack ├── requirements.txt ├── .env.template ├── README.md └── tests/     └── test_data_fetcher.py

5.1  Key Config Values (config.py)
Claude Code should create config.py with these constants:
•	PORTFOLIO — dict of ticker → {shares, avg_cost} for all positions
•	BENCHMARKS — ['SPY', 'QQQ', 'VIX', '^TNX'] for macro context
•	FINNHUB_NEWS_DAYS — 7 (look-back window for news fetch)
•	FINNHUB_NEWS_PER_TICKER — 4 (max articles per stock)
•	CLAUDE_MODEL — 'claude-opus-4-5'
•	CLAUDE_MAX_TOKENS — 1500
•	OUTPUT_DIR — os.path.expanduser('~/portfolio_briefings')
 
6. Briefing Output Structure
The Claude synthesis prompt should instruct Claude to produce exactly six sections in every briefing. This structure applies to both intraday and EOD modes (the tone shifts, not the structure).

1. Portfolio Performance
Total P&L for the day in dollars and percent. Compare to SPY/QQQ to show whether underperformance or outperformance is idiosyncratic or market-driven. Top 3 winners and losers by dollar impact.

2. Key Movers & Why
For each position that moved >1.5% today, explain the most likely catalyst drawn from news and macro data. Be specific — not 'market conditions' but the actual driver.

3. News That Matters
Surface the 3–5 most portfolio-relevant news items from the last 7 days. Skip generic market noise. Prioritize company-specific earnings, product, regulatory, or management news.

4. Analyst Watch
Flag any positions where current price is significantly above or below the analyst consensus target. Note any recent rating changes if present in the data.

5. Macro Read
One paragraph on how the macro environment today (VIX level, yield direction, index performance) is helping or hurting the portfolio's specific sector exposures.

6. One Thing to Watch
The single most important item — catalyst, risk, or opportunity — heading into the next trading session. One sentence. Actionable.

 
7. Phase 2 Roadmap
These features are out of scope for the initial build but Claude Code should architect the app to accommodate them easily (especially the output_handler.py separation).

7.1  Delivery Channels
•	Email delivery — Gmail SMTP or SendGrid: run at EOD, receive briefing in inbox
•	Slack/Discord webhook — post formatted briefing to a private channel
•	iMessage — Applescript or Shortcuts integration on Mac

7.2  Data Enrichment
•	SEC EDGAR 8-K monitoring — detect earnings surprises and material events
•	Options flow — unusual options activity via Unusual Whales free tier or Tradier
•	Reddit/X sentiment — wsb or StockTwits sentiment scores for high-volatility names
•	Earnings calendar — auto-flag positions with upcoming earnings in the briefing

7.3  Interface
•	Streamlit dashboard — web UI showing briefing history, P&L charts, position table
•	CLI history viewer — python main.py --history to browse past briefings
•	Single-ticker deep dive — python main.py --ticker PLTR for focused analysis

7.4  Intelligence Upgrades
•	Trend detection — compare today's briefing to last 5 EOD briefings, flag pattern changes
•	Earnings transcript analysis — pipe PLTR/NVDA transcripts through existing earnings_sentiment_analyzer.py
•	Portfolio rebalancing suggestions — flag when a position drifts >5% from target weight
8. Instructions for Claude Code
Paste the following prompt directly into Claude Code in VS Code to start the build:

Claude Code Kickoff Prompt — copy and paste this
You are building a Portfolio Intelligence Briefing System for me.  I have attached a full project plan (ELECTIVE_PROJECT_1_PLAN.docx) —  read it before writing any code.  Build in this order: 1. Create the full directory structure from Section 5 2. Build config.py with my portfolio tickers (ask me for shares/cost basis if not provided) 3. Build data_fetcher.py — all functions in Phase 2, with error handling 4. Build synthesizer.py — prompt builder and Claude API call 5. Build output_handler.py — print and save functions 6. Build main.py — wire everything together with argparse 7. Write README.md with setup and scheduling instructions  Use python-dotenv for API key management. Keep each module under 200 lines — split into helpers if needed. After each phase, show me a quick test to verify it works before moving on.

8.1  CLAUDE.md Bridge File
Claude Code should also create a CLAUDE.md file in the project root. This gives the agent persistent context across sessions — it won't forget what the project does or how it's structured.
•	Project name, purpose, and owner
•	Architecture overview (data → synthesis → output)
•	All environment variable names and where to get keys
•	Current phase and what's been completed
•	Known quirks: yfinance multi-ticker grouping, Finnhub rate limits


Document version: 1.0  |  March 2026  |  Elective Project 1
