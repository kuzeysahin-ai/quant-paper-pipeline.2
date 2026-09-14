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

## Reproduce/Verify/Sample: implemented against the fixed pipeline interface

Built directly against `pipeline/interface.py` (2026-09-14) -- the first
paper to be a real implementation of that contract rather than bespoke
code (paper #2's `SmartReversalSimulator` predates it).

- `reversal_signal.py` -- `industry_adjusted_reversal_signal`: leave-one-out
  industry-peer-mean reversal signal, `REV_IN_{i,t} = R_{i,t} -
  mean(R_{j,t}, j != i, j in industry(i))`. 3 unit tests, hand-verified
  arithmetic (not just "it runs").
- `portfolio.py` -- `monthly_long_short_returns`: quintile sort, value-weighted
  long (bottom quintile) / short (top quintile), one-month formation-to-holding
  lag. 5 unit tests.
- `stage_impl.py` -- `reproduce_stage` / `verify_stage` / `sample_stage`
  matching `pipeline.interface`'s signatures exactly. 6 unit tests against
  synthetic CSVs (no live network calls).

**18/18 tests passing** (`cd` into this folder and run
`../../../.venv/Scripts/python.exe -m pytest -v`).

**Design decisions recorded in `ReproduceResult.assumptions`, not
silently baked in** (per CLAUDE.md's rigor principle):
- Leave-one-out industry mean (paper says "peers," doesn't specify
  whether that excludes the stock itself -- read the more conservative
  way).
- Fama-French 12 industry classification, static for the whole sample --
  not the paper's own unspecified taxonomy, and doesn't model a stock
  changing industry mid-sample.
- One-month formation-to-holding lag (signal from month t, portfolio
  held in month t+1), matching the paper's "prior-month return" framing.
- Value-weighted quintiles (5 groups) -- the paper's headline Table 1-3
  numbers, not the equal-weighted variant it also reports.

## Not built yet: real data for `reproduce_stage`/`sample_stage`

`stage_impl.py` expects `data_dir/returns.csv` and
`data_dir/market_cap.csv` (documented in its module docstring) -- neither
is produced by a real pipeline yet. All tests above use synthetic CSVs.
Still needed before this can run on real data:

- Real monthly returns from Alpaca for whatever US universe we settle
  on. Alpaca's free tier gives daily bars; monthly returns need
  aggregating from those (or fetching `TimeFrame.Month` bars directly if
  the API supports it -- worth checking before hand-rolling aggregation).
- Value-weighting requires market cap per stock per month. Alpaca doesn't
  provide shares outstanding either -- SEC's `companyfacts` endpoint
  (same API family as `industry_classification.py`) typically has this,
  not yet investigated.
- Which US universe, and the same survivorship-bias question flagged for
  paper #2 applies here too if we use today's tradable-on-Alpaca list
  applied retroactively.
