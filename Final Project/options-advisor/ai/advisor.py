"""
Claude tool-use loop for the options advisor.

get_advice() takes a user message and returns Claude's recommendation
plus any strategy legs Claude constructed so the frontend can render the P/L chart.
"""
from __future__ import annotations

import anthropic

from ai.tools import TOOLS, execute_tool

MODEL = "claude-sonnet-4-6"

_SYSTEM = """\
You are an expert options strategy advisor embedded in a live options pricing tool.

When the user describes a market view or goal (e.g. "I'm bullish on TSLA for the next month", \
"I want to hedge my NVDA position", "I want to profit if AAPL stays range-bound"), you:

1. Fetch the current price for the ticker they mention.
2. Get available expiration dates and choose one suited to their timeframe \
   (default to ~30–60 days out if they don't specify).
3. Get the live options chain for that expiration.
4. Design a strategy that matches their directional view and risk tolerance:
   - Bullish: long call, bull call spread, cash-secured put
   - Bearish: long put, bear put spread, covered call
   - Neutral/range-bound: short strangle, iron condor, butterfly
5. Call calculate_payoff with the chosen legs so the user can see breakevens and max profit/loss.
6. Explain your choices: which contracts, why those strikes, what the net cost or credit is, \
   and what conditions cause profit vs. loss.

Rules:
- Always use real market data — never invent prices or strikes.
- For beginners, default to defined-risk strategies (spreads, long options) over naked shorts.
- Quantities are number of contracts: positive = long, negative = short.
- Keep the explanation concise and focused on the risk/reward tradeoff."""


def validate_api_key(key: str) -> bool:
    if not key:
        return False
    try:
        client = anthropic.Anthropic(api_key=key)
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True
    except anthropic.AuthenticationError:
        return False
    except Exception:
        return False


def get_advice(user_message: str) -> dict:
    """
    Run a full Claude tool-use loop for one user query.

    Returns:
        {
            "text":     str,          # Claude's final explanation
            "strategy": list | None,  # leg dicts if calculate_payoff was called
            "spot":     float | None, # spot price used in calculate_payoff
        }
    """
    from flask import session
    api_key = session.get("api_key", "")
    if not api_key:
        return {
            "text": "No API key found in session. Please sign in again.",
            "strategy": None,
            "spot": None,
            "ticker": None,
        }

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": user_message}]

    final_text = ""
    strategy_legs: list | None = None
    spot: float | None = None
    ticker_used: str | None = None

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=TOOLS,
            messages=messages,
        )

        for block in response.content:
            if hasattr(block, "text"):
                final_text += block.text

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "get_current_price":
                    ticker_used = block.input.get("ticker", "").upper().strip()
                if block.name == "calculate_payoff":
                    strategy_legs = block.input.get("legs")
                    spot = block.input.get("spot")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": execute_tool(block.name, block.input),
                    }
                )

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return {"text": final_text, "strategy": strategy_legs, "spot": spot, "ticker": ticker_used}
