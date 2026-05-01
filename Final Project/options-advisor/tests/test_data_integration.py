"""
Integration smoke test — makes real network calls to yfinance.

Run with:
    pytest tests/test_data_integration.py -v -s -m integration

The -s flag lets print() output through so you can see the formatted table.
Omit -m integration from your normal test run to skip these.
"""

from datetime import date

import pytest

import config
from data.yfinance_provider import YFinanceProvider
from pricing.black_scholes import greeks
from pricing.implied_vol import implied_vol

TICKER = "SPY"


@pytest.fixture(scope="module")
def provider():
    return YFinanceProvider()


@pytest.fixture(scope="module")
def quote(provider):
    return provider.get_quote(TICKER)


@pytest.fixture(scope="module")
def valid_expiration(provider):
    """First expiration at least 5 calendar days out — ensures T is meaningful."""
    exps = provider.get_expirations(TICKER)
    today = date.today()
    for exp in exps:
        if (date.fromisoformat(exp) - today).days >= 5:
            return exp
    pytest.skip("No expiration >= 5 days out found (unusual market condition)")


@pytest.fixture(scope="module")
def chain(provider, valid_expiration):
    return provider.get_chain(TICKER, valid_expiration)


# ---------------------------------------------------------------------------
# Structural / type tests (fast, just inspect what we got)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_quote_structure(quote):
    """Quote has a positive price and correct ticker."""
    assert quote.ticker == TICKER
    assert quote.price > 0, f"Expected positive price, got {quote.price}"
    print(f"\n  {TICKER} spot: ${quote.price:.2f}")


@pytest.mark.integration
def test_expirations_sorted_and_nonempty(provider):
    """get_expirations returns a non-empty sorted list of ISO date strings."""
    exps = provider.get_expirations(TICKER)
    assert len(exps) > 0
    assert exps == sorted(exps), "Expirations are not sorted"
    # Validate ISO format
    for exp in exps[:5]:
        date.fromisoformat(exp)  # raises if malformed
    print(f"\n  {TICKER} expirations ({len(exps)} total): {exps[:5]} ...")


@pytest.mark.integration
def test_chain_nonempty(chain, valid_expiration):
    """Chain has both calls and puts."""
    calls = [c for c in chain if c.option_type == "call"]
    puts = [c for c in chain if c.option_type == "put"]
    assert len(calls) > 0, "No calls in chain"
    assert len(puts) > 0, "No puts in chain"
    print(f"\n  Chain for {valid_expiration}: {len(chain)} contracts "
          f"({len(calls)} calls, {len(puts)} puts)")


@pytest.mark.integration
def test_chain_sorted(chain):
    """Contracts are ordered: calls first, ascending strike within each type."""
    calls = [c for c in chain if c.option_type == "call"]
    puts = [c for c in chain if c.option_type == "put"]
    assert calls == sorted(calls, key=lambda c: c.strike)
    assert puts == sorted(puts, key=lambda c: c.strike)
    # All calls appear before all puts
    call_indices = [i for i, c in enumerate(chain) if c.option_type == "call"]
    put_indices = [i for i, c in enumerate(chain) if c.option_type == "put"]
    assert max(call_indices) < min(put_indices)


@pytest.mark.integration
def test_contract_fields(chain):
    """Every contract has a strike > 0 and a non-empty symbol."""
    for c in chain:
        assert c.strike > 0
        assert len(c.symbol) > 0
        assert c.option_type in ("call", "put")
        assert c.bid >= 0
        assert c.ask >= 0
        assert c.last >= 0


@pytest.mark.integration
def test_mid_price_fallback(chain):
    """
    OptionContract.mid falls back to last when bid=ask=0.
    Outside market hours, bid/ask are often 0 — confirm mid is still useful.
    """
    zero_spread = [c for c in chain if c.bid == 0 and c.ask == 0]
    if zero_spread:
        for c in zero_spread[:3]:
            # mid should be last (or 0 if last is also 0)
            assert c.mid == c.last


# ---------------------------------------------------------------------------
# Full pipeline: data → IV → Greeks
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_full_pipeline_near_atm(quote, chain, valid_expiration):
    """
    For the 6 closest-to-ATM contracts (3 calls, 3 puts), compute IV and Greeks.
    Prints a formatted table so you can visually inspect the results.
    """
    S = quote.price
    r = config.RISK_FREE_RATE
    today = date.today()
    T = (date.fromisoformat(valid_expiration) - today).days / 365.0

    assert T > 0, "Time to expiration must be positive"

    calls = sorted(
        [c for c in chain if c.option_type == "call"],
        key=lambda c: abs(c.strike - S),
    )[:3]
    puts = sorted(
        [c for c in chain if c.option_type == "put"],
        key=lambda c: abs(c.strike - S),
    )[:3]

    print(f"\n  Pipeline test — {TICKER} @ ${S:.2f}, exp={valid_expiration} (T={T:.4f} yr)")
    print(f"  {'Type':<5} {'Strike':>7} {'Mid':>7} {'IV':>8} {'Delta':>7} {'Gamma':>7} {'Theta':>8} {'Vega':>7}")
    print(f"  {'-'*5} {'-'*7} {'-'*7} {'-'*8} {'-'*7} {'-'*7} {'-'*8} {'-'*7}")

    any_iv_found = False
    for c in calls + puts:
        mid = c.mid
        if mid <= 0:
            continue

        iv = implied_vol(mid, S, c.strike, T, r, c.option_type)
        if iv is None:
            print(f"  {c.option_type.upper():<5} {c.strike:>7.1f} {mid:>7.2f} {'N/A':>8}")
            continue

        any_iv_found = True
        g = greeks(S, c.strike, T, r, iv, c.option_type)
        print(
            f"  {c.option_type.upper():<5} {c.strike:>7.1f} {mid:>7.2f} "
            f"{iv*100:>7.1f}%  {g['delta']:>7.3f} {g['gamma']:>7.4f} "
            f"{g['theta']:>8.4f} {g['vega']:>7.4f}"
        )

        # Structural assertions on the Greeks
        if c.option_type == "call":
            assert 0 < g["delta"] < 1, f"Call delta {g['delta']} out of range"
        else:
            assert -1 < g["delta"] < 0, f"Put delta {g['delta']} out of range"
        assert g["gamma"] > 0
        assert g["vega"] > 0
        assert g["theta"] < 0

    assert any_iv_found, (
        "Could not compute IV for any near-ATM contract. "
        "All mids were 0 — this can happen if the market is closed and "
        "yfinance returns stale zero bid/ask with no last price for this expiration."
    )
