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

**20/20 tests passing** (`cd` into this folder and run
`../../../.venv/Scripts/python.exe -m pytest -v`) -- 2 more than
originally, added when a real bug was caught: see "Real data connected"
below.

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

## Real data connected (2026-09-14, later same day)

`scripts/build_paper01_data.py` builds `data_dir/returns.csv` and
`data_dir/market_cap.csv` for real: Alpaca IEX daily bars (S&P 500
universe, `Adjustment.ALL`) aggregated to monthly, market cap from SEC's
`companyconcept` endpoint (point-in-time shares outstanding × price).
Full data-source reasoning, including the survivorship-bias statement,
is in that script's module docstring.

**Universe**: today's S&P 500 (Wikipedia, includes CIK directly)
intersected with Alpaca's tradable-active list -- **survivorship-biased**,
applied retroactively; no free point-in-time membership source found.
Stated in `ReproduceResult.assumptions` on every real run, not just here.

**Two real bugs found and fixed while wiring this up** (full detail in
`STATUS.md`'s "Real data connected" entry):
1. Alpaca's free-tier IEX daily bars do NOT go back to 2016 as CLAUDE.md
   originally assumed -- real floor is ~2020-07-27 (a ~6-year rolling
   window from today, empirically confirmed). Corrected in CLAUDE.md and
   the data-build script's default `--start`.
2. `monthly_long_short_returns` was silently converting "no data this
   month" (both legs empty) into a fake `0.0` return instead of `NaN` --
   inflated the observation count and dragged statistics toward zero.
   Fixed; 2 regression tests added (`test_monthly_long_short_returns_missing_month_is_nan_not_zero`,
   `..._one_empty_leg_still_counts_other_leg`).

**Real run** (`python -m pipeline.run papers/paper-01-ssrn-6630998`,
503 tickers, 73 monthly observations, 2020-09 to 2026-09):

| Metric | Our result | Paper's published US figure |
|---|---|---|
| Mean monthly return | 0.517% | 0.340% (t=2.12) |
| t-statistic | **0.65** | 2.12 |
| Annualized Sharpe | ~0.27 | 0.32 |

The point estimate lands close to the paper's, but our t-stat (0.65) is
far below significance -- we cannot reject the null of no effect, even
though the paper's own result could. Not a clean replication success;
consistent with CLAUDE.md's expectation that most papers won't replicate
at their published effect size. Full honest writeup, including the
right-skewed return distribution (median negative, mean positive, driven
by a few extreme months that were checked and are NOT a thin-coverage
artifact): `STATUS.md`.

### Still open

- `verify_stage`'s tolerance check compares only the mean, no
  significance test -- a real design gap, not yet fixed.
- 63/503 tickers lack SEC shares-outstanding data (dual-class tickers,
  and a handful of SEC API anomalies like ABT's empty-dict response) --
  excluded from value-weighting where missing, not a crash.
- The extreme-month skew (Feb 2021, Jul 2026) hasn't been investigated
  beyond ruling out thin coverage.
- Universe survivorship bias remains unresolved.
- Read stage's Claude-API automation is still unvalidated against a real
  call -- this run used a manually-seeded `read_extraction_auto.json`.
