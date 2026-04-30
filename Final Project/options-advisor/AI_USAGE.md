# AI Usage Log

This file documents every meaningful interaction with AI tools during the development of this project, per course requirements.

---

## Entry 1 — 

**What I asked:**
Design and build a Flask-based options strategy visualizer with the following stack: yfinance for market data, Black-Scholes from scratch (no QuantLib), Newton-Raphson IV solver, multi-leg strategy P/L payoff, Plotly chart rendered client-side, Bootstrap 5 UI. Build phase by phase.

**What was generated:**
- `pricing/black_scholes.py` — BS call/put price, delta, gamma, theta, vega
- `pricing/implied_vol.py` — Newton-Raphson solver with bisection fallback, edge-case handling (T≤0, below-intrinsic, noise floor)
- `pricing/strategies.py` — `Leg` and `Strategy` dataclasses; `aggregate_greeks`, `max_profit/loss`, `breakevens`
- `pricing/payoff.py` — piecewise-linear payoff curve, exact breakevens via linear interpolation
- `data/provider.py` — abstract `DataProvider` ABC with `Quote` and `OptionContract` dataclasses
- `data/yfinance_provider.py` — concrete yfinance implementation
- `app.py` — Flask routes, Flask-Caching with per-argument memoization
- `templates/` — base, index, builder (Bootstrap 5, two-column layout)
- `static/js/charts.js` — chain table rendering, leg panel, Plotly P/L diagram
- `tests/` — 90+ unit tests across all pricing modules

**What I did with it:**
Reviewed each file as it was generated. Caught and corrected a vega test case where the expected value in the test was wrong (mental arithmetic error). Confirmed the piecewise-linear breakeven logic against hand-computed examples. Approved the multi-leg approach in Phase 4 after understanding the architecture.

**What I learned:**
- Black-Scholes Greeks require careful unit choices: theta per calendar day (÷365), vega per 1% vol (÷100)
- Newton-Raphson on IV stalls when vega → 0 (deep OTM near expiry); bisection is the correct fallback
- Flask-Caching `memoize()` on view functions does NOT key by request args — must extract to helper functions with explicit parameters
- Piecewise-linear payoff → exact breakevens by linear interpolation between sign-change neighbors

---

## Entry 2 — Bug fix: Flask-Caching memoize on view functions

**What I asked:**
TSLA options chain showed SPY's price and strikes. Diagnose and fix.

**What was generated:**
Diagnosis confirming `@cache.memoize()` on `api_chain()` generated a single cache key for all tickers. Fix: extract `_fetch_chain(ticker, expiration)` and `_fetch_quote(ticker)` as plain functions decorated with `@cache.memoize()` so the cache key includes both arguments.

**What I did with it:**
Applied the fix. Verified by restarting the server and confirming TSLA loaded its own chain correctly.

**What I learned:**
Flask-Caching `memoize()` keys by function arguments only when those arguments are explicit parameters. Applied to a view function (which takes no parameters), it becomes a simple TTL cache with one slot.

---

## Entry 3 — Data provider swap: yfinance → Tradier sandbox (Iteration 2)

**What I asked:**
Switch from yfinance to Tradier sandbox as a second iteration of the data layer. The yfinance provider returned unreliable call-side data (bid=0 stubs across OTM strikes → garbage implied vols even after adding a noise floor). Keep yfinance intact; don't delete any code. Make it reversible via a `DATA_PROVIDER` env var.

**What was generated:**
- `data/tradier_provider.py` — full `TradierProvider` implementation: `get_quote`, `get_expirations`, `get_chain` with `greeks=true`, ORATS IV/Greeks mapped to `provided_iv`/`provided_greeks` on `OptionContract`
- `data/provider.py` — two optional fields added to `OptionContract`: `provided_iv`, `provided_greeks`
- `config.py` — `DATA_PROVIDER` env var, Tradier token/URL config, startup validation with clear error if token missing
- `app.py` — conditional provider instantiation; `_fetch_chain` updated to use pre-computed Greeks when present, NR solver as fallback
- `.env.example` — Tradier token, base URL, `DATA_PROVIDER` documented
- `requirements.txt` — `requests>=2.31.0` added
- `README.md` — setup instructions, provider comparison table, Tradier token acquisition steps
- `AI_USAGE.md` — this file

**What I did with it:**
Reviewed the diff. Ran a smoke test confirming TSLA July 2026 380 call returned a mid of ~$31 (vs. $0.45 when the caching bug was returning the 0DTE chain). Verified put-call parity held across the chain. Tested `DATA_PROVIDER=yfinance` fallback. Merged the branch after confirming both providers work.

**What I learned:**
- Provider abstractions pay off immediately: swapping the data source touched almost no other code — only `app.py` provider instantiation and one conditional in `_fetch_chain`
- Keeping the NR IV solver as a fallback preserves the technical work while making it optional for providers that supply Greeks directly
- A single `DATA_PROVIDER` env var makes the swap fully reversible without any code changes — critical for Demo Day resilience
