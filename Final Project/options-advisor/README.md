# Options Strategy Visualizer + AI Advisor

A Flask web application for building multi-leg options strategies with live options chain data, Black-Scholes Greeks, P/L diagrams, and an AI-powered advisor.

## Features

- Live options chain (15-min delayed) for any US-listed equity
- Multi-leg strategy builder: long/short any combination of calls and puts
- Payoff diagram at expiration (Plotly), rendered client-side
- Exact breakeven calculation via piecewise-linear interpolation
- Aggregate Greeks (Δ, Γ, Θ, ν) for the full position
- AI advisor powered by Claude (Phase 5)

## Architecture

```
options-advisor/
├── app.py                  # Flask routes only — no business logic
├── config.py               # Env var loading + provider selection
├── data/
│   ├── provider.py         # Abstract DataProvider interface
│   ├── yfinance_provider.py  # Legacy: yfinance (no token required)
│   └── tradier_provider.py   # Default: Tradier sandbox + ORATS Greeks
├── pricing/
│   ├── black_scholes.py    # BS call/put price, delta, gamma, theta, vega
│   ├── implied_vol.py      # Newton-Raphson IV solver with bisection fallback
│   ├── strategies.py       # Leg + Strategy dataclasses
│   └── payoff.py           # P/L curve builder
├── static/
│   ├── css/style.css
│   └── js/charts.js        # Chain table, leg panel, Plotly chart
└── templates/
    ├── base.html
    ├── index.html
    └── builder.html
```

### Iterative data provider design

The project deliberately maintains two data providers as a record of architectural iteration:

| Provider | Status | Notes |
|---|---|---|
| `yfinance_provider.py` | Legacy (retained) | Free, no token; call-side bid=0 stubs produced unreliable IV on OTM strikes |
| `tradier_provider.py` | Default (Iteration 2) | Tradier sandbox + ORATS Greeks; exchange-quality quotes, IV and Greeks pre-computed |

The `DataProvider` ABC in `provider.py` made this swap almost entirely additive — no pricing, strategy, payoff, or UI code required changes.

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd "Final Project/options-advisor"
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```
ANTHROPIC_API_KEY=...         # from console.anthropic.com
FLASK_SECRET_KEY=...          # any random string
TRADIER_SANDBOX_TOKEN=...     # see below
DATA_PROVIDER=tradier         # or "yfinance" to use the legacy provider
```

### 3. Get a free Tradier sandbox token

1. Sign up at [developer.tradier.com](https://developer.tradier.com)
2. Navigate to **Sandbox** → **API Access** → copy your Bearer token
3. Paste it as `TRADIER_SANDBOX_TOKEN` in `.env`

To use yfinance instead (no token required), set `DATA_PROVIDER=yfinance`.

### 4. Run

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Running tests

```bash
pytest tests/
```

The test suite covers Black-Scholes pricing, the IV solver, and strategy/payoff calculations. Data integration tests require a live network connection.

## Data freshness

Both providers return data delayed approximately 15 minutes during market hours. The disclaimer in the UI reflects this.
