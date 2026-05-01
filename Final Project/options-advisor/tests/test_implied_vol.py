"""
Tests for pricing/implied_vol.py.

Strategy:
  Round-trip tests: pick a known sigma, compute BS price, feed price back into
  the solver, and verify we recover the original sigma. This avoids relying on
  external "true" IV values, but is a rigorous end-to-end check of the solver.

  Edge-case tests: expired options, bad inputs, arbitrage violations.
"""

import pytest
from pricing.black_scholes import call_price, put_price
from pricing.implied_vol import implied_vol

R = 0.048  # matches config.RISK_FREE_RATE


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _round_trip(S, K, T, sigma, option_type):
    """Compute BS price at sigma, then recover sigma from that price."""
    pricer = call_price if option_type == "call" else put_price
    price = pricer(S, K, T, R, sigma)
    recovered = implied_vol(price, S, K, T, R, option_type)
    return recovered


# ---------------------------------------------------------------------------
# 1. Parametrised round-trip accuracy
# ---------------------------------------------------------------------------

ROUND_TRIP_CASES = [
    # (S, K, T, sigma, option_type, description)
    (100, 100, 1.0,  0.20, "call", "ATM 1yr call"),
    (100, 100, 1.0,  0.20, "put",  "ATM 1yr put"),
    (100, 110, 0.5,  0.25, "call", "OTM 6mo call"),
    (100,  90, 0.5,  0.25, "put",  "OTM 6mo put"),
    (42,   40, 0.5,  0.20, "call", "Hull-like near-ATM call"),
    (100,  80, 0.25, 0.35, "call", "ITM 3mo call"),
    (100, 120, 0.25, 0.35, "put",  "ITM 3mo put"),
]

@pytest.mark.parametrize("S,K,T,sigma,opt,desc", ROUND_TRIP_CASES)
def test_round_trip(S, K, T, sigma, opt, desc):
    """Recovered IV must match input sigma within 0.01% (1 basis point)."""
    recovered = _round_trip(S, K, T, sigma, opt)
    assert recovered is not None, f"Solver returned None for: {desc}"
    assert recovered == pytest.approx(sigma, abs=1e-4), (
        f"{desc}: input={sigma:.4f}, recovered={recovered:.6f}"
    )


# ---------------------------------------------------------------------------
# 2. Accuracy across a wide volatility range
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target_sigma", [0.05, 0.10, 0.20, 0.30, 0.50, 0.80, 1.50])
def test_accuracy_across_vol_range(target_sigma):
    """
    Solver is accurate from very low vol (5%) through very high vol (150%).
    Uses ATM call so BS is well-conditioned throughout.
    """
    S, K, T = 100, 100, 0.5
    price = call_price(S, K, T, R, target_sigma)
    recovered = implied_vol(price, S, K, T, R, "call")
    assert recovered is not None
    assert recovered == pytest.approx(target_sigma, abs=1e-4), (
        f"Failed at sigma={target_sigma}: recovered={recovered}"
    )


@pytest.mark.parametrize("target_sigma", [0.05, 0.10, 0.20, 0.30, 0.50, 0.80, 1.50])
def test_accuracy_puts(target_sigma):
    """Same sweep for puts."""
    S, K, T = 100, 100, 0.5
    price = put_price(S, K, T, R, target_sigma)
    recovered = implied_vol(price, S, K, T, R, "put")
    assert recovered is not None
    assert recovered == pytest.approx(target_sigma, abs=1e-4)


# ---------------------------------------------------------------------------
# 3. Edge-case / guard tests
# ---------------------------------------------------------------------------

def test_expired_option_returns_none():
    """T=0 → IV undefined → None."""
    assert implied_vol(5.0, 100, 95, 0, R, "call") is None


def test_negative_T_returns_none():
    """Negative T (settlement already happened) → None."""
    assert implied_vol(5.0, 100, 95, -0.01, R, "call") is None


def test_zero_price_returns_none():
    """A $0 option has no meaningful IV."""
    assert implied_vol(0.0, 100, 100, 1.0, R, "call") is None


def test_negative_price_returns_none():
    """A negative price is impossible."""
    assert implied_vol(-1.0, 100, 100, 1.0, R, "call") is None


def test_below_intrinsic_call_returns_none():
    """
    Call price below intrinsic (S−K) violates no-arbitrage.
    S=110, K=100 → intrinsic=$10; market_price=$3 is invalid.
    """
    assert implied_vol(3.0, 110, 100, 1.0, R, "call") is None


def test_below_intrinsic_put_returns_none():
    """
    Put price below intrinsic (K−S) violates no-arbitrage.
    S=90, K=100 → intrinsic=$10; market_price=$4 is invalid.
    """
    assert implied_vol(4.0, 90, 100, 1.0, R, "put") is None


def test_invalid_option_type_raises():
    """Unknown option_type raises ValueError with a helpful message."""
    with pytest.raises(ValueError, match="option_type"):
        implied_vol(5.0, 100, 100, 1.0, R, "straddle")


# ---------------------------------------------------------------------------
# 4. Consistency: recovered IV used in BS gives back the original price
# ---------------------------------------------------------------------------

def test_price_consistency_call():
    """
    Recover IV from a BS price, plug it back in: should reproduce the price.
    Stronger than round-trip (round-trips sigma; this round-trips price).
    """
    S, K, T, sigma = 100, 95, 0.4, 0.28
    original_price = call_price(S, K, T, R, sigma)
    iv = implied_vol(original_price, S, K, T, R, "call")
    reproduced_price = call_price(S, K, T, R, iv)
    assert reproduced_price == pytest.approx(original_price, abs=1e-5)


def test_price_consistency_put():
    """Same price-consistency check for puts."""
    S, K, T, sigma = 100, 105, 0.4, 0.28
    original_price = put_price(S, K, T, R, sigma)
    iv = implied_vol(original_price, S, K, T, R, "put")
    reproduced_price = put_price(S, K, T, R, iv)
    assert reproduced_price == pytest.approx(original_price, abs=1e-5)
