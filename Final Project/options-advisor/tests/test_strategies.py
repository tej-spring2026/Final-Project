"""
Tests for pricing/strategies.py and pricing/payoff.py.

All monetary assertions are in dollars per contract (1 contract = 100 shares).

Fixed date anchors make aggregate_greeks tests deterministic regardless of
when the test suite runs.
"""

import math
from datetime import date

import pytest

from pricing.black_scholes import call_price, put_price
from pricing.payoff import build_payoff
from pricing.strategies import Leg, Strategy

# ---------------------------------------------------------------------------
# Fixed date anchors — ensures T is constant across test runs
# ---------------------------------------------------------------------------
AS_OF = date(2024, 1, 1)
EXP = "2024-07-01"          # 182 days after AS_OF → T ≈ 0.498 yr

S = 100.0
R = 0.048
SIGMA = 0.20
T_FIXED = (date.fromisoformat(EXP) - AS_OF).days / 365.0

# Entry prices computed from BS so the IV round-trip is exact in Greek tests
CALL_ENTRY = call_price(S, S, T_FIXED, R, SIGMA)   # ATM call
PUT_ENTRY = put_price(S, S, T_FIXED, R, SIGMA)     # ATM put


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def long_call(K=100.0, entry=5.0, q=1) -> Strategy:
    return Strategy([Leg("call", K, EXP, q, entry)])

def long_put(K=100.0, entry=4.0, q=1) -> Strategy:
    return Strategy([Leg("put", K, EXP, q, entry)])

def short_call(K=100.0, entry=5.0) -> Strategy:
    return Strategy([Leg("call", K, EXP, -1, entry)])

def short_put(K=100.0, entry=3.0) -> Strategy:
    return Strategy([Leg("put", K, EXP, -1, entry)])


# ===========================================================================
# 1. net_debit_credit
# ===========================================================================

def test_long_call_debit():
    """Long call: debit = entry_price × 100 (positive)."""
    assert long_call(K=100, entry=5.0).net_debit_credit() == pytest.approx(500.0)

def test_short_put_credit():
    """Short put: credit = −entry_price × 100 (negative)."""
    assert short_put(K=100, entry=3.0).net_debit_credit() == pytest.approx(-300.0)

def test_bull_call_spread_debit():
    """Bull call spread: net = (long_price − short_price) × 100."""
    s = Strategy([
        Leg("call", 95,  EXP, +1, 8.0),
        Leg("call", 105, EXP, -1, 3.0),
    ])
    assert s.net_debit_credit() == pytest.approx(500.0)

def test_credit_spread_is_negative():
    """Bull put spread (sell high-strike put, buy low-strike put) is a credit."""
    s = Strategy([
        Leg("put", 105, EXP, -1, 10.0),   # sold the higher-strike put
        Leg("put",  95, EXP, +1,  5.0),   # bought the lower-strike put
    ])
    assert s.net_debit_credit() == pytest.approx(-500.0)  # $500 credit


# ===========================================================================
# 2. max_profit / max_loss — single legs
# ===========================================================================

def test_long_call_max_profit_infinite():
    """Long call: profit is unlimited — stock can go to infinity."""
    assert long_call().max_profit() == float("inf")

def test_long_call_max_loss():
    """Long call: max loss = premium paid = $500 (if entry=5)."""
    assert long_call(entry=5.0).max_loss() == pytest.approx(-500.0)

def test_long_put_max_profit():
    """Long put: max profit at S=0 is (K − entry) × 100."""
    assert long_put(K=100, entry=4.0).max_profit() == pytest.approx(9600.0)

def test_long_put_max_loss():
    """Long put: max loss = premium paid."""
    assert long_put(entry=4.0).max_loss() == pytest.approx(-400.0)

def test_short_call_max_loss_infinite():
    """Naked short call: loss unlimited — stock can go to infinity."""
    assert short_call().max_loss() == float("-inf")

def test_short_call_max_profit():
    """Naked short call: max profit = premium received."""
    assert short_call(entry=5.0).max_profit() == pytest.approx(500.0)

def test_short_put_max_profit():
    """Short put: max profit = premium received."""
    assert short_put(entry=3.0).max_profit() == pytest.approx(300.0)

def test_short_put_max_loss():
    """Short put: max loss = (−K + entry) × 100 — if stock goes to zero."""
    assert short_put(K=100, entry=3.0).max_loss() == pytest.approx(-9700.0)


# ===========================================================================
# 3. max_profit / max_loss — multi-leg (capped strategies)
# ===========================================================================

def test_bull_call_spread_max_profit():
    """Bull call spread max profit = (spread_width − net_debit) × 100."""
    s = Strategy([
        Leg("call", 95,  EXP, +1, 8.0),
        Leg("call", 105, EXP, -1, 3.0),
    ])
    # Width=10, net_debit=5 → max profit=5 per share = $500
    assert s.max_profit() == pytest.approx(500.0)

def test_bull_call_spread_max_loss():
    """Bull call spread max loss = net debit paid."""
    s = Strategy([
        Leg("call", 95,  EXP, +1, 8.0),
        Leg("call", 105, EXP, -1, 3.0),
    ])
    assert s.max_loss() == pytest.approx(-500.0)

def test_long_straddle_max_loss():
    """Long straddle: max loss = total premium paid (at the shared strike)."""
    s = Strategy([
        Leg("call", 100, EXP, +1, 5.0),
        Leg("put",  100, EXP, +1, 4.0),
    ])
    assert s.max_loss() == pytest.approx(-900.0)  # (5+4) × 100

def test_long_straddle_max_profit_infinite():
    """Long straddle: max profit is unlimited (long call)."""
    s = Strategy([
        Leg("call", 100, EXP, +1, 5.0),
        Leg("put",  100, EXP, +1, 4.0),
    ])
    assert s.max_profit() == float("inf")

def test_bear_put_spread_max_profit():
    """Bear put spread: max profit = (spread_width − net_debit) × 100."""
    s = Strategy([
        Leg("put", 105, EXP, +1, 8.0),   # long higher-strike put
        Leg("put",  95, EXP, -1, 3.0),   # short lower-strike put
    ])
    # Width=10, debit=5 → max profit=5 per share = $500
    assert s.max_profit() == pytest.approx(500.0)


# ===========================================================================
# 4. breakevens
# ===========================================================================

def test_long_call_breakeven():
    """Long call breakeven = strike + premium."""
    be = long_call(K=100, entry=5.0).breakevens()
    assert len(be) == 1
    assert be[0] == pytest.approx(105.0, abs=0.01)

def test_long_put_breakeven():
    """Long put breakeven = strike − premium."""
    be = long_put(K=100, entry=4.0).breakevens()
    assert len(be) == 1
    assert be[0] == pytest.approx(96.0, abs=0.01)

def test_short_call_breakeven():
    """Short call breakeven = strike + premium received."""
    be = short_call(K=100, entry=5.0).breakevens()
    assert len(be) == 1
    assert be[0] == pytest.approx(105.0, abs=0.01)

def test_short_put_breakeven():
    """Short put breakeven = strike − premium received."""
    be = short_put(K=100, entry=3.0).breakevens()
    assert len(be) == 1
    assert be[0] == pytest.approx(97.0, abs=0.01)

def test_bull_call_spread_breakeven():
    """Bull call spread: single breakeven = low_strike + net_debit."""
    s = Strategy([
        Leg("call", 95,  EXP, +1, 8.0),
        Leg("call", 105, EXP, -1, 3.0),
    ])
    be = s.breakevens()
    assert len(be) == 1
    assert be[0] == pytest.approx(100.0, abs=0.01)

def test_long_straddle_two_breakevens():
    """Long straddle: two breakevens at K ± total_premium."""
    s = Strategy([
        Leg("call", 100, EXP, +1, 5.0),
        Leg("put",  100, EXP, +1, 4.0),
    ])
    be = s.breakevens()
    assert len(be) == 2
    assert be[0] == pytest.approx(91.0, abs=0.01)   # K − (5+4)
    assert be[1] == pytest.approx(109.0, abs=0.01)  # K + (5+4)


# ===========================================================================
# 5. aggregate_greeks
# ===========================================================================

def test_long_call_delta_positive(tmp_path):
    """Long call aggregate delta is in (0, 1)."""
    s = Strategy([Leg("call", S, EXP, +1, CALL_ENTRY)])
    g = s.aggregate_greeks(S, R, as_of=AS_OF)
    assert 0 < g["delta"] < 1

def test_long_put_delta_negative():
    """Long put aggregate delta is in (−1, 0)."""
    s = Strategy([Leg("put", S, EXP, +1, PUT_ENTRY)])
    g = s.aggregate_greeks(S, R, as_of=AS_OF)
    assert -1 < g["delta"] < 0

def test_short_call_delta_negative():
    """Short call (q=−1) aggregate delta is in (−1, 0)."""
    s = Strategy([Leg("call", S, EXP, -1, CALL_ENTRY)])
    g = s.aggregate_greeks(S, R, as_of=AS_OF)
    assert -1 < g["delta"] < 0

def test_short_put_delta_positive():
    """Short put (q=−1) aggregate delta is in (0, 1)."""
    s = Strategy([Leg("put", S, EXP, -1, PUT_ENTRY)])
    g = s.aggregate_greeks(S, R, as_of=AS_OF)
    assert 0 < g["delta"] < 1

def test_long_straddle_delta_near_zero():
    """Long ATM straddle: call delta + put delta ≈ 0 (symmetric)."""
    s = Strategy([
        Leg("call", S, EXP, +1, CALL_ENTRY),
        Leg("put",  S, EXP, +1, PUT_ENTRY),
    ])
    g = s.aggregate_greeks(S, R, as_of=AS_OF)
    # ATM call delta ≈ 0.56, ATM put delta ≈ -0.44 → net ≈ 0.12 (not exactly 0
    # because N(d1) ≠ 0.5 unless r=0; just verify it's in a reasonable range)
    assert -0.5 < g["delta"] < 0.5

def test_aggregate_greeks_keys():
    """aggregate_greeks returns all four expected keys."""
    s = Strategy([Leg("call", S, EXP, +1, CALL_ENTRY)])
    g = s.aggregate_greeks(S, R, as_of=AS_OF)
    assert set(g.keys()) == {"delta", "gamma", "theta", "vega"}

def test_aggregate_greeks_gamma_positive():
    """Long options always contribute positive gamma."""
    for leg_type in ("call", "put"):
        entry = CALL_ENTRY if leg_type == "call" else PUT_ENTRY
        s = Strategy([Leg(leg_type, S, EXP, +1, entry)])
        g = s.aggregate_greeks(S, R, as_of=AS_OF)
        assert g["gamma"] > 0

def test_aggregate_greeks_vega_positive():
    """Long options always contribute positive vega."""
    for leg_type in ("call", "put"):
        entry = CALL_ENTRY if leg_type == "call" else PUT_ENTRY
        s = Strategy([Leg(leg_type, S, EXP, +1, entry)])
        g = s.aggregate_greeks(S, R, as_of=AS_OF)
        assert g["vega"] > 0

def test_bull_spread_greeks_delta_reduced():
    """
    Bull call spread has lower delta than a standalone long call
    (the short call hedges some directional exposure).
    """
    solo = Strategy([Leg("call", 95, EXP, +1, 8.0)])

    # For the spread short leg, use a reasonable OTM price
    otm_price = call_price(S, 105, T_FIXED, R, SIGMA)
    spread = Strategy([
        Leg("call", 95,  EXP, +1, 8.0),
        Leg("call", 105, EXP, -1, otm_price),
    ])
    g_solo = solo.aggregate_greeks(S, R, as_of=AS_OF)
    g_spread = spread.aggregate_greeks(S, R, as_of=AS_OF)
    assert g_spread["delta"] < g_solo["delta"]


# ===========================================================================
# 6. payoff.py — build_payoff
# ===========================================================================

def test_build_payoff_structure():
    """build_payoff returns the expected keys with correct array lengths."""
    s = long_call(K=100, entry=5.0)
    result = build_payoff(s, num_points=100)
    assert set(result.keys()) == {
        "price_range", "pnl", "breakevens", "max_profit", "max_loss", "net_debit_credit"
    }
    assert len(result["price_range"]) == 100
    assert len(result["pnl"]) == 100

def test_build_payoff_monotone_prices():
    """price_range is strictly increasing."""
    result = build_payoff(long_call(), num_points=50)
    prices = result["price_range"]
    assert all(prices[i] < prices[i + 1] for i in range(len(prices) - 1))

def test_build_payoff_breakevens_consistent():
    """
    Breakevens reported in the dict match a near-zero P/L in the pnl array
    (within the array resolution).
    """
    s = long_call(K=100, entry=5.0)
    result = build_payoff(s, num_points=1000)
    for be in result["breakevens"]:
        # Find closest price in the array
        closest_idx = min(
            range(len(result["price_range"])),
            key=lambda i: abs(result["price_range"][i] - be),
        )
        pnl_at_be = result["pnl"][closest_idx]
        assert abs(pnl_at_be) < 20.0  # within $20 of zero given array resolution

def test_build_payoff_empty_strategy_raises():
    """build_payoff raises ValueError for an empty Strategy."""
    with pytest.raises(ValueError, match="empty"):
        build_payoff(Strategy())

def test_build_payoff_long_call_shape():
    """Long call P/L is monotonically increasing in the upper half of the range."""
    result = build_payoff(long_call(K=100, entry=5.0), num_points=200)
    prices = result["price_range"]
    pnl = result["pnl"]
    # Find index of strike price
    idx_strike = min(range(len(prices)), key=lambda i: abs(prices[i] - 100.0))
    # P/L above the strike should be strictly increasing
    upper_pnl = pnl[idx_strike:]
    assert all(upper_pnl[i] <= upper_pnl[i + 1] for i in range(len(upper_pnl) - 1))

def test_build_payoff_spread_pnl_capped():
    """Bull call spread P/L is capped — never exceeds max_profit."""
    s = Strategy([
        Leg("call", 95,  EXP, +1, 8.0),
        Leg("call", 105, EXP, -1, 3.0),
    ])
    result = build_payoff(s, num_points=500)
    mp = result["max_profit"]
    # All pnl values should be ≤ max_profit + small numerical tolerance
    assert all(v <= mp + 1.0 for v in result["pnl"])
