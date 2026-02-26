"""
Portfolio Analysis CLI Tool
A command-line application for analyzing stock portfolios.
Users input stock holdings and receive analysis including allocation, returns, and risk metrics.
"""


def format_currency(amount):
    """Format a number as currency (e.g., $1,234.56)."""
    return f"${amount:,.2f}"


def format_percentage(value, decimals=2):
    """Format a number as a percentage (e.g., 12.34%)."""
    return f"{value:.{decimals}f}%"


def get_stock_input(existing_tickers):
    """
    Prompt user for a single stock's data with validation.

    Args:
        existing_tickers: List of tickers already in the portfolio (to check for duplicates)

    Returns:
        Dictionary with keys: ticker, shares, purchase_price, current_price
    """
    while True:
        ticker = input("\nEnter stock ticker: ").strip().upper()

        # Validate ticker format
        if not ticker:
            print("Error: Ticker cannot be empty.")
            continue
        if len(ticker) > 5:
            print("Error: Ticker should be 5 characters or less.")
            continue
        if not ticker.isalpha():
            print("Error: Ticker should contain only letters.")
            continue
        if ticker in existing_tickers:
            print(f"Error: {ticker} is already in your portfolio.")
            continue

        break

    # Get number of shares
    while True:
        try:
            shares = float(input("Enter number of shares: "))
            if shares <= 0:
                print("Error: Shares must be a positive number.")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number.")

    # Get purchase price
    while True:
        try:
            purchase_price = float(input("Enter purchase price per share: $"))
            if purchase_price <= 0:
                print("Error: Purchase price must be a positive number.")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number.")

    # Get current price
    while True:
        try:
            current_price = float(input("Enter current price per share: $"))
            if current_price <= 0:
                print("Error: Current price must be a positive number.")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number.")

    return {
        "ticker": ticker,
        "shares": shares,
        "purchase_price": purchase_price,
        "current_price": current_price
    }


def collect_portfolio():
    """
    Main input loop to collect stock data from user.

    Returns:
        List of stock dictionaries
    """
    stocks = []
    existing_tickers = []

    print("\n" + "="*60)
    print("PORTFOLIO STOCK ENTRY")
    print("="*60)
    print("Enter your stocks one by one.")
    print("You will be prompted to add another after each entry.\n")

    while True:
        stock = get_stock_input(existing_tickers)
        stocks.append(stock)
        existing_tickers.append(stock["ticker"])

        print(f"\n[Added] {stock['ticker']}")

        # Ask if user wants to add another stock
        while True:
            add_another = input("Add another stock? (yes/no): ").strip().lower()
            if add_another in ["yes", "y"]:
                break
            elif add_another in ["no", "n"]:
                return stocks
            else:
                print("Error: Please enter 'yes' or 'no'.")


def calculate_cost_basis(shares, purchase_price):
    """Calculate total amount invested in a stock."""
    return shares * purchase_price


def calculate_current_value(shares, current_price):
    """Calculate current value of a stock holding."""
    return shares * current_price


def calculate_gain_loss(current_value, cost_basis):
    """Calculate absolute gain/loss in dollars."""
    return current_value - cost_basis


def calculate_return_percent(gain_loss, cost_basis):
    """Calculate return as a percentage."""
    if cost_basis == 0:
        return 0
    return (gain_loss / cost_basis) * 100


def calculate_total_invested(stocks):
    """Calculate total amount invested across all stocks."""
    total = 0
    for stock in stocks:
        cost_basis = calculate_cost_basis(stock["shares"], stock["purchase_price"])
        total += cost_basis
    return total


def calculate_total_current_value(stocks):
    """Calculate total current value of portfolio."""
    total = 0
    for stock in stocks:
        current_value = calculate_current_value(stock["shares"], stock["current_price"])
        total += current_value
    return total


def calculate_total_gain_loss(stocks):
    """Calculate total gain/loss across all stocks."""
    total_current = calculate_total_current_value(stocks)
    total_invested = calculate_total_invested(stocks)
    return total_current - total_invested


def calculate_total_return_percent(total_gain_loss, total_invested):
    """Calculate overall portfolio return percentage."""
    if total_invested == 0:
        return 0
    return (total_gain_loss / total_invested) * 100


def calculate_allocations(stocks):
    """
    Calculate each stock's percentage allocation in the portfolio.

    Returns:
        Dictionary with {ticker: percentage}
    """
    total_value = calculate_total_current_value(stocks)

    if total_value == 0:
        return {stock["ticker"]: 0 for stock in stocks}

    allocations = {}
    for stock in stocks:
        current_value = calculate_current_value(stock["shares"], stock["current_price"])
        allocation_percent = (current_value / total_value) * 100
        allocations[stock["ticker"]] = allocation_percent

    return allocations


def find_best_performer(stocks):
    """
    Find the stock with the highest return percentage.

    Returns:
        Tuple of (ticker, return_percent)
    """
    best_ticker = None
    best_return = float("-inf")

    for stock in stocks:
        cost_basis = calculate_cost_basis(stock["shares"], stock["purchase_price"])
        current_value = calculate_current_value(stock["shares"], stock["current_price"])
        gain_loss = calculate_gain_loss(current_value, cost_basis)
        return_percent = calculate_return_percent(gain_loss, cost_basis)

        if return_percent > best_return:
            best_return = return_percent
            best_ticker = stock["ticker"]

    return (best_ticker, best_return)


def find_worst_performer(stocks):
    """
    Find the stock with the lowest return percentage.

    Returns:
        Tuple of (ticker, return_percent)
    """
    worst_ticker = None
    worst_return = float("inf")

    for stock in stocks:
        cost_basis = calculate_cost_basis(stock["shares"], stock["purchase_price"])
        current_value = calculate_current_value(stock["shares"], stock["current_price"])
        gain_loss = calculate_gain_loss(current_value, cost_basis)
        return_percent = calculate_return_percent(gain_loss, cost_basis)

        if return_percent < worst_return:
            worst_return = return_percent
            worst_ticker = stock["ticker"]

    return (worst_ticker, worst_return)


def calculate_risk_score(allocations):
    """
    Calculate concentration risk score (0-100).

    Formula: max(allocation_percentages) * 100
    - 100% in one stock = risk 100 (most concentrated)
    - 50/50 split = risk 50
    - Evenly distributed = lower risk

    Returns:
        Risk score as a float (0-100)
    """
    if not allocations:
        return 0

    max_allocation = max(allocations.values())
    return max_allocation


def print_portfolio_table(stocks):
    """
    Print a formatted ASCII table showing all stocks in the portfolio.

    Columns: Ticker, Shares, Purchase Price, Current Price, Cost Basis,
             Current Value, Gain/Loss, Return %, % of Portfolio
    """
    allocations = calculate_allocations(stocks)

    # Print header
    header = f"{'TICKER':<8} {'SHARES':<10} {'PURCHASE':<12} {'CURRENT':<12} {'COST BASIS':<15} {'CURRENT VALUE':<15} {'GAIN/LOSS':<15} {'RETURN %':<10} {'% OF PORT':<10}"
    print("\n" + header)
    print("-" * 130)

    # Print each stock
    for stock in stocks:
        ticker = stock["ticker"]
        shares = f"{stock['shares']:,.2f}"
        purchase_price = format_currency(stock["purchase_price"])
        current_price = format_currency(stock["current_price"])

        cost_basis = calculate_cost_basis(stock["shares"], stock["purchase_price"])
        current_value = calculate_current_value(stock["shares"], stock["current_price"])
        gain_loss = calculate_gain_loss(current_value, cost_basis)
        return_percent = calculate_return_percent(gain_loss, cost_basis)
        allocation_percent = allocations[ticker]

        row = f"{ticker:<8} {shares:<10} {purchase_price:<12} {current_price:<12} {format_currency(cost_basis):<15} {format_currency(current_value):<15} {format_currency(gain_loss):<15} {format_percentage(return_percent):<10} {format_percentage(allocation_percent):<10}"
        print(row)

    print("-" * 130)


def print_summary_metrics(stocks):
    """
    Print portfolio summary metrics below the table.

    Metrics: Total Invested, Total Current Value, Total Gain/Loss,
             Overall Return %, Best Performer, Worst Performer, Risk Score
    """
    total_invested = calculate_total_invested(stocks)
    total_current = calculate_total_current_value(stocks)
    total_gain_loss = calculate_total_gain_loss(stocks)
    total_return = calculate_total_return_percent(total_gain_loss, total_invested)
    allocations = calculate_allocations(stocks)
    risk_score = calculate_risk_score(allocations)
    best_ticker, best_return = find_best_performer(stocks)
    worst_ticker, worst_return = find_worst_performer(stocks)

    print("\n" + "="*60)
    print("PORTFOLIO SUMMARY METRICS")
    print("="*60)
    print(f"Total Invested:         {format_currency(total_invested)}")
    print(f"Total Current Value:    {format_currency(total_current)}")
    print(f"Total Gain/Loss:        {format_currency(total_gain_loss)}")
    print(f"Overall Return:         {format_percentage(total_return)}")
    print()
    print(f"Best Performer:         {best_ticker} ({format_percentage(best_return)})")
    print(f"Worst Performer:        {worst_ticker} ({format_percentage(worst_return)})")
    print()
    print(f"Risk Score:             {format_percentage(risk_score, decimals=1)}/100")
    print(f"  (Concentration: largest position is {format_percentage(max(allocations.values()))} of portfolio)")
    print("="*60)


def save_portfolio(stocks):
    """
    Save portfolio to a text file (optional feature).
    """
    save_choice = input("\nWould you like to save your portfolio? (yes/no): ").strip().lower()

    if save_choice not in ["yes", "y"]:
        return

    filename = input("Enter filename (without extension): ").strip()
    if not filename:
        filename = "portfolio"

    filename = f"{filename}.txt"

    try:
        with open(filename, "w") as f:
            f.write("PORTFOLIO DATA\n")
            f.write("="*60 + "\n\n")

            for stock in stocks:
                f.write(f"Ticker: {stock['ticker']}\n")
                f.write(f"Shares: {stock['shares']}\n")
                f.write(f"Purchase Price: {format_currency(stock['purchase_price'])}\n")
                f.write(f"Current Price: {format_currency(stock['current_price'])}\n\n")

        print(f"[Saved] Portfolio saved to {filename}")
    except Exception as e:
        print(f"Error saving file: {e}")


def main():
    """
    Main function that orchestrates the entire application flow.
    """
    print("\n" + "="*60)
    print("PORTFOLIO ANALYSIS TOOL")
    print("="*60)
    print("Analyze your stock portfolio holdings\n")

    # Collect stocks from user
    stocks = collect_portfolio()

    if not stocks:
        print("\nNo stocks entered. Exiting.")
        return

    # Run calculations and display results
    print("\n" + "="*60)
    print("PORTFOLIO ANALYSIS")
    print("="*60)

    print_portfolio_table(stocks)
    print_summary_metrics(stocks)

    # Optional: save portfolio
    save_portfolio(stocks)

    print("\nThank you for using Portfolio Analysis Tool!")


if __name__ == "__main__":
    main()
