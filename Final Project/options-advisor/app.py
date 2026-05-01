"""
Flask entry point — routes only, no business logic.
Business logic lives in pricing/, data/, and ai/.
"""
from datetime import date, timedelta
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_caching import Cache

import config
from pricing.black_scholes import greeks as bs_greeks
from pricing.implied_vol import implied_vol
from pricing.payoff import build_payoff
from pricing.strategies import Leg, Strategy

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.permanent_session_lifetime = timedelta(hours=24)

cache = Cache(app, config={"CACHE_TYPE": "SimpleCache"})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "api_key" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

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

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        key = request.form.get("api_key", "").strip()
        from ai.advisor import validate_api_key
        if validate_api_key(key):
            session.permanent = True
            session["api_key"] = key
            return redirect(url_for("index"))
        error = "Invalid API key. Please try again."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@require_api_key
def index():
    return render_template("index.html")


@app.route("/builder")
@require_api_key
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
@require_api_key
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


def _filter_chain(
    contracts: list[dict],
    spot: float,
    min_strike: float | None,
    max_strike: float | None,
) -> tuple[list[dict], dict]:
    """
    Filter the full cached chain to the requested strike range.

    Custom mode  (min_strike + max_strike provided):
        Return all strikes in [min_strike, max_strike] regardless of increment.

    Default mode (no params):
        Pick a tier increment from spot, keep only grid-aligned strikes, then
        return the 20 grid strikes below spot and 20 above spot.

    Tier boundaries:
        spot > 600  → $10 increments
        spot >= 50  → $5 increments   (spot == 600 uses $5, spot == 50 uses $5)
        spot < 50   → $1 increments
    """
    # ── Custom range ────────────────────────────────────────────────────────
    if min_strike is not None and max_strike is not None:
        filtered = [c for c in contracts if min_strike <= c["strike"] <= max_strike]
        return filtered, {
            "mode": "custom",
            "label": f"Custom range: ${min_strike:g}–${max_strike:g}",
        }

    # ── Tier-based default ───────────────────────────────────────────────────
    # spot > $600 → $10 increments
    # spot $50–$600 (inclusive) → $5 increments
    # spot < $50 → $1 increments
    if spot > 600:
        increment = 10
    elif spot >= 50:
        increment = 5
    else:
        increment = 1

    def _on_grid(strike: float) -> bool:
        rem = strike % increment
        return rem < 0.01 or rem > increment - 0.01

    all_strikes = sorted({c["strike"] for c in contracts})
    grid = [s for s in all_strikes if _on_grid(s)]

    if grid:
        atm_idx = min(range(len(grid)), key=lambda i: abs(grid[i] - spot))
        selected = set(
            grid[max(0, atm_idx - 20) : atm_idx + 21]
        )
        filtered = [c for c in contracts if c["strike"] in selected]

        # Fallback: fewer than 5 grid strikes on either side → use ±20% of spot
        below = {c["strike"] for c in filtered if c["strike"] < spot}
        above = {c["strike"] for c in filtered if c["strike"] > spot}
        if len(below) < 5 or len(above) < 5:
            import sys
            print(
                f"[WARN] Tier filter sparse (below={len(below)}, above={len(above)}). "
                "Falling back to ±20% of spot.",
                file=sys.stderr,
            )
            lo, hi = spot * 0.80, spot * 1.20
            filtered = [c for c in contracts if lo <= c["strike"] <= hi]
            return filtered, {
                "mode": "fallback",
                "label": f"Showing strikes within ±20% of ${spot:.2f} (sparse chain)",
            }
    else:
        # No grid-aligned strikes at all — return everything
        filtered = contracts

    return filtered, {
        "mode": "default",
        "increment": increment,
        "label": f"Showing ±20 strikes at ${increment} increments near ${spot:.2f}",
    }


@app.route("/api/chain")
@require_api_key
def api_chain():
    ticker = request.args.get("ticker", "").upper().strip()
    expiration = request.args.get("expiration", "").strip()
    if not ticker or not expiration:
        return jsonify({"error": "ticker and expiration required"}), 400

    min_s = request.args.get("min_strike")
    max_s = request.args.get("max_strike")
    try:
        min_strike = float(min_s) if min_s else None
        max_strike = float(max_s) if max_s else None
    except ValueError:
        return jsonify({"error": "min_strike and max_strike must be numbers"}), 400

    if min_strike is not None and max_strike is not None and min_strike > max_strike:
        return jsonify(
            {"error": f"min_strike ({min_strike:g}) must be less than max_strike ({max_strike:g})"}
        ), 400

    try:
        full = _fetch_chain(ticker, expiration)
        filtered, filter_info = _filter_chain(
            full["contracts"], full["spot"], min_strike, max_strike
        )
        return jsonify({"spot": full["spot"], "contracts": filtered, "filter": filter_info})
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 422


@app.route("/api/payoff", methods=["POST"])
@require_api_key
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


@app.route("/advisor")
@require_api_key
def advisor():
    return render_template("advisor.html")


@app.route("/api/advise", methods=["POST"])
@require_api_key
def api_advise():
    data = request.get_json(force=True)
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "message required"}), 400

    from ai.advisor import get_advice
    result = get_advice(message)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=config.DEBUG)
