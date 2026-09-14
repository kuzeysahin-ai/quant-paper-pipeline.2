# Reproduce stage: paper #1

## Blocker resolved: industry classification

read_notes.md flagged that the industry-adjusted reversal signal needs a
per-stock industry grouping, and Alpaca doesn't provide one (confirmed by
inspecting its asset metadata directly -- fields are trading attributes
like `marginable`/`shortable`, no sector/industry field at all).

**Resolution**: `industry_classification.py` pulls SIC codes for free
from SEC EDGAR (`company_tickers.json` for ticker->CIK, then each
company's `submissions` endpoint for its SIC code) and maps them to the
**Fama-French 12-industry** scheme using Ken French's official SIC-range
definitions. This is not the paper's exact industry taxonomy (they don't
specify one, likely GICS or a country-specific scheme per Compustat/CRSP
conventions) -- FF12 is a standard, well-established, citable choice
instead of an invented one, appropriate for the US-only subset we can
actually test.

Spot-checked against real tickers (2026-09-14):

| Ticker | SIC | FF12 | Correct? |
|---|---|---|---|
| AAPL | 3571 | BusEq | yes (computer hardware) |
| MSFT | 7372 | BusEq | yes (prepackaged software) |
| JPM | 6021 | Money | yes (national commercial bank) |
| XOM | 2911 | Enrgy | yes (petroleum refining) |
| KO | 2080 | NoDur | yes (beverages) |
| JNJ | 2834 | Hlth | yes (pharmaceutical preparations) |
| T | 4813 | Telcm | yes (telephone communications) |
| DUK | 4931 | Utils | yes (electric services) |

Run the (network-free) unit tests for the SIC->FF12 mapping logic:
```bash
cd papers/paper-01-ssrn-6630998/reproduce
../../../.venv/Scripts/python.exe -m pytest -v
```

SEC lookups are cached to `cache/` (gitignored, regenerable -- ~800KB
ticker->CIK file plus a growing per-CIK SIC cache). Be polite to SEC's
servers: `industry_classification.py` rate-limits itself to ~6-7
req/sec, under their ~10/sec guidance, and every request carries a
descriptive `User-Agent` with contact info as SEC's usage policy asks.

## Not built yet

- The actual industry-adjusted reversal signal computation
  (`R_i,t-1 - mean(R_j,t-1)` within each FF12 group) and the monthly
  quintile portfolio construction -- straightforward once real monthly
  return data is on hand, not yet wired up.
- Real monthly returns from Alpaca for whatever US universe we settle on.
  Alpaca's free tier gives daily bars; monthly returns need aggregating
  from those (or fetching TimeFrame.Month bars directly if the API
  supports it -- worth checking before hand-rolling aggregation).
- Value-weighting requires market cap per stock per month. Alpaca doesn't
  provide shares outstanding either -- another small data gap to solve,
  smaller than the industry-classification one since SEC's `companyfacts`
  endpoint (same API family used here) typically has this too, not yet
  investigated.
