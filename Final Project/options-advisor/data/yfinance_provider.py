"""
yfinance implementation of DataProvider.

No API key required. Data is typically 15-min delayed.

Known edge cases handled here:
  - bid/ask for the underlying are unavailable via fast_info outside market
    hours; we expose 0.0 (the downstream IV solver uses price, not bid/ask).
  - Volume, openInterest, and bid/ask on individual contracts are often NaN
    for deep ITM/OTM strikes or after-hours — coerced to 0.0 / 0.
  - Today's expiration may appear in the list; get_chain will still return it,
    but T will be ~0 and IV solving will return None for those contracts.
  - Low-volume tickers sometimes return empty chains for certain expirations.
"""

import pandas as pd
import yfinance as yf

from data.provider import DataProvider, OptionContract, Quote


class YFinanceProvider(DataProvider):
    """Concrete DataProvider backed by the yfinance library."""

    def get_quote(self, ticker: str) -> Quote:
        """
        Return current spot price for *ticker*.

        Uses fast_info for speed; falls back to previous_close if last_price
        is unavailable (can happen for tickers with no recent trades).
        """
        ticker = ticker.upper().strip()
        try:
            fi = yf.Ticker(ticker).fast_info
            price = fi.last_price
            if price is None or (isinstance(price, float) and pd.isna(price)):
                price = fi.previous_close
        except Exception as exc:
            raise RuntimeError(
                f"Could not fetch quote for {ticker!r}: {exc}"
            ) from exc

        if price is None or (isinstance(price, float) and pd.isna(price)):
            raise RuntimeError(
                f"No price data for {ticker!r}. "
                "Verify the ticker symbol and try again."
            )

        # fast_info does not expose underlying bid/ask — not needed for BS.
        return Quote(ticker=ticker, price=float(price), bid=0.0, ask=0.0)

    def get_expirations(self, ticker: str) -> list[str]:
        """
        Return available option expiration dates as ISO strings, sorted ascending.

        yfinance already returns them sorted; we make the contract explicit.
        """
        ticker = ticker.upper().strip()
        try:
            exps = yf.Ticker(ticker).options
        except Exception as exc:
            raise RuntimeError(
                f"Could not fetch expirations for {ticker!r}: {exc}"
            ) from exc

        if not exps:
            raise RuntimeError(
                f"No options data for {ticker!r}. "
                "The ticker may not have listed options, or the symbol is wrong."
            )

        return sorted(exps)

    def get_chain(self, ticker: str, expiration: str) -> list[OptionContract]:
        """
        Return all option contracts for *ticker* expiring on *expiration*.

        Contracts are sorted: calls first, then puts; ascending by strike within
        each type. This ordering is stable and matches typical chain displays.
        """
        ticker = ticker.upper().strip()
        try:
            raw = yf.Ticker(ticker).option_chain(expiration)
        except Exception as exc:
            raise RuntimeError(
                f"Could not fetch chain for {ticker!r} exp={expiration!r}: {exc}"
            ) from exc

        contracts: list[OptionContract] = []
        for opt_type, df in (("call", raw.calls), ("put", raw.puts)):
            if df is None or df.empty:
                continue
            for _, row in df.iterrows():
                contracts.append(
                    OptionContract(
                        symbol=str(row.get("contractSymbol", "")),
                        option_type=opt_type,
                        strike=float(row["strike"]),
                        expiration=expiration,
                        bid=_safe_float(row.get("bid")),
                        ask=_safe_float(row.get("ask")),
                        last=_safe_float(row.get("lastPrice")),
                        volume=_safe_int(row.get("volume")),
                        open_interest=_safe_int(row.get("openInterest")),
                    )
                )

        if not contracts:
            raise RuntimeError(
                f"Chain for {ticker!r} exp={expiration!r} returned no contracts. "
                "Try a different expiration or check the ticker."
            )

        # calls before puts, ascending by strike within each group
        contracts.sort(key=lambda c: (c.option_type != "call", c.strike))
        return contracts


# ---------------------------------------------------------------------------
# NaN-safe coercion helpers (pandas fields are often float even for ints)
# ---------------------------------------------------------------------------

def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        f = float(val)
        return 0.0 if pd.isna(f) else f
    except (TypeError, ValueError):
        return 0.0


def _safe_int(val) -> int:
    if val is None:
        return 0
    try:
        f = float(val)
        return 0 if pd.isna(f) else int(f)
    except (TypeError, ValueError):
        return 0
