"""
Black-Scholes option pricing and Greeks.

All functions are pure (no I/O, no Flask imports) so they can be tested in isolation.

Parameter conventions used throughout this module:
  S     – current price of the underlying asset
  K     – strike price of the option
  T     – time to expiration expressed in years (e.g. 30 days → T = 30/365)
  r     – annualized risk-free interest rate, continuously compounded (e.g. 0.05 = 5%)
  sigma – annualized implied volatility (e.g. 0.25 = 25%)

Formula source: Black & Scholes (1973), as presented in Hull's
"Options, Futures, and Other Derivatives", 11th ed., Chapter 15.
"""

import numpy as np
from scipy.stats import norm


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    """
    Compute the intermediate d1 and d2 terms shared across all BS formulas.

    d1 = [ln(S/K) + (r + σ²/2) · T] / (σ · √T)
    d2 = d1 − σ · √T
    """
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2


def call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    European call price via Black-Scholes.

    C = S · N(d1) − K · e^(−rT) · N(d2)

    At expiration (T ≤ 0) returns intrinsic value max(S − K, 0).
    """
    if T <= 0:
        return max(S - K, 0.0)
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    European put price via Black-Scholes.

    P = K · e^(−rT) · N(−d2) − S · N(−d1)

    At expiration (T ≤ 0) returns intrinsic value max(K − S, 0).
    """
    if T <= 0:
        return max(K - S, 0.0)
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def call_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Call delta: sensitivity of the call price to a $1 move in the underlying.
    Range: [0, 1]. ATM ≈ 0.5; deep ITM → 1; deep OTM → 0.
    """
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return float(norm.cdf(d1))


def put_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Put delta: sensitivity of the put price to a $1 move in the underlying.
    Range: [−1, 0]. ATM ≈ −0.5; deep ITM → −1; deep OTM → 0.
    """
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return float(norm.cdf(d1) - 1.0)


def gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Gamma: rate of change of delta per $1 move in the underlying.
    Identical for calls and puts (put-call parity). Always positive.

    Γ = n(d1) / (S · σ · √T)
    """
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return float(norm.pdf(d1) / (S * sigma * np.sqrt(T)))


def theta_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Call theta: daily time decay (change in price per one calendar day passing).
    Almost always negative — options lose value as expiration approaches.

    Θ_call = [−S · n(d1) · σ / (2√T)  −  r · K · e^(−rT) · N(d2)] / 365
    """
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    term1 = -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
    term2 = -r * K * np.exp(-r * T) * norm.cdf(d2)
    return float((term1 + term2) / 365)


def theta_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Put theta: daily time decay per calendar day.
    Usually negative, but deep-ITM puts with high interest rates can be positive
    because the time value of receiving K early becomes significant.

    Θ_put = [−S · n(d1) · σ / (2√T)  +  r · K · e^(−rT) · N(−d2)] / 365
    """
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    term1 = -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
    term2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
    return float((term1 + term2) / 365)


def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Vega: change in option price per 1 percentage-point increase in implied volatility.
    Identical for calls and puts. Always positive.

    ν = S · n(d1) · √T / 100
    (divided by 100 so the result is in $/1% vol, matching market convention)
    """
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return float(S * norm.pdf(d1) * np.sqrt(T) / 100)


def greeks(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call"
) -> dict:
    """
    Return all four Greeks for a single option leg.

    Args:
        option_type: "call" or "put"

    Returns:
        dict with keys: delta, gamma, theta, vega
    """
    option_type = option_type.lower()
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got {option_type!r}")

    shared = {
        "gamma": gamma(S, K, T, r, sigma),
        "vega": vega(S, K, T, r, sigma),
    }
    if option_type == "call":
        return {
            "delta": call_delta(S, K, T, r, sigma),
            "theta": theta_call(S, K, T, r, sigma),
            **shared,
        }
    return {
        "delta": put_delta(S, K, T, r, sigma),
        "theta": theta_put(S, K, T, r, sigma),
        **shared,
    }
