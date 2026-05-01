"""
Tradier sandbox implementation of DataProvider.

Uses the Tradier Developer Sandbox (sandbox.tradier.com) which provides
real-time options data with Greeks pre-computed by ORATS. No API key is
needed beyond a free sandbox account token.

Requires env vars:
    TRADIER_SANDBOX_TOKEN    — Bearer token from sandbox.tradier.com
    TRADIER_SANDBOX_BASE_URL — defaults to https://sandbox.tradier.com/v1

Why Tradier over yfinance (iteration 2 decision):
    yfinance call-side data proved unreliable during testing — bid=0 stubs
    across deep-OTM strikes produced garbage implied vols even after adding
    the Newton-Raphson noise floor. Tradier returns exchange-quality quotes
    with ORATS Greeks, eliminating both problems cleanly.
"""

from __future__ import annotations

import requests

from data.provider import DataProvider, OptionContract, Quote


class TradierProvider(DataProvider):
    """Concrete DataProvider backed by the Tradier sandbox REST API."""

    def __init__(self, token: str, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal HTTP helper
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self._base_url}{path}"
        try:
            resp = requests.get(url, headers=self._headers, params=params, timeout=10)
        except requests.RequestException as exc:
            raise RuntimeError(f"Tradier network error: {exc}") from exc
        if resp.status_code != 200:
            raise RuntimeError(
                f"Tradier API returned {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()

    # ------------------------------------------------------------------
    # DataProvider interface
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> Quote:
        ticker = ticker.upper().strip()
        data = self._get("/markets/quotes", params={"symbols": ticker})
        q = data["quotes"]["quote"]
        if isinstance(q, list):
            q = q[0]

        price = _safe_float(q.get("last")) or _safe_float(q.get("close"))
        if not price:
            raise RuntimeError(
                f"No price data for {ticker!r} from Tradier. "
                "Verify the ticker symbol and try again."
            )

        return Quote(
            ticker=ticker,
            price=price,
            bid=_safe_float(q.get("bid")) or 0.0,
            ask=_safe_float(q.get("ask")) or 0.0,
        )

    def get_expirations(self, ticker: str) -> list[str]:
        ticker = ticker.upper().strip()
        data = self._get(
            "/markets/options/expirations",
            params={"symbol": ticker, "includeAllRoots": "true"},
        )
        expirations = data.get("expirations") or {}
        dates = expirations.get("date")
        if not dates:
            raise RuntimeError(
                f"No options expirations for {ticker!r} from Tradier. "
                "The ticker may not have listed options, or the symbol is wrong."
            )
        if isinstance(dates, str):
            dates = [dates]
        return sorted(dates)

    def get_chain(self, ticker: str, expiration: str) -> list[OptionContract]:
        ticker = ticker.upper().strip()
        data = self._get(
            "/markets/options/chains",
            params={"symbol": ticker, "expiration": expiration, "greeks": "true"},
        )
        options = (data.get("options") or {}).get("option")
        if not options:
            raise RuntimeError(
                f"Chain for {ticker!r} exp={expiration!r} returned no contracts. "
                "Try a different expiration or check the ticker."
            )
        if isinstance(options, dict):
            options = [options]

        contracts: list[OptionContract] = []
        for opt in options:
            bid  = _safe_float(opt.get("bid"))  or 0.0
            ask  = _safe_float(opt.get("ask"))  or 0.0
            last = _safe_float(opt.get("last")) or 0.0

            # ORATS Greeks from the 'greeks' sub-object
            g = opt.get("greeks") or {}
            # mid_iv preferred; fall back to bid_iv or ask_iv if mid is absent
            iv_raw = g.get("mid_iv") or g.get("bid_iv") or g.get("ask_iv")
            provided_iv = (_safe_float(iv_raw) or None)  # None when 0 or missing

            provided_greeks: dict | None = None
            if g:
                provided_greeks = {}
                for field in ("delta", "gamma", "theta", "vega"):
                    val = _safe_float(g.get(field))
                    if val is not None:
                        provided_greeks[field] = round(val, 4)

            contracts.append(
                OptionContract(
                    symbol=str(opt.get("symbol", "")),
                    option_type=str(opt.get("option_type", "")).lower(),
                    strike=float(opt["strike"]),
                    expiration=expiration,
                    bid=bid,
                    ask=ask,
                    last=last,
                    volume=_safe_int(opt.get("volume")),
                    open_interest=_safe_int(opt.get("open_interest")),
                    provided_iv=provided_iv,
                    provided_greeks=provided_greeks,
                )
            )

        contracts.sort(key=lambda c: (c.option_type != "call", c.strike))
        return contracts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return None if f != f else f   # NaN guard
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> int:
    if val is None:
        return 0
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return 0
