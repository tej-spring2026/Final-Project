import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# Risk-free rate: 3-Month US Treasury Bill yield (short-dated options).
# Update this when rates change materially.  Source: US Treasury (April 2026).
RISK_FREE_RATE = 0.048

# Flask-Caching TTLs (seconds)
CACHE_TTL_CHAIN = 300   # options chain: 5 minutes
CACHE_TTL_QUOTE = 60    # spot quote: 60 seconds

# ── Data provider ─────────────────────────────────────────────────────────────
# "tradier" (default) uses Tradier sandbox with ORATS Greeks.
# "yfinance" falls back to the legacy yfinance provider (no token required).
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "tradier").lower().strip()

TRADIER_SANDBOX_TOKEN    = os.getenv("TRADIER_SANDBOX_TOKEN", "")
TRADIER_SANDBOX_BASE_URL = os.getenv(
    "TRADIER_SANDBOX_BASE_URL", "https://sandbox.tradier.com/v1"
)

if DATA_PROVIDER == "tradier" and not TRADIER_SANDBOX_TOKEN:
    raise RuntimeError(
        "TRADIER_SANDBOX_TOKEN is not set. "
        "Add it to .env, or set DATA_PROVIDER=yfinance to use the legacy provider."
    )
