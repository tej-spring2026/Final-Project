import yfinance as yf


def get_stock_price(ticker: str) -> str:
    ticker = ticker.upper().strip()
    data = yf.Ticker(ticker)
    price = data.fast_info.last_price

    if price is None:
        return None

    return f"${price:,.2f}"
