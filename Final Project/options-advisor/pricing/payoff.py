"""
Payoff array builder for Plotly P/L diagrams.

Produces a dict that Flask templates can pass directly to the Plotly JSON
renderer — all lists, all JSON-serialisable, no numpy arrays.
"""

import numpy as np

from pricing.strategies import Strategy


def build_payoff(strategy: Strategy, num_points: int = 300) -> dict:
    """
    Generate the expiration P/L curve and summary metrics for a strategy.

    Price range is auto-scaled to show the full profile:
      lower = min_strike × 0.70
      upper = max_strike × 1.30

    This captures the flat OTM region on both sides, making the "hockey
    stick" shape of single-leg diagrams and the tent/valley of spreads
    visually clear.

    Args:
        strategy:   a Strategy with at least one Leg
        num_points: number of points in the price/pnl arrays (higher = smoother)

    Returns a dict with:
        price_range      – list[float], underlying prices on the x-axis
        pnl              – list[float], P/L in dollars at each price
        breakevens       – list[float], prices where pnl = 0
        max_profit       – float, maximum gain in dollars (+inf if uncapped)
        max_loss         – float, maximum loss in dollars (-inf if uncapped)
        net_debit_credit – float, positive = debit paid, negative = credit received
    """
    if not strategy.legs:
        raise ValueError("Cannot build payoff for an empty strategy")

    strikes = [leg.strike for leg in strategy.legs]
    S_min = max(0.0, min(strikes) * 0.70)
    S_max = max(strikes) * 1.30

    prices = np.linspace(S_min, S_max, num_points).tolist()
    pnl = [strategy._payoff_at(S) for S in prices]

    return {
        "price_range": prices,
        "pnl": pnl,
        "breakevens": strategy.breakevens(),
        "max_profit": strategy.max_profit(),
        "max_loss": strategy.max_loss(),
        "net_debit_credit": strategy.net_debit_credit(),
    }
