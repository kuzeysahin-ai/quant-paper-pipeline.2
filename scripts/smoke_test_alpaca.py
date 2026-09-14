"""
One-off connectivity check — NOT part of the pipeline.

Confirms the local environment can authenticate against Alpaca before any
real Read/Reproduce/Verify/Sample work starts. Run once after setting up
.env, then forget about it; the actual pipeline modules are separate.

Usage:
    .venv\\Scripts\\python.exe scripts\\smoke_test_alpaca.py
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

key_id = os.environ.get("ALPACA_API_KEY_ID")
secret_key = os.environ.get("ALPACA_API_SECRET_KEY")
base_url = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

if not key_id or key_id == "your-key-id" or not secret_key or secret_key == "your-secret-key":
    print(
        "Missing or placeholder Alpaca credentials.\n"
        "Copy .env.example to .env and fill in ALPACA_API_KEY_ID / "
        "ALPACA_API_SECRET_KEY from the Alpaca dashboard "
        "(Paper Trading -> API Keys).",
        file=sys.stderr,
    )
    sys.exit(1)

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

is_paper = "paper" in base_url

# --- Trading account check ---
trading_client = TradingClient(key_id, secret_key, paper=is_paper)
account = trading_client.get_account()
print("Trading API OK")
print(f"  account status : {account.status}")
print(f"  paper account  : {is_paper}")
print(f"  buying power   : {account.buying_power}")

# --- Market data check: a few days of SPY daily bars ---
data_client = StockHistoricalDataClient(key_id, secret_key)
request = StockBarsRequest(
    symbol_or_symbols=["SPY"],
    timeframe=TimeFrame.Day,
    limit=5,
)
bars = data_client.get_stock_bars(request)
spy_bars = bars["SPY"]
print(f"\nMarket Data API OK — last {len(spy_bars)} SPY daily bars:")
for bar in spy_bars:
    print(f"  {bar.timestamp.date()}  close={bar.close}")

print("\nAll checks passed. Alpaca connectivity confirmed.")
