"""
Builds papers/paper-01-ssrn-6630998/data/{returns.csv,market_cap.csv} --
the exact contract documented in that paper's reproduce/stage_impl.py
docstring: wide format, index=month-end date, one column per ticker,
returns.csv holding simple monthly returns and market_cap.csv holding
market cap in USD as of each formation month.

## Universe -- and why it's survivorship-biased, stated plainly

Universe = TODAY's S&P 500 constituents (Wikipedia's "List of S&P 500
companies" table, which conveniently includes each company's CIK),
intersected with Alpaca's currently ACTIVE, tradable US equity assets.

**This is a survivorship-biased universe.** No free source of
point-in-time historical S&P 500 membership, or of price history for
stocks that were later delisted, was found or built. Concretely: a stock
that was in the S&P 500 (or listed on a US exchange) at some point during
the window this script covers but has since been delisted, acquired,
gone bankrupt, or dropped from the index is NOT in this dataset at all.
This biases both
Reproduce's and Sample's results upward relative to a true point-in-time
backtest, because failing/delisted companies (which would disproportionately
show up as "losers" in a reversal strategy) are systematically excluded.
This is the same category of limitation flagged for paper #2's universe
question (papers/paper-02-groot-huij-zhou-2012/reproduce/README.md) --
recorded here explicitly rather than silently absorbed into the numbers,
per CLAUDE.md's rigor principle. This exact sentence is also written into
ReproduceResult.assumptions by stage_impl.py's caller (this script writes
data; assumptions about signal/portfolio construction live in stage_impl.py
already -- see BUILD_ASSUMPTIONS below for the ones this script adds).

## Other data-source choices, stated plainly

- **Prices**: Alpaca IEX daily bars, `Adjustment.ALL` (split- and
  dividend-adjusted) -- a genuine total-return proxy, not a bare price
  return.
- **Market cap**: shares outstanding from SEC's `companyconcept` endpoint
  (`dei:EntityCommonStockSharesOutstanding`, the cover-page share count
  every 10-K/10-Q must report), selected POINT-IN-TIME per month (the
  most recent value whose `filed` date is on or before that month-end --
  using `filed`, not the report's `end`/cover date, specifically to avoid
  look-ahead bias: the market didn't know the number until it was filed).
  This is a standard share count, not adjusted for buybacks/issuance
  between filings -- market cap can be stale by up to one quarter.
  For the ~2 dual-class S&P 500 tickers that use a period in their symbol
  (BRK.B, BF.B), SEC's own ticker->CIK map uses a hyphen instead --
  since this script gets CIK straight from Wikipedia's table (not that
  map), pricing/returns are unaffected, but those two tickers will fail
  industry lookup in industry_classification.py and default to
  industry="Other" (a warning prints; not a crash, not silent).
- Sample and Reproduce use the SAME data (see stage_impl.py's docstring
  and pipeline/run.py -- both stages are handed the same data_dir).
  There is no older window to reserve for "Reproduce" separately from a
  "current" window for "Sample" -- the entire dataset already IS the
  current era, by construction of the data constraint itself.

## IMPORTANT CORRECTION to an earlier project assumption

CLAUDE.md originally stated Alpaca's free tier provides US equity/ETF
daily data "starting from 2016." **Empirically confirmed false** for the
IEX feed as actually queried (2026-09-14): `StockBarsRequest` with
`feed=DataFeed.IEX` returns **zero rows for AAPL before 2020-07-27** --
tested directly at 2016-06, 2018-06, 2019-06, and 2020-06 start dates,
all returned 0 bars; 2020-09 returned real data. The real floor is a
~6-year ROLLING window back from the current date, not a fixed calendar
year. This was caught by a real bug it caused: an initial run with
`--start 2016-01-01` silently produced 33 all-NaN "returns" rows (2017-12
through 2020-08), which `monthly_long_short_returns` originally turned
into fake 0.0% observations instead of excluding them (see that
function's fix and the test in `papers/paper-01-ssrn-6630998/reproduce/test_portfolio.py`
-- `test_monthly_long_short_returns_missing_month_is_nan_not_zero`).

**Default `--start` here is therefore `2020-08-01`**, comfortably after
the observed real floor, not 2016-01-01. If Alpaca's actual historical
depth changes in the future (this appears to be a rolling window, so the
floor itself moves forward over time), re-verify with the same direct
`StockBarsRequest` probe before trusting an older `--start` value again --
don't assume the original "2016" claim was ever correct for this feed.

Usage:
    .venv\\Scripts\\python.exe scripts\\build_paper01_data.py
    .venv\\Scripts\\python.exe scripts\\build_paper01_data.py --limit 25   # fast smoke test
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
PAPER_DIR = REPO_ROOT / "papers" / "paper-01-ssrn-6630998"
DATA_DIR = PAPER_DIR / "data"
CACHE_DIR = Path(__file__).parent / "cache_paper01_data"

USER_AGENT = "quant-paper-pipeline research kuzey8113@gmail.com"
SEC_REQUEST_DELAY_SECONDS = 0.15  # matches industry_classification.py's politeness pacing

BUILD_ASSUMPTIONS = [
    "Universe = today's S&P 500 constituents intersected with Alpaca's "
    "currently-active tradable list, applied across the whole backtest "
    "window -- SURVIVORSHIP BIASED. Delisted/removed stocks are absent "
    "entirely, which likely biases the reversal effect upward (failing "
    "companies, disproportionately 'losers,' are systematically excluded).",
    "Prices are Alpaca IEX daily bars with Adjustment.ALL (split + "
    "dividend adjusted) -- a total-return proxy, aggregated to monthly "
    "via last-trading-day-of-month close. Alpaca IEX's actual historical "
    "depth is ~6 years rolling back from today, NOT a fixed 2016 start "
    "as originally assumed in CLAUDE.md -- empirically confirmed "
    "2026-09-14 (see this module's docstring); --start defaults "
    "accordingly to just after the observed floor.",
    "Market cap = point-in-time shares outstanding (SEC companyconcept, "
    "dei:EntityCommonStockSharesOutstanding, most recent value FILED on "
    "or before the formation month -- not the report's cover/end date, "
    "to avoid look-ahead) times that month's close price. Share count "
    "can be up to one quarter stale relative to actual buybacks/issuance.",
    "Reproduce and Sample use the identical dataset -- there is no older "
    "window to reserve for Reproduce separately from a 'current' window "
    "for Sample; the whole available window already is the current era.",
]


# ---------------------------------------------------------------------
# Pure functions -- unit tested in test_build_paper01_data.py, no network.
# ---------------------------------------------------------------------


def monthly_close_and_returns(daily_close: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    daily_close: wide DataFrame, index=daily dates (irregular/gappy OK,
    e.g. weekends/holidays missing), columns=tickers, values=adjusted
    close price.

    Returns (monthly_close, monthly_returns): both wide, index=month-end
    dates (the last trading day Alpaca actually returned data for in
    each calendar month, not necessarily the calendar month-end).
    monthly_returns is monthly_close.pct_change() -- the first row is
    always NaN (no prior month to compare against); left in rather than
    dropped, since the portfolio code already treats NaN as "missing,"
    consistent with how it handles any other gap.
    """
    monthly_close = daily_close.resample("ME").last()
    monthly_returns = monthly_close.pct_change()
    return monthly_close, monthly_returns


def select_point_in_time_value(
    entries: list[dict], as_of: pd.Timestamp, date_key: str = "filed", value_key: str = "val"
) -> float | None:
    """
    From a list of {date_key: 'YYYY-MM-DD', value_key: number, ...}
    entries (the shape SEC's companyconcept API returns), pick the value
    whose date_key is the latest date <= as_of. None if nothing was filed
    by that date yet (e.g. as_of predates the company's earliest filing).

    Using `filed` (not `end`, the report's cover-page date) is the
    look-ahead-avoiding choice: the market didn't know the share count
    until the filing was actually public.
    """
    candidates = [e for e in entries if pd.Timestamp(e[date_key]) <= as_of]
    if not candidates:
        return None
    best = max(candidates, key=lambda e: e[date_key])
    return float(best[value_key])


def build_market_cap_panel(
    monthly_close: pd.DataFrame, shares_by_ticker: dict[str, list[dict]]
) -> pd.DataFrame:
    """
    monthly_close: wide DataFrame, index=month-end dates, columns=tickers,
    values=close price (SAME index as monthly_close_and_returns' output --
    market_cap.csv must share returns.csv's exact date index, since
    stage_impl.py does direct .loc[date] lookups across both).
    shares_by_ticker: ticker -> list of SEC companyconcept entries (see
    select_point_in_time_value for the shape).

    Returns a same-shaped DataFrame: market_cap = shares(as of that
    month, point-in-time) * price. NaN wherever either the price or a
    point-in-time share count is unavailable -- left as NaN, not
    silently zero-filled, so downstream code (which already treats NaN
    as "exclude from ranking") handles it correctly.
    """
    out = pd.DataFrame(index=monthly_close.index, columns=monthly_close.columns, dtype=float)
    for ticker in monthly_close.columns:
        entries = shares_by_ticker.get(ticker, [])
        if not entries:
            continue
        for date in monthly_close.index:
            price = monthly_close.loc[date, ticker]
            if pd.isna(price):
                continue
            shares = select_point_in_time_value(entries, date)
            if shares is not None:
                out.loc[date, ticker] = shares * price
    return out


# ---------------------------------------------------------------------
# Network-touching functions -- not unit tested (matches project
# convention: e.g. industry_classification.py's live fetches are
# spot-checked manually, not mocked in the automated test suite).
# ---------------------------------------------------------------------


def fetch_sp500_universe() -> pd.DataFrame:
    """S&P 500 constituents from Wikipedia -- includes a CIK column
    directly, so no separate ticker->CIK resolution is needed for this
    script's purposes (industry_classification.py still does its own
    SEC-based lookup for industry labels, independently)."""
    resp = requests.get(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0][["Symbol", "CIK"]].copy()
    df.columns = ["symbol", "cik"]
    df["cik"] = df["cik"].astype(int)
    return df


def filter_to_alpaca_tradable(symbols: list[str]) -> set[str]:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import AssetClass, AssetStatus
    from alpaca.trading.requests import GetAssetsRequest

    client = TradingClient(
        os.environ["ALPACA_API_KEY_ID"], os.environ["ALPACA_API_SECRET_KEY"], paper=True
    )
    req = GetAssetsRequest(asset_class=AssetClass.US_EQUITY, status=AssetStatus.ACTIVE)
    assets = client.get_all_assets(req)
    tradable = {a.symbol for a in assets if a.tradable}
    return set(symbols) & tradable


def fetch_daily_close_prices(
    symbols: list[str], start: pd.Timestamp, end: pd.Timestamp, chunk_size: int = 150
) -> pd.DataFrame:
    from alpaca.data.enums import Adjustment, DataFeed
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(
        os.environ["ALPACA_API_KEY_ID"], os.environ["ALPACA_API_SECRET_KEY"]
    )
    close_series = []
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i : i + chunk_size]
        print(f"    fetching bars for {len(chunk)} symbols ({i + 1}-{i + len(chunk)} of {len(symbols)})...")
        req = StockBarsRequest(
            symbol_or_symbols=chunk,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed=DataFeed.IEX,
            adjustment=Adjustment.ALL,
        )
        bars = client.get_stock_bars(req)
        df = bars.df
        if df is not None and len(df):
            close_series.append(df["close"])
        time.sleep(0.5)

    close_long = pd.concat(close_series)
    wide = close_long.unstack(level="symbol")
    # Bar timestamps carry a UTC time-of-day component; normalize to
    # tz-naive calendar dates so resample("ME") groups by calendar month
    # cleanly regardless of the exact intraday timestamp Alpaca stamped.
    idx = wide.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert(None)
    wide.index = idx.normalize()
    return wide.sort_index()


def fetch_shares_outstanding(cik: int, cache: dict, max_retries: int = 3) -> list[dict]:
    """
    `cache[key]` is only ever set to a genuine, confirmed result: a
    non-empty entries list, or `[]` after SEC affirmatively returned 404
    (concept doesn't exist for this filer -- a real, permanent answer).
    Any other failure (timeout, connection error, malformed/incomplete
    response, non-404 non-200 status) is retried up to `max_retries`
    times and, if still failing, left OUT of the cache entirely so a
    later run retries it instead of permanently freezing in a false
    negative. This exists because exactly that happened once during
    development: a transient failure on one ticker got cached as `{}`
    and would have silently stayed "missing" on every future run without
    this fix -- see STATUS.md.
    """
    key = str(cik)
    if key in cache:
        return cache[key]

    cik_padded = f"{cik:010d}"
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik_padded}/dei/EntityCommonStockSharesOutstanding.json"

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        except requests.RequestException:
            time.sleep(SEC_REQUEST_DELAY_SECONDS * (attempt + 1))
            continue
        finally:
            time.sleep(SEC_REQUEST_DELAY_SECONDS)

        if resp.status_code == 404:
            cache[key] = []  # confirmed: this filer has no such concept
            return []
        if resp.status_code != 200:
            continue  # transient (429/5xx/etc) -- retry

        try:
            data = resp.json()
            entries = data["units"]["shares"]
        except (ValueError, KeyError):
            continue  # malformed/incomplete response -- retry

        if entries:  # only cache a genuinely non-empty, well-formed result
            cache[key] = entries
            return entries
        # entries == [] with a 200 and well-formed body is itself odd for
        # a real filer; treat it the same as a transient failure and retry
        # rather than trust it on the first try.

    return []  # exhausted retries this run; NOT written to cache -- retry next run


# ---------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=None, help="Use only the first N universe tickers (fast smoke test)"
    )
    parser.add_argument(
        "--start",
        default="2020-08-01",
        help="Start date for daily bars. Default is just after Alpaca IEX's "
        "empirically-observed floor (~2020-07-27 as of 2026-09-14, see "
        "module docstring) -- NOT 2016, despite an earlier project "
        "assumption that turned out to be wrong for this feed.",
    )
    args = parser.parse_args()

    if not os.environ.get("ALPACA_API_KEY_ID") or not os.environ.get("ALPACA_API_SECRET_KEY"):
        print("Missing ALPACA_API_KEY_ID/ALPACA_API_SECRET_KEY in .env", file=sys.stderr)
        sys.exit(1)

    print("Fetching S&P 500 universe from Wikipedia (includes CIK column)...")
    universe = fetch_sp500_universe()
    print(f"  {len(universe)} S&P 500 rows")

    print("Filtering to Alpaca-tradable, active US equities...")
    tradable = filter_to_alpaca_tradable(universe["symbol"].tolist())
    dropped = sorted(set(universe["symbol"]) - tradable)
    universe = universe[universe["symbol"].isin(tradable)].reset_index(drop=True)
    print(f"  {len(universe)} tradable on Alpaca ({len(dropped)} dropped: {dropped[:10]}{'...' if len(dropped) > 10 else ''})")

    if args.limit:
        universe = universe.head(args.limit).reset_index(drop=True)
        print(f"  --limit applied: using first {len(universe)} tickers")

    symbols = universe["symbol"].tolist()
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp.now(tz="UTC")

    print(f"Fetching daily bars from Alpaca ({start.date()} to {end.date()}, adjustment=ALL)...")
    daily_close = fetch_daily_close_prices(symbols, start, end)
    print(f"  {daily_close.shape[0]} trading days x {daily_close.shape[1]} tickers with data")

    print("Aggregating to monthly (last trading day of each month)...")
    monthly_close, monthly_returns = monthly_close_and_returns(daily_close)
    print(f"  {monthly_returns.shape[0]} months")

    print("Fetching point-in-time shares outstanding from SEC (companyconcept)...")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / "shares_outstanding.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    shares_by_ticker: dict[str, list[dict]] = {}
    missing = []
    for i, row in universe.iterrows():
        entries = fetch_shares_outstanding(int(row["cik"]), cache)
        shares_by_ticker[row["symbol"]] = entries
        if not entries:
            missing.append(row["symbol"])
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(universe)} tickers checked...")

    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    print(
        f"  {len(universe) - len(missing)}/{len(universe)} tickers have SEC "
        f"shares-outstanding data ({len(missing)} missing: "
        f"{missing[:10]}{'...' if len(missing) > 10 else ''})"
    )

    print("Building market cap panel...")
    market_cap = build_market_cap_panel(monthly_close, shares_by_ticker)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    monthly_returns.to_csv(DATA_DIR / "returns.csv")
    market_cap.to_csv(DATA_DIR / "market_cap.csv")
    print(f"Wrote {DATA_DIR / 'returns.csv'} {monthly_returns.shape}")
    print(f"Wrote {DATA_DIR / 'market_cap.csv'} {market_cap.shape}")
    print("\nBuild assumptions (also recorded in stage_impl.py's ReproduceResult.assumptions):")
    for a in BUILD_ASSUMPTIONS:
        print(f"  - {a}")


if __name__ == "__main__":
    main()
