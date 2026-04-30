"""
Implied volatility solver: Newton-Raphson with bisection fallback.

yfinance's options chain includes bid/ask but no Greeks and unreliable IV.
This module backs out the implied volatility (sigma) from a market mid-price
by finding the sigma that makes Black-Scholes equal to the observed price.

Newton-Raphson update rule (one step):
    sigma_{n+1} = sigma_n  −  (BS(sigma_n) − market_price) / dBS/dsigma

dBS/dsigma is exactly the "raw vega" = S · n(d1) · √T.
Our black_scholes.vega() returns raw_vega / 100 (per 1% vol), so we multiply
back by 100 inside this module.

Falls back to bisection if vega becomes too small for Newton-Raphson to be
stable (e.g. deep OTM options near expiry where the payoff is binary).
"""

from pricing.black_scholes import call_price, put_price, vega as bs_vega

_SIGMA_LOW = 1e-6   # floor: ~zero vol
_SIGMA_HIGH = 10.0  # ceiling: 1000% — never observed in practice


def _bs_price(sigma: float, S: float, K: float, T: float, r: float, option_type: str) -> float:
    if option_type == "call":
        return call_price(S, K, T, r, sigma)
    return put_price(S, K, T, r, sigma)


def _intrinsic(S: float, K: float, option_type: str) -> float:
    if option_type == "call":
        return max(S - K, 0.0)
    return max(K - S, 0.0)


def implied_vol(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
    tol: float = 1e-6,
    max_iter: int = 100,
) -> float | None:
    """
    Compute implied volatility for a single option contract.

    Args:
        market_price: observed mid-price, i.e. (bid + ask) / 2
        S:            current underlying price
        K:            strike price
        T:            time to expiration in years
        r:            annualized risk-free rate (continuously compounded)
        option_type:  "call" or "put"
        tol:          convergence threshold on |BS_price − market_price|
        max_iter:     Newton-Raphson iteration limit before bisection

    Returns:
        Implied volatility as a decimal (0.25 = 25%), or None when:
          - T ≤ 0 (expired — IV undefined)
          - market_price ≤ 0
          - market_price < intrinsic value (arbitrage violation)
          - solver cannot converge within [_SIGMA_LOW, _SIGMA_HIGH]
    """
    option_type = option_type.lower()
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got {option_type!r}")

    if T <= 0:
        return None  # no time value; IV is undefined at expiration

    if market_price <= 0:
        return None

    if market_price < 0.05:
        # Price is at or near the minimum tick ($0.01–$0.04).
        # These are effectively zero-value quotes; IV would be unreliable.
        return None

    intrinsic = _intrinsic(S, K, option_type)
    if market_price < intrinsic - tol:
        # Price below intrinsic is an arbitrage violation.
        # Could be a stale quote; we refuse to return a nonsense IV.
        return None

    # --- Newton-Raphson ---
    # Start at 30% vol, a reasonable prior for most equity options.
    sigma = 0.30

    for _ in range(max_iter):
        price = _bs_price(sigma, S, K, T, r, option_type)
        diff = price - market_price

        if abs(diff) < tol:
            return sigma

        # raw_vega = dBS/dsigma = bs_vega() * 100 (undo the per-1% scaling)
        raw_vega = bs_vega(S, K, T, r, sigma) * 100

        if raw_vega < 1e-10:
            # Vega is negligible — Newton-Raphson would divide near-zero and
            # overshoot wildly. Hand off to bisection.
            break

        sigma -= diff / raw_vega
        sigma = max(_SIGMA_LOW, min(sigma, _SIGMA_HIGH))

    # --- Bisection fallback ---
    return _bisection(market_price, S, K, T, r, option_type, tol)


def _bisection(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str,
    tol: float,
    max_iter: int = 300,
) -> float | None:
    """
    Bisection method: guaranteed convergence if a root exists in [_SIGMA_LOW, _SIGMA_HIGH].
    Slower than Newton-Raphson (~300 iterations vs ~5), but always stable.
    """
    lo, hi = _SIGMA_LOW, _SIGMA_HIGH
    price_lo = _bs_price(lo, S, K, T, r, option_type)
    price_hi = _bs_price(hi, S, K, T, r, option_type)

    # If market_price is outside [BS(lo), BS(hi)], no solution exists.
    if price_lo > market_price or price_hi < market_price:
        return None

    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        price_mid = _bs_price(mid, S, K, T, r, option_type)

        if abs(price_mid - market_price) < tol:
            return mid

        if price_mid < market_price:
            lo = mid
        else:
            hi = mid

    # Return midpoint as best estimate after exhausting iterations.
    return (lo + hi) / 2.0
