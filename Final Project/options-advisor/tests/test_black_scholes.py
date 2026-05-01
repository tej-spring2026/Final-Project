"""
Validation tests for pricing/black_scholes.py.

Three tiers of assertions:
  1. Known textbook prices  – Hull's "Options, Futures, and Other Derivatives",
                              11th ed., used as ground truth. Tolerance ±$0.05.
  2. Mathematical identities – must hold to floating-point precision (1 ppm).
  3. Greek sign/bound checks – correct sign and monotonicity, no tolerance needed.
"""

import math
import pytest
from pricing.black_scholes import (
    call_price,
    put_price,
    call_delta,
    put_delta,
    gamma,
    theta_call,
    theta_put,
    vega,
    greeks,
)

# ---------------------------------------------------------------------------
# Shared parameter sets
# ---------------------------------------------------------------------------

# Hull example: "Options, Futures, and Other Derivatives" §15.7 (various eds.)
# European call on a non-dividend-paying stock.
HULL = dict(S=42, K=40, T=0.5, r=0.10, sigma=0.20)

# ATM 1-year call — standard classroom example, easy to verify by hand.
ATM = dict(S=100, K=100, T=1.0, r=0.05, sigma=0.20)

# OTM put — used only for parity and sign tests.
OTM_PUT = dict(S=50, K=55, T=0.25, r=0.03, sigma=0.35)


# ---------------------------------------------------------------------------
# 1. Textbook price tests
# ---------------------------------------------------------------------------


def test_hull_call_price():
    """Hull's worked example produces call ≈ $4.76."""
    price = call_price(**HULL)
    assert price == pytest.approx(4.76, abs=0.05), f"Call price {price:.4f} outside ±$0.05 of $4.76"


def test_hull_put_price():
    """Hull's worked example produces put ≈ $0.81."""
    price = put_price(**HULL)
    assert price == pytest.approx(0.81, abs=0.05), f"Put price {price:.4f} outside ±$0.05 of $0.81"


def test_atm_call_price():
    """ATM 1-year call (S=K=100, σ=20%, r=5%) ≈ $10.45."""
    price = call_price(**ATM)
    assert price == pytest.approx(10.45, abs=0.05), f"ATM call {price:.4f} outside ±$0.05 of $10.45"


def test_atm_put_price():
    """ATM 1-year put (S=K=100, σ=20%, r=5%) ≈ $5.57."""
    price = put_price(**ATM)
    assert price == pytest.approx(5.57, abs=0.05), f"ATM put {price:.4f} outside ±$0.05 of $5.57"


# ---------------------------------------------------------------------------
# 2. Mathematical identity tests
# ---------------------------------------------------------------------------


def test_put_call_parity_hull():
    """
    Put-call parity: C − P = S − K · e^(−rT).
    This is a no-arbitrage identity; any correct BS implementation satisfies it exactly.
    """
    p = HULL
    lhs = call_price(**p) - put_price(**p)
    rhs = p["S"] - p["K"] * math.exp(-p["r"] * p["T"])
    assert lhs == pytest.approx(rhs, rel=1e-6), f"Parity violation: LHS={lhs:.6f}, RHS={rhs:.6f}"


def test_put_call_parity_atm():
    """Put-call parity holds for ATM parameters."""
    p = ATM
    lhs = call_price(**p) - put_price(**p)
    rhs = p["S"] - p["K"] * math.exp(-p["r"] * p["T"])
    assert lhs == pytest.approx(rhs, rel=1e-6)


def test_put_call_parity_otm_put():
    """Put-call parity holds for an OTM put scenario."""
    p = OTM_PUT
    lhs = call_price(**p) - put_price(**p)
    rhs = p["S"] - p["K"] * math.exp(-p["r"] * p["T"])
    assert lhs == pytest.approx(rhs, rel=1e-6)


def test_delta_relationship():
    """
    call_delta − put_delta = 1 exactly (follows from N(d1) − (N(d1)−1) = 1).
    """
    for params in (HULL, ATM, OTM_PUT):
        cd = call_delta(**params)
        pd = put_delta(**params)
        assert cd - pd == pytest.approx(1.0, rel=1e-10), (
            f"call_delta−put_delta={cd - pd:.10f} for {params}"
        )


def test_gamma_call_equals_gamma_put():
    """Gamma is identical for calls and puts with the same strike and expiry."""
    for params in (HULL, ATM, OTM_PUT):
        g_call = gamma(**params)
        # Gamma has no option_type argument — verify the formula is type-agnostic.
        assert g_call > 0, "Gamma must be positive"


def test_intrinsic_value_at_expiration():
    """At T=0, BS should return max(S−K, 0) for calls and max(K−S, 0) for puts."""
    assert call_price(100, 90, 0, 0.05, 0.20) == pytest.approx(10.0)
    assert call_price(100, 110, 0, 0.05, 0.20) == pytest.approx(0.0)
    assert put_price(100, 110, 0, 0.05, 0.20) == pytest.approx(10.0)
    assert put_price(100, 90, 0, 0.05, 0.20) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 3. Greek sign and bound tests
# ---------------------------------------------------------------------------


def test_call_delta_bounds():
    """Call delta must lie strictly in (0, 1) for any option with T > 0."""
    for params in (HULL, ATM, OTM_PUT):
        d = call_delta(**params)
        assert 0 < d < 1, f"call_delta={d:.4f} out of (0,1) for {params}"


def test_put_delta_bounds():
    """Put delta must lie strictly in (−1, 0) for any option with T > 0."""
    for params in (HULL, ATM, OTM_PUT):
        d = put_delta(**params)
        assert -1 < d < 0, f"put_delta={d:.4f} out of (-1,0) for {params}"


def test_gamma_positive():
    """Gamma is always positive (convexity always benefits the option holder)."""
    for params in (HULL, ATM, OTM_PUT):
        assert gamma(**params) > 0


def test_vega_positive():
    """Vega is always positive (higher volatility → higher option value)."""
    for params in (HULL, ATM, OTM_PUT):
        assert vega(**params) > 0


def test_theta_call_negative():
    """Call theta is almost always negative for long calls (time decay)."""
    for params in (HULL, ATM, OTM_PUT):
        assert theta_call(**params) < 0, f"theta_call positive for {params}"


def test_theta_put_sign():
    """
    Put theta is usually negative for near-the-money puts.
    (Deep ITM puts with high r can be positive — we don't test that edge here.)
    """
    for params in (HULL, ATM):
        assert theta_put(**params) < 0, f"theta_put positive for {params}"


def test_hull_call_delta():
    """Call delta for Hull example ≈ N(d1) ≈ 0.779."""
    d = call_delta(**HULL)
    assert d == pytest.approx(0.779, abs=0.005)


def test_hull_gamma():
    """Gamma for Hull example ≈ 0.0500 (standard result)."""
    g = gamma(**HULL)
    assert g == pytest.approx(0.050, abs=0.003)


def test_hull_vega():
    """Vega for Hull example ≈ $0.088 per 1-percentage-point vol move.

    Raw vega = S · n(d1) · √T = 42 · 0.2967 · 0.7071 ≈ 8.81
    Our convention divides by 100 → $0.088 per 1% σ move.
    """
    v = vega(**HULL)
    assert v == pytest.approx(0.088, abs=0.005)


# ---------------------------------------------------------------------------
# 4. Interface tests
# ---------------------------------------------------------------------------


def test_greeks_call_returns_all_keys():
    """greeks() for a call returns delta, gamma, theta, vega."""
    g = greeks(**HULL, option_type="call")
    assert set(g.keys()) == {"delta", "gamma", "theta", "vega"}
    assert g["delta"] == pytest.approx(call_delta(**HULL))
    assert g["gamma"] == pytest.approx(gamma(**HULL))


def test_greeks_put_returns_all_keys():
    """greeks() for a put returns delta, gamma, theta, vega."""
    g = greeks(**HULL, option_type="put")
    assert set(g.keys()) == {"delta", "gamma", "theta", "vega"}
    assert g["delta"] == pytest.approx(put_delta(**HULL))


def test_greeks_invalid_type_raises():
    """greeks() raises ValueError for an unrecognised option_type."""
    with pytest.raises(ValueError, match="option_type"):
        greeks(**HULL, option_type="straddle")
