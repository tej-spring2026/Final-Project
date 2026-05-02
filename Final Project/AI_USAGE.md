# AI Usage Log

This file documents every meaningful interaction with AI tools during the development of this project

---

## Entry 1 — 

**What I asked:**
Design and build a Flask-based options strategy visualizer with the following stack: yfinance for market data, Black-Scholes from scratch, Newton-Raphson IV solver, multi-leg strategy P/L payoff, Plotly chart rendered client-side.

**What was generated:**
- `pricing/black_scholes.py` — BS call/put price, delta, gamma, theta, vega
- `pricing/implied_vol.py` — Newton-Raphson solver with bisection fallback, edge-case handling (T≤0, below-intrinsic, noise floor)
- `pricing/strategies.py` — `Leg` and `Strategy` dataclasses; `aggregate_greeks`, `max_profit/loss`, `breakevens`
- `pricing/payoff.py` — piecewise-linear payoff curve, exact breakevens via linear interpolation
- `data/provider.py` — abstract `DataProvider` ABC with `Quote` and `OptionContract` dataclasses
- `data/yfinance_provider.py` — concrete yfinance implementation
- `app.py` — Flask routes, Flask-Caching with per-argument memoization
- `templates/` — base, index, builder
- `static/js/charts.js` — chain table rendering, leg panel, Plotly P/L diagram

**What I did with it:**
Reviewed each file as it was generated. Verified tests and corrected the initially incorrect vega test case where the expected value was wrong. Confirmed the logic on simple maths like breakeven and max/min profit. 

**What I learned:**
- Black-Scholes Greeks require careful unit choices: theta per calendar day (÷365), vega per 1% vol (÷100)
- Newton-Raphson on IV stalls when vega → 0 (deep OTM near expiry); bisection is the correct fallback
- Flask-Caching `memoize()` on view functions does NOT key by request args — must extract to helper functions with explicit parameters

---

## Entry 2 — 

**What I asked:**
The TSLA options chain is showing the SPY's price and strikes. This wrong please fix it.

**What was generated:**
Diagnosis confirming `@cache.memoize()` on `api_chain()` generated a single cache key for all tickers. Fix: extract `_fetch_chain(ticker, expiration)` and `_fetch_quote(ticker)` as plain functions decorated with `@cache.memoize()` so the cache key includes both arguments.

**What I did with it:**
Applied the fix. Verified by restarting the server and confirming TSLA loaded its own chain correctly.

**What I learned:**
How do quickly de-bug coding errors efficiently with AI


---

## Entry  3 — 

**What I asked:**
TSLA calls were displaying what appeared to be 0DTE pricing ($0.30 mid at strike 380) while puts at the same strike showed correct July 2026 data (~$27). Suspected the cache fix from Entry 2 had not taken effect or a new bug had been introduced. Requested a systematic diagnosis with `[DIAG-*]` print statements at every layer before writing any fix.

**What was generated:**
- `[DIAG-ROUTE]` logging added to `api_chain()` to confirm Flask received the correct ticker and expiration
- `[DIAG-CACHE]` logging added to `_fetch_chain()` to confirm cache misses were keyed by (ticker, expiration)
- `[DIAG-PROVIDER]` logging added to `YFinanceProvider.get_chain()` to confirm what expiration yfinance received and what bid/ask it returned
- `[DIAG-FRONTEND]` console.log added to `loadChain()` in charts.js to confirm the browser sent the right URL

**What I did with it:**
Ran the instrumented server, loaded TSLA, selected 2026-07-17. Flask logs showed two separate cache misses keyed correctly: `2026-05-01` (default selection) returned 380 call mid=$4.47; `2026-07-17` returned 380 call mid=$31.93. The UI confirmed $31.93 displayed correctly. Bug was not reproducible once a proper `.env` file with `DATA_PROVIDER=yfinance` was created — the app had previously been failing to start cleanly without it. Removed all `[DIAG-*]` instrumentation after confirming clean data.

**What I learned:**
- Systematic layered logging (frontend URL → route → cache → provider → yfinance) is the correct way to isolate where data corruption occurs — it immediately ruled out the backend and pointed to a configuration/startup issue
- My missing `.env` file caused `config.py` to default to `DATA_PROVIDER=tradier` instead of `DATA_PROVIDER=yfiance`, this ran errors as it wasn't referring to yfinance data
- Learned how to cross reference between Claude Code agent and Claude within Browser to generate better prompts and fix errors

## Entry  4 — 

**What I asked:**
I asked it to add the AI Advisor section and make the UI interface design better to match brokerage platform layouts like Fidelity's and Robinhood's.

**What was generated:**
- Generated differently designed JSON and HTML files to make the UI better
- It added the AI advisor section and added API key in env. to make this possible. It also added a specialized prompt for Claude within my application page to better analyze options pricing and strategy

**What I did with it:**
- Re-check the application to make sure the AI advisor was working an functional
- Made sure I liked the new UI design, which I did


**What I learned:**
- How html design generation works and how prompty claude in browser to create design prompt to copy/paste into claude code vs agent is the best way to go.
- Also learned how to specialize AI features for certain use-cases, like options analysis

## Entry  5 — 

**What I asked:**
Asked AI to generate an authentification login for my application so that only user with Anthropic API keys could use the application to ensure that my usage tokens weren't getting rinsed.

**What was generated:**
- It added authentification to app.py and tested that it was working

**What I did with it:**
- Re-check the application to make sure authentification was present
- Deployed the application onto render.com since it was finally ready to by published on public repo


**What I learned:**
- I learned how to add authentification to a public website by creating a initial 'login' screen before it takes you to the application.
- Also I learned that I didn't need to add my independent API key into render.com as enviornment variable anymore