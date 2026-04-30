"""
Options strategy modelling: Leg dataclass + Strategy class.

Monetary convention used throughout:
  All dollar amounts are *per contract* (1 contract = 100 shares).
  "Debit" = you paid money out (positive). "Credit" = you received money (negative).

Multi-expiration caveat:
  _payoff_at() assumes every leg is evaluated at expiration intrinsic value.
  For same-expiry strategies this is exact. For calendars / diagonals, the
  far-dated leg will still have time value at near-expiry — the diagram will
  understate that leg's value. This is a known limitation of standard
  expiration P/L diagrams; Phase-6 stretch goals address it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from pricing.black_scholes import greeks as bs_greeks
from pricing.implied_vol import implied_vol


@dataclass
class Leg:
    """A single option position within a strategy."""

    option_type: str    # "call" or "put"
    strike: float       # K — strike price
    expiration: str     # ISO date "YYYY-MM-DD"
    quantity: int       # signed: +N = long N contracts, -N = short N contracts
    entry_price: float  # market mid-price per share when the leg was entered


class Strategy:
    """
    A collection of option Legs with analytics computed at the strategy level.

    Example — bull call spread::

        s = Strategy([
            Leg("call", 95,  "2024-07-01", +1, 8.0),
            Leg("call", 105, "2024-07-01", -1, 3.0),
        ])
        s.max_profit()   # → 500.0  ($5 spread width × 100, less net debit)
        s.breakevens()   # → [100.0]
    """

    def __init__(self, legs: list[Leg] | None = None) -> None:
        self.legs: list[Leg] = list(legs) if legs else []

    def add_leg(self, leg: Leg) -> None:
        self.legs.append(leg)

    # ------------------------------------------------------------------
    # Core payoff math
    # ------------------------------------------------------------------

    def _payoff_at(self, S: float) -> float:
        """
        Total P/L at expiration for underlying price *S*, in dollars per contract.

        Each leg contributes: quantity × (intrinsic − entry_price) × 100
        Positive quantity = long; negative = short.
        """
        total = 0.0
        for leg in self.legs:
            if leg.option_type == "call":
                intrinsic = max(S - leg.strike, 0.0)
            else:
                intrinsic = max(leg.strike - S, 0.0)
            total += leg.quantity * (intrinsic - leg.entry_price)
        return total * 100

    def _key_prices(self) -> list[float]:
        """
        Price points where the payoff function changes slope (i.e. each strike),
        plus boundary anchors at 0 and 3× the highest strike.

        The payoff is perfectly linear between consecutive key prices, so
        evaluating only at these points captures the exact max/min/breakevens.
        """
        strikes = sorted({leg.strike for leg in self.legs})
        upper = max(strikes) * 3
        return [0.0] + strikes + [upper]

    # ------------------------------------------------------------------
    # Summary metrics
    # ------------------------------------------------------------------

    def net_debit_credit(self) -> float:
        """
        Net cost of the position in dollars per contract.
        Positive = net debit (paid). Negative = net credit (received).
        """
        return sum(leg.quantity * leg.entry_price for leg in self.legs) * 100

    def max_profit(self) -> float:
        """
        Maximum possible profit in dollars per contract.
        Returns +inf for strategies with uncapped upside (net long calls).
        """
        if not self.legs:
            return 0.0
        # Any net long call exposure → profit unbounded as S → ∞
        if sum(l.quantity for l in self.legs if l.option_type == "call") > 0:
            return float("inf")
        payoffs = [self._payoff_at(S) for S in self._key_prices()]
        return max(payoffs)

    def max_loss(self) -> float:
        """
        Maximum possible loss in dollars per contract (a negative number).
        Returns -inf for naked short calls (unlimited downside).
        """
        if not self.legs:
            return 0.0
        # Any net short call exposure → loss unbounded as S → ∞
        if sum(l.quantity for l in self.legs if l.option_type == "call") < 0:
            return float("-inf")
        payoffs = [self._payoff_at(S) for S in self._key_prices()]
        return min(payoffs)

    def breakevens(self) -> list[float]:
        """
        Underlying prices at expiration where total P/L = 0.

        The payoff is piecewise linear, so breakevens are found by exact
        linear interpolation between consecutive key price points.
        Returns a sorted list; most strategies have 1 or 2 breakevens.
        """
        prices = self._key_prices()
        payoffs = [self._payoff_at(p) for p in prices]
        result: list[float] = []

        for i in range(len(prices) - 1):
            p1, p2 = prices[i], prices[i + 1]
            y1, y2 = payoffs[i], payoffs[i + 1]

            if abs(y1) < 0.01:
                result.append(round(p1, 4))
            elif (y1 > 0) != (y2 > 0):
                # Sign change — linear interpolation gives exact crossing
                frac = -y1 / (y2 - y1)
                result.append(round(p1 + frac * (p2 - p1), 4))

        # Handle the last boundary separately
        if abs(payoffs[-1]) < 0.01:
            result.append(round(prices[-1], 4))

        # Deduplicate (two nearby strikes can produce duplicate roots)
        seen: list[float] = []
        for be in sorted(result):
            if not any(abs(be - s) < 0.01 for s in seen):
                seen.append(be)
        return seen

    def aggregate_greeks(
        self, S: float, r: float, as_of: date | None = None
    ) -> dict:
        """
        Weighted sum of Greeks across all legs.

        T per leg is computed from *as_of* (defaults to today).
        IV is backed out from each leg's entry_price via Newton-Raphson,
        which is accurate when entry prices reflect current market levels.

        Args:
            S:     current underlying price
            r:     annualised risk-free rate
            as_of: date to compute T from (use a fixed date in tests)

        Returns:
            dict with keys: delta, gamma, theta, vega
            Legs whose IV cannot be solved (e.g. deep OTM near-zero price)
            are silently skipped — the returned Greeks reflect only the
            priceable legs.
        """
        today = as_of or date.today()
        total = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

        for leg in self.legs:
            exp_date = date.fromisoformat(leg.expiration)
            T = (exp_date - today).days / 365.0
            if T <= 0:
                continue  # expired leg contributes no Greeks

            iv = implied_vol(leg.entry_price, S, leg.strike, T, r, leg.option_type)
            if iv is None:
                continue

            g = bs_greeks(S, leg.strike, T, r, iv, leg.option_type)
            for key in total:
                total[key] += leg.quantity * g[key]

        return total
