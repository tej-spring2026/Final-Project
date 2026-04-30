"""
Abstract base class for market data providers.

Concrete implementations live alongside this file (yfinance_provider.py, etc.).
The rest of the app only imports DataProvider — swapping backends never touches
routes, pricing, or AI code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Quote:
    """Live (or delayed) spot price for an underlying."""
    ticker: str
    price: float    # last trade / mid
    bid: float
    ask: float


@dataclass
class OptionContract:
    """A single row from an options chain."""
    symbol: str          # OCC option symbol, e.g. "SPY251219C00500000"
    option_type: str     # "call" or "put"
    strike: float
    expiration: str      # ISO date string "YYYY-MM-DD"
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int

    # Optional: provider-supplied IV and Greeks (e.g. from Tradier/ORATS).
    # When set, _fetch_chain skips the Newton-Raphson solver for this contract.
    provided_iv: float | None = None       # decimal form (0.45 = 45%)
    provided_greeks: dict | None = None   # keys: delta, gamma, theta, vega

    @property
    def mid(self) -> float:
        """Mid-price used for IV solving and display."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        if self.last > 0:
            return self.last
        return 0.0


class DataProvider(ABC):
    """
    Interface every data backend must satisfy.

    Implementations should raise a descriptive exception (not return None)
    when data is unavailable — the Flask layer will catch and surface it.
    """

    @abstractmethod
    def get_quote(self, ticker: str) -> Quote:
        """Return the current spot price for *ticker*."""
        ...

    @abstractmethod
    def get_expirations(self, ticker: str) -> list[str]:
        """Return available option expiration dates as sorted ISO strings."""
        ...

    @abstractmethod
    def get_chain(self, ticker: str, expiration: str) -> list[OptionContract]:
        """
        Return all option contracts for *ticker* expiring on *expiration*.

        Args:
            ticker:     e.g. "SPY"
            expiration: ISO date string "YYYY-MM-DD"
        """
        ...
