"""
Flask entry point — routes only, no business logic.
Business logic lives in pricing/, data/, and ai/.
"""
from datetime import date

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_caching import Cache

import config
from pricing.black_scholes import greeks as bs_greeks
from pricing.implied_vol import implied_vol
from pricing.payoff import build_payoff
from pricing.strategies import Leg, Strategy

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

cache = Cache(app, config={"CACHE_TYPE": "SimpleCache"})

if config.DATA_PROVIDER == "tradier":
    from data.tradier_provider import TradierProvider
    provider = TradierProvider(
        config.TRADIER_SANDBOX_TOKEN,
        config.TRADIER_SANDBOX_BASE_URL,
    )
else:
    from data.yfinance_provider import YFinanceProvider
    provider = YFinanceProvider()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/builder")
def builder():
    ticker = request.args.get("ticker", "").upper().strip()
    if not ticker:
        return redirect(url_for("index"))
    try:
        quote = provider.get_quote(ticker)
        expirations = provider.get_expirations(ticker)
    except RuntimeError as exc:
        return render_template("index.html", error=str(exc))
    return render_template(
        "builder.html",
        ticker=ticker,
        price=round(quote.price, 2),
        expirations=expirations,
    )


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@cache.memoize(timeout=config.CACHE_TTL_QUOTE)
def _fetch_quote(ticker: str) -> dict:
    q = provider.get_quote(ticker)
    return {"ticker": q.ticker, "price": round(q.price, 2)}


@app.route("/api/quote")
def api_quote():
    ticker = request.args.get("ticker", "").upper().strip()
    if not ticker:
        return jsonify({"error": "ticker required"}), 400
    try:
        return jsonify(_fetch_quote(ticker))
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 422


@cache.memoize(timeout=config.CACHE_TTL_CHAIN)
def _fetch_chain(ticker: str, expiration: str) -> dict:
    quote = provider.get_quote(ticker)
    contracts = provider.get_chain(ticker, expiration)

    S = quote.price
    r = config.RISK_FREE_RATE
    T = max((date.fromisoformat(expiration) - date.today()).days / 365.0, 1e-4)

    rows = []
    for c in contracts:
        mid = c.mid
        iv_val = None
        greek_vals = {}

        if c.provided_iv is not None:
            # Provider supplied IV+Greeks directly (e.g. Tradier/ORATS) —
            # skip Newton-Raphson solver for this contract.
            iv_val = c.provided_iv
            greek_vals = {k: round(v, 4) for k, v in (c.provided_greeks or {}).items()}
        else:
            usable_mid = mid if mid >= 0.05 else None
            if usable_mid is not None:
                iv_val = implied_vol(usable_mid, S, c.strike, T, r, c.option_type)
                if iv_val is not None:
                    g = bs_greeks(S, c.strike, T, r, iv_val, c.option_type)
                    greek_vals = {k: round(v, 4) for k, v in g.items()}

        usable_mid = mid if mid >= 0.05 else None

        rows.append({
            "symbol": c.symbol,
            "option_type": c.option_type,
            "strike": c.strike,
            "expiration": c.expiration,
            "bid": c.bid,
            "ask": c.ask,
            "last": c.last,
            "mid": round(usable_mid, 2) if usable_mid is not None else None,
            "volume": c.volume,
            "open_interest": c.open_interest,
            "iv": round(iv_val * 100, 1) if iv_val is not None else None,
            **greek_vals,
        })

    return {"spot": round(S, 2), "contracts": rows}


@app.route("/api/chain")
def api_chain():
    ticker = request.args.get("ticker", "").upper().strip()
    expiration = request.args.get("expiration", "").strip()
    if not ticker or not expiration:
        return jsonify({"error": "ticker and expiration required"}), 400
    try:
        return jsonify(_fetch_chain(ticker, expiration))
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 422


@app.route("/api/payoff", methods=["POST"])
def api_payoff():
    data = request.get_json(force=True)
    legs_raw = data.get("legs", [])
    if not legs_raw:
        return jsonify({"error": "No legs provided"}), 400

    try:
        legs = [
            Leg(
                option_type=str(l["option_type"]).lower(),
                strike=float(l["strike"]),
                expiration=str(l["expiration"]),
                quantity=int(l["quantity"]),
                entry_price=float(l["entry_price"]),
            )
            for l in legs_raw
        ]
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": f"Invalid leg data: {exc}"}), 400

    strategy = Strategy(legs)
    result = build_payoff(strategy)

    # JSON does not support Infinity — use null (client renders as "Unlimited")
    def _clean_inf(v):
        if v is None or v != v:          # also catches float nan
            return None
        if abs(v) == float("inf"):
            return None
        return round(v, 2)

    result["max_profit"] = _clean_inf(result["max_profit"])
    result["max_loss"] = _clean_inf(result["max_loss"])
    result["net_debit_credit"] = round(result["net_debit_credit"], 2)
    result["breakevens"] = [round(b, 2) for b in result["breakevens"]]
    result["pnl"] = [round(v, 2) for v in result["pnl"]]

    S = float(data.get("spot", legs[0].strike))
    g = strategy.aggregate_greeks(S, config.RISK_FREE_RATE)
    result["greeks"] = {k: round(v, 4) for k, v in g.items()}

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=config.DEBUG)
