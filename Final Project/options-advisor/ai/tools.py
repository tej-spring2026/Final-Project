"""
Tool schemas (for the Claude API) and their Python implementations.

Each tool schema is a dict Claude receives so it knows what to call.
execute_tool() dispatches by name and returns a JSON string result.
"""
from __future__ import annotations

import json

import config
from pricing.payoff import build_payoff
from pricing.strategies import Leg, Strategy

# ── Provider singleton — mirrors the selection logic in app.py ───────────────
if config.DATA_PROVIDER == "tradier":
    from data.tradier_provider import TradierProvider
    _provider = TradierProvider(
        config.TRADIER_SANDBOX_TOKEN,
        config.TRADIER_SANDBOX_BASE_URL,
    )
else:
    from data.yfinance_provider import YFinanceProvider
    _provider = YFinanceProvider()


# ── Tool schemas (sent to Claude in every messages.create call) ──────────────

TOOLS = [
    {
        "name": "get_current_price",
        "description": (
            "Get the current market price of a stock. "
            "Call this first to anchor the strategy to the live spot price."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol, e.g. TSLA",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_expirations",
        "description": "Get available options expiration dates for a ticker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_options_chain",
        "description": (
            "Get the live options chain for a ticker and expiration date. "
            "Returns available strikes with mid prices, IVs, and deltas. "
            "Use this to select specific strikes when building a strategy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "expiration": {
                    "type": "string",
                    "description": "Expiration date in YYYY-MM-DD format",
                },
            },
            "required": ["ticker", "expiration"],
        },
    },
    {
        "name": "calculate_payoff",
        "description": (
            "Calculate the P/L payoff profile for a multi-leg options strategy at expiration. "
            "Returns breakevens, max profit, max loss, net debit/credit, and aggregate Greeks. "
            "Always call this after selecting strikes so the user can see the full risk profile."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "spot": {
                    "type": "number",
                    "description": "Current spot price of the underlying",
                },
                "legs": {
                    "type": "array",
                    "description": "Option legs in the strategy",
                    "items": {
                        "type": "object",
                        "properties": {
                            "option_type": {
                                "type": "string",
                                "enum": ["call", "put"],
                            },
                            "strike": {"type": "number"},
                            "expiration": {
                                "type": "string",
                                "description": "YYYY-MM-DD",
                            },
                            "quantity": {
                                "type": "integer",
                                "description": "Contracts: positive = long, negative = short",
                            },
                            "entry_price": {
                                "type": "number",
                                "description": "Mid price per share (multiply by 100 for contract value)",
                            },
                        },
                        "required": [
                            "option_type",
                            "strike",
                            "expiration",
                            "quantity",
                            "entry_price",
                        ],
                    },
                },
            },
            "required": ["spot", "legs"],
        },
    },
]


# ── Tool implementations ─────────────────────────────────────────────────────

def _get_current_price(ticker: str) -> dict:
    q = _provider.get_quote(ticker.upper().strip())
    return {"ticker": q.ticker, "price": round(q.price, 2)}


def _get_expirations(ticker: str) -> dict:
    exps = _provider.get_expirations(ticker.upper().strip())
    return {"ticker": ticker.upper(), "expirations": exps}


def _get_options_chain(ticker: str, expiration: str) -> dict:
    ticker = ticker.upper().strip()
    quote = _provider.get_quote(ticker)
    contracts = _provider.get_chain(ticker, expiration)

    calls, puts = [], []
    for c in contracts:
        mid = c.mid
        usable = round(mid, 2) if mid >= 0.05 else None
        iv = round(c.provided_iv * 100, 1) if c.provided_iv is not None else None
        delta = None
        if c.provided_greeks:
            delta = round(c.provided_greeks.get("delta", 0), 2)
        entry = {"strike": c.strike, "mid": usable, "iv_pct": iv, "delta": delta}
        if c.option_type == "call":
            calls.append(entry)
        else:
            puts.append(entry)

    return {
        "spot": round(quote.price, 2),
        "expiration": expiration,
        "calls": calls,
        "puts": puts,
    }


def _calculate_payoff(spot: float, legs: list[dict]) -> dict:
    strategy_legs = [
        Leg(
            option_type=str(l["option_type"]).lower(),
            strike=float(l["strike"]),
            expiration=str(l["expiration"]),
            quantity=int(l["quantity"]),
            entry_price=float(l["entry_price"]),
        )
        for l in legs
    ]
    strategy = Strategy(strategy_legs)
    result = build_payoff(strategy)

    def _clean(v):
        if v is None or (isinstance(v, float) and (v != v or abs(v) == float("inf"))):
            return None
        return round(v, 2)

    greeks = strategy.aggregate_greeks(spot, config.RISK_FREE_RATE)

    return {
        "net_debit_credit": round(result["net_debit_credit"], 2),
        "max_profit": _clean(result["max_profit"]),
        "max_loss": _clean(result["max_loss"]),
        "breakevens": [round(b, 2) for b in result["breakevens"]],
        "greeks": {k: round(v, 4) for k, v in greeks.items()},
    }


# ── Dispatcher ───────────────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict) -> str:
    """Execute a tool by name and return its result as a JSON string."""
    try:
        if name == "get_current_price":
            result = _get_current_price(**inputs)
        elif name == "get_expirations":
            result = _get_expirations(**inputs)
        elif name == "get_options_chain":
            result = _get_options_chain(**inputs)
        elif name == "calculate_payoff":
            result = _calculate_payoff(**inputs)
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as exc:
        result = {"error": str(exc)}
    return json.dumps(result)
