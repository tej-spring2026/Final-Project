"""
synthesizer.py — Portfolio Intelligence Briefing System
Synthesis layer: builds the structured prompt and calls the Claude API.
No data-fetching logic lives here.

Functions:
    build_prompt(pnl, macro, news, analyst, crypto, mode)
        — assembles all data sections into a structured prompt for Claude
    synthesize_with_claude(prompt)
        — POSTs to Anthropic /v1/messages, returns briefing text
"""

import os
import anthropic
from dotenv import load_dotenv

from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS

load_dotenv()


# ============================================================================
# PROMPT BUILDER
# ============================================================================

def build_prompt(pnl, macro, news, analyst, crypto, mode="intraday"):
    """
    Assemble all data sections into a structured prompt for Claude.

    The prompt instructs Claude to produce exactly six briefing sections:
        1. Portfolio Performance
        2. Key Movers & Why
        3. News That Matters
        4. Analyst Watch
        5. Macro Read
        6. One Thing to Watch

    Args:
        pnl:      dict from get_portfolio_pnl()
        macro:    dict from get_macro_data()
        news:     dict from get_finnhub_news()
        analyst:  dict from get_analyst_signals()
        crypto:   dict from get_crypto_data()
        mode:     "intraday" (default) or "eod" — shifts the tone of the briefing

    Returns:
        str: the full prompt string
    """
    tone_instruction = (
        "This is an END-OF-DAY recap. Focus on what happened today, what it means "
        "for tomorrow, and whether the day's moves change the thesis on any position."
        if mode == "eod"
        else
        "This is an INTRADAY briefing. Focus on current momentum, near-term catalysts, "
        "and what to watch before the close."
    )

    lines = []
    lines.append("You are a sharp, concise portfolio intelligence analyst.")
    lines.append(tone_instruction)
    lines.append("")
    lines.append(
        "Using ONLY the data provided below, produce a briefing with exactly these "
        "six sections. Be specific and actionable — never say 'market conditions' "
        "when you can name the actual driver. Keep the total briefing under 600 words."
    )
    lines.append("")
    lines.append("Required sections:")
    lines.append("  1. Portfolio Performance")
    lines.append("  2. Key Movers & Why")
    lines.append("  3. News That Matters")
    lines.append("  4. Analyst Watch")
    lines.append("  5. Macro Read")
    lines.append("  6. One Thing to Watch  (one sentence, actionable)")
    lines.append("")
    lines.append("=" * 60)
    lines.append("PORTFOLIO DATA")
    lines.append("=" * 60)

    # --- Portfolio P&L summary ---
    lines.append(f"Total Market Value:     ${pnl['total_market_value']:>14,.2f}")
    lines.append(f"Total Day Change:       ${pnl['total_day_change_dollar']:>+14,.2f}  "
                 f"({pnl['total_day_change_pct']:>+.2f}%)")
    lines.append(f"Total Unrealized Gain:  ${pnl['total_unrealized_gain']:>+14,.2f}  "
                 f"({pnl['total_unrealized_pct']:>+.2f}%)")
    lines.append("")

    # --- Top movers (by absolute dollar impact) ---
    lines.append("TOP MOVERS (by day dollar impact):")
    for pos in pnl["positions"][:10]:
        sign = "+" if pos["day_change_dollar"] >= 0 else ""
        lines.append(
            f"  {pos['ticker']:<6}  price ${pos['current_price']:>8,.2f}  "
            f"day {sign}${pos['day_change_dollar']:>+10,.2f} ({pos['day_change_pct']:>+.2f}%)  "
            f"value ${pos['market_value']:>12,.2f}"
        )
    lines.append("")

    # --- All positions for full context ---
    lines.append("ALL POSITIONS:")
    for pos in pnl["positions"]:
        sign = "+" if pos["day_change_dollar"] >= 0 else ""
        lines.append(
            f"  {pos['ticker']:<6}  {pos['shares']:>10.3f} sh @ avg ${pos['avg_cost']:>8.2f}  "
            f"cur ${pos['current_price']:>8,.2f}  "
            f"day {sign}${pos['day_change_dollar']:>+10,.2f} ({pos['day_change_pct']:>+.2f}%)  "
            f"unrlzd {'+' if pos['unrealized_gain'] >= 0 else ''}${pos['unrealized_gain']:>12,.2f} "
            f"({pos['unrealized_pct']:>+.2f}%)"
        )

    # --- Macro ---
    lines.append("")
    lines.append("=" * 60)
    lines.append("MACRO CONTEXT")
    lines.append("=" * 60)
    for label, data in macro.items():
        lines.append(
            f"  {label:<6}  {data['current_price']:>8.2f}  "
            f"({data['day_change_pct']:>+.2f}% today)"
        )

    # --- Crypto ---
    if crypto:
        lines.append("")
        lines.append("CRYPTO MARKET:")
        if "BTC" in crypto:
            btc = crypto["BTC"]
            dom = f"  dominance {btc.get('dominance_pct', 'N/A')}%" if "dominance_pct" in btc else ""
            lines.append(
                f"  BTC   ${btc['current_price']:>10,.2f}  "
                f"({btc['day_change_pct']:>+.2f}% 24hr){dom}"
            )
        if "ETH" in crypto:
            eth = crypto["ETH"]
            lines.append(
                f"  ETH   ${eth['current_price']:>10,.2f}  "
                f"({eth['day_change_pct']:>+.2f}% 24hr)"
            )
        if "btc_dominance_pct" in crypto:
            lines.append(f"  BTC dominance: {crypto['btc_dominance_pct']}%")
        if "total_crypto_market_cap" in crypto:
            cap = crypto["total_crypto_market_cap"]
            lines.append(f"  Total crypto market cap: ${cap / 1e12:.2f}T")

    # --- Analyst signals ---
    lines.append("")
    lines.append("=" * 60)
    lines.append("ANALYST SIGNALS")
    lines.append("=" * 60)
    if analyst:
        for ticker, sig in sorted(analyst.items()):
            if sig["target_mean"] is None:
                continue
            upside = f"{sig['upside_pct']:>+.1f}%" if sig["upside_pct"] is not None else "N/A"
            rec    = sig["recommendation"] or "N/A"
            lines.append(
                f"  {ticker:<6}  cur ${sig['current_price'] or 'N/A':>8}  "
                f"tgt mean ${sig['target_mean']:>8.2f} / "
                f"high ${sig['target_high'] or 'N/A':>8} / "
                f"low ${sig['target_low'] or 'N/A':>7}  "
                f"upside {upside:>7}  rec: {rec}"
            )
    else:
        lines.append("  (No analyst data available)")

    # --- News ---
    lines.append("")
    lines.append("=" * 60)
    lines.append("RECENT NEWS (last 7 days)")
    lines.append("=" * 60)
    if news:
        for ticker, articles in news.items():
            if not articles:
                continue
            lines.append(f"\n  [{ticker}]")
            for art in articles:
                lines.append(f"    • {art['datetime']}  {art['source']}")
                lines.append(f"      {art['headline']}")
                if art["summary"]:
                    summary = art["summary"][:200] + "..." if len(art["summary"]) > 200 else art["summary"]
                    lines.append(f"      {summary}")
    else:
        lines.append("  (No news data available)")

    lines.append("")
    lines.append("=" * 60)
    lines.append("Now write the six-section briefing:")
    lines.append("=" * 60)

    return "\n".join(lines)


# ============================================================================
# CLAUDE API CALL
# ============================================================================

def synthesize_with_claude(prompt, debug=False):
    """
    Send the assembled prompt to Claude and return the briefing text.

    Args:
        prompt: str — the full prompt from build_prompt()
        debug:  bool — if True, prints the prompt before sending

    Returns:
        str: the briefing text from Claude, or an error message string.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "[Error] ANTHROPIC_API_KEY not set. Add it to your .env file."

    if debug:
        print("\n" + "=" * 60)
        print("DEBUG — PROMPT SENT TO CLAUDE:")
        print("=" * 60)
        print(prompt)
        print("=" * 60 + "\n")

    try:
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            timeout=60,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        return message.content[0].text

    except anthropic.AuthenticationError:
        return "[Error] Invalid Anthropic API key. Check your .env file."

    except anthropic.RateLimitError:
        return "[Error] Anthropic rate limit hit. Wait a moment and try again."

    except anthropic.APITimeoutError:
        return "[Error] Claude API call timed out after 60 seconds."

    except anthropic.APIError as e:
        return f"[Error] Anthropic API error: {e}"

    except Exception as e:
        return f"[Error] Unexpected error calling Claude: {e}"
