# STATUS

The single source of truth bridging Cowork (planning) and local Claude Code
(execution) — see CLAUDE.md for why this matters. Update this at the end of
any session that changes state. Read it first, before assuming what's done.

## Current phase

**Read stage done on both papers. Reproduce started on paper #2.**

- **Paper #1**: Stosik & Zaremba (2026), "Short-Term Reversal Persists
  Globally -- If Properly Measured," SSRN 6630998 / Economics Letters.
  SSRN/ScienceDirect both blocked automated fetch (Cloudflare/paywall,
  confirmed domain-wide, not paper-specific) -- **owner manually
  downloaded and supplied the PDF**, placed at
  `papers/paper-01-ssrn-6630998/source.pdf`. **Read complete**:
  `papers/paper-01-ssrn-6630998/read_notes.md`. Key facts: monthly,
  64-country panel 1990-2023 (DOES overlap Alpaca's 2016+ window, unlike
  paper #2); main signal is industry-adjusted reversal (raw prior-month
  return minus industry-peer mean); US result is significant but the
  *weakest* of the major markets (t=2.12, vs UK t=5.37, Japan t=4.63);
  regret-based signal (3rd variant tested) is subsumed by
  industry-adjusted reversal per their own spanning regression, so we
  don't need to build it separately.
  **Blocker RESOLVED (2026-09-14)**: Alpaca confirmed to have no
  sector/industry field on its asset metadata (checked directly). Built
  `papers/paper-01-ssrn-6630998/reproduce/industry_classification.py` --
  free SIC codes from SEC EDGAR (ticker->CIK via
  `company_tickers.json`, then per-company `submissions` endpoint),
  mapped to the Fama-French 12-industry scheme via Ken French's official
  SIC ranges. Spot-checked against 8 real tickers (AAPL, MSFT, JPM, XOM,
  KO, JNJ, T, DUK) -- all classified correctly. 4 unit tests on the
  mapping logic passing (network-free). Owner chose to prioritize this
  paper over paper #2 (see below) -- this is now the active line of work.
  **Not yet built**: the actual signal computation (industry-adjusted
  monthly return vs. FF12 peers), monthly return aggregation from
  Alpaca's daily bars, and market-cap data for value-weighting (shares
  outstanding -- likely also available via SEC's companyfacts endpoint,
  not yet checked). See `reproduce/README.md`.
- **Paper #2**: de Groot, Huij & Zhou (2012), "Another Look at Trading
  Costs and Short-Term Reversal Profits," JBF 36:371-382 -- the primary
  source behind Quantpedia's "Short Term Reversal Effect in Stocks" page.
  **Read complete**, full text from Erasmus University's open repository
  (SSRN mirror blocked). Write-up: `papers/paper-02-groot-huij-zhou-2012/read_notes.md`.
  **Important finding**: Quantpedia's methodology description does not
  match the actual paper (wrong formation-period rule, wrong position
  count -- 20/20 not 10/10 on the 100-stock universe) -- see that file's
  "Discrepancies" section before building anything off the Quantpedia
  page alone.
  **Structural limitation**: paper's sample ends Dec 2009, zero overlap
  with Alpaca's 2016+ coverage -- same-period Verify against the
  published numbers is not possible. Plan is Read -> Reproduce -> Sample
  (skip formal Verify), per the read_notes.
  **Reproduce in progress**: `papers/paper-02-groot-huij-zhou-2012/reproduce/strategy.py`
  implements the "smart" portfolio construction mechanism (percentile
  rank, entry into extreme quintile, hold-until-median-crossing exit,
  replacement). 7 unit tests on synthetic data, all passing --
  `reproduce/test_strategy.py`. **Not yet wired to real data.** Blocked
  on the same kind of open question as paper #1: which "100 largest US
  stocks" universe, over time, without survivorship bias -- no free
  point-in-time historical constituents source lined up yet. See
  `reproduce/README.md`'s "What's deliberately NOT here yet" section.

## Environment

- Local machine: Windows, Python 3.14.0, pip 25.2 confirmed working
  (2026-09-14).
- `.venv/` created; `alpaca-py==0.44.0` + `python-dotenv==1.2.3` installed,
  pinned in `requirements.txt`. (2026-09-14)
- `.env.example` in place; owner created real `.env` with Alpaca keys
  (2026-09-14) -- not committed, never read/pasted into chat by design.
- `scripts/smoke_test_alpaca.py` written and **passing** -- one-off
  connectivity check (Trading API + Market Data API), explicitly NOT part
  of the pipeline package. Confirmed working (2026-09-14): paper account
  active, $400,000 buying power (default paper balance), SPY daily bars
  fetched via IEX feed successfully.
  - Fix along the way: an unbounded query (no explicit `start`/`end`,
    default feed) came back with zero bars -- free tier needs an explicit
    date range and `feed=DataFeed.IEX`, an unanchored "recent" query
    isn't enough. Now hardcoded in the script.
- Alpaca account type confirmed: individual "Trading API" account (not
  Broker API, not data-only, not OAuth2 app platform) — gives one key
  pair covering both paper trading and market data, matching the
  single-integration plan in CLAUDE.md.
- Repo connected: https://github.com/kuzeysahin-ai/quant-paper-pipeline.2
  (was empty at connection time, 2026-09-14).
- Confirmed with owner: run #1 (the WebFetch-scraping attempt) has
  nothing worth porting in — this repo starts fully fresh, no legacy code
  to reconcile.

## Done

- CLAUDE.md written: mission, 4-stage pipeline, priority order, why the
  constraints matter, advantages/disadvantages, paper-selection criteria,
  stage-by-stage expectations. (2026-09-14)
- This file created. (2026-09-14)
- Python env + Alpaca client libraries installed. (2026-09-14)

## Pipeline automation (2026-09-14)

**Owner correctly flagged that "Read" had zero actual automation** -- every
paper read so far was Claude Code reading PDF text and writing notes
live in conversation, indistinguishable from "paste a paper into a chat
and ask for a summary." Built `pipeline/read_stage.py` in response: a
callable script that takes a paper folder and calls the Claude API
directly (`claude-opus-5`, structured JSON output via
`output_config.format`) to produce a first-pass extraction, with no live
conversation required. See `pipeline/README.md`.

- Script is written, installs clean, syntax-checked, and its
  missing-API-key error path is confirmed correct.
- **Not yet run against a real API call** -- needs the owner's
  `ANTHROPIC_API_KEY` in `.env` (separate credential from any Claude
  Code session; this script calls the API standalone).
- **Next validation step**: run it on paper #2 and diff the automated
  `read_extraction_auto.json`/`read_stage_auto.md` against the
  manually-written `papers/paper-02-groot-huij-zhou-2012/read_notes.md`
  to check whether the automated first pass is trustworthy before
  relying on it for a new (3rd) paper.
- Human review of the output is still expected -- this is a first-pass
  draft generator, not an unsupervised Read stage.
- `pipeline/` is now the location for genuinely paper-agnostic code
  (Read-stage extraction applies identically to any paper from day one).
  This is distinct from `papers/paper-0N-*/reproduce/` strategy code,
  which stays paper-specific per CLAUDE.md until 3+ papers exist and
  common patterns actually emerge.

## Fixed pipeline interface (2026-09-14)

Per the owner's direction (relayed from the Cowork planning session):
before writing paper #1's actual Reproduce logic, locked in the
four-stage contract as real code -- `pipeline/interface.py`:

- `read_stage(paper_dir) -> ReadExtraction` -- **real**, delegates to
  `pipeline/read_stage.py`.
- `reproduce_stage(extraction, data_dir) -> ReproduceResult` -- **stub**,
  raises `NotImplementedError`.
- `verify_stage(reproduce_result, extraction) -> VerifyResult` -- **stub**.
- `sample_stage(reproduce_result, data_dir) -> SampleResult` -- **stub**.

`pipeline/test_interface.py` (4 tests, all passing) confirms the stubs
import cleanly and fail loudly rather than silently faking a result.
This is the actual start of "automation" in the structural sense: going
forward, a new paper means filling in this fixed interface, not
re-explaining the pipeline shape from scratch each time.

**Done**: paper #1's `reproduce_stage`/`verify_stage`/`sample_stage` are
now real implementations against this interface --
`papers/paper-01-ssrn-6630998/reproduce/stage_impl.py`, built on two new
modules: `reversal_signal.py` (the industry-adjusted reversal signal,
leave-one-out peer mean) and `portfolio.py` (quintile value-weighted
long-short construction). 18/18 tests passing (synthetic data, no live
network calls -- see that folder's README.md for the design decisions
recorded in `ReproduceResult.assumptions`).

**Still blocked on real data**: `reproduce_stage`/`sample_stage` expect
`data_dir/returns.csv` + `data_dir/market_cap.csv` (documented in
`stage_impl.py`'s docstring) -- nothing produces these from Alpaca/SEC
yet. Same open questions as before: monthly-return aggregation from
Alpaca daily bars, a market-cap source (likely SEC `companyfacts`, not
yet checked), and which US universe (survivorship-bias question, same
category as paper #2's).

Paper #2's existing `SmartReversalSimulator` still predates the
interface and has not been adapted to it.

## Real data connected; real Verify/Sample results (2026-09-14, later same day)

**Built `scripts/build_paper01_data.py`** -- fetches Alpaca daily bars
(IEX, split+dividend adjusted) for the S&P 500 universe, aggregates to
monthly, and builds a point-in-time market-cap panel from SEC's
`companyconcept` endpoint (`dei:EntityCommonStockSharesOutstanding`,
selected by `filed` date to avoid look-ahead). 8 unit tests on the pure
aggregation/point-in-time logic (synthetic data, no network), all
passing. Full writeup and all data-source decisions:
`papers/paper-01-ssrn-6630998/reproduce/README.md` and the script's own
module docstring.

**Two real bugs found and fixed while building this -- not assumptions,
actual defects caught by looking at the real output rather than trusting
it:**

1. **CLAUDE.md's "Alpaca free tier goes back to 2016" claim is wrong.**
   Empirically confirmed: `StockBarsRequest` with `feed=DataFeed.IEX`
   returns zero rows for AAPL at 2016/2018/2019/2020-06 start dates; real
   data starts ~2020-07-27. The actual depth is a ~6-year *rolling*
   window back from today, not a fixed calendar year. **Corrected in
   CLAUDE.md** (4 places) and in the data-build script, whose default
   `--start` is now `2020-08-01`, not `2016-01-01`.
2. **`monthly_long_short_returns` was silently turning "no data this
   month" into a fake 0.0% return.** When both the long and short legs
   came back empty (nothing passed the quintile filter), the code fell
   through to `0.0 - 0.0 = 0.0` -- indistinguishable from a real month
   where longs and shorts happened to cancel out. Caught because the
   *first* full run (with the wrong 2016 start date, before fix #1) used
   this fallback to quietly manufacture 33 fake "0% return" months
   out of 106, which is exactly what inflated the sample size and
   dragged statistics toward zero. **Fixed**: both-legs-empty now
   produces `NaN` (excluded from the mean/count), not `0.0`. A single
   leg being empty while the other has real data still falls back to
   0% for that leg only -- a narrower, defensible case, kept as-is.
   Regression tests added: `test_monthly_long_short_returns_missing_month_is_nan_not_zero`,
   `test_monthly_long_short_returns_one_empty_leg_still_counts_other_leg`
   in `papers/paper-01-ssrn-6630998/reproduce/test_portfolio.py`.

**Universe/survivorship decision, made explicitly, not silently:**
today's S&P 500 constituents (Wikipedia, which conveniently includes
each company's CIK) intersected with Alpaca's currently-tradable active
list, applied retroactively across the whole window. **This is
survivorship-biased** -- no free point-in-time historical S&P 500
membership source was found. Stated in full in
`ReproduceResult.assumptions` every time `reproduce_stage` runs (visible
in the run output below), not just in a doc file nobody reads at
run time.

### The real run

```
python -m pipeline.run papers/paper-01-ssrn-6630998
```

Read stage used a manually-authored `read_extraction_auto.json` seeded
from the already-verified `read_notes.md` content (the real Claude-API
Read automation, `pipeline/read_stage.py`, is still unvalidated --
separate open item below, needs `ANTHROPIC_API_KEY`). This is real
published-paper data either way, just not run through the untested
automated extraction path yet -- noted so it isn't conflated with a
validated `read_stage.py` run.

**Reproduce**: 503 S&P 500 tickers (all tradable on Alpaca), 74 months
of data (2020-08 to 2026-09), 73 monthly long-short observations
(2020-09 to 2026-09).

**Real numbers:**

| Metric | Our result | Paper's published US figure |
|---|---|---|
| Mean monthly return | **0.517%** | 0.340% (t=2.12) |
| t-statistic | **0.65** | 2.12 |
| Annualized return | ~6.4% | -- |
| Annualized Sharpe | ~0.27 | 0.32 |
| % positive months | 48.6% | -- |
| Median monthly return | -0.25% | -- |

**`verify_stage` result**: `comparable=True, within_tolerance=True` (our
0.517% vs. paper's 0.340%, within the ±0.20pp tolerance on the mean).

**Honest read of this, not a spin**: the point estimate landing this
close to the paper's published number is genuinely notable. But
`verify_stage`'s tolerance check compares *only the mean* -- it has no
significance test built in, and by that measure alone a result can pass
"within tolerance" that would not survive any real significance test.
Our own t-stat (0.65) is far below the paper's (2.12): **we cannot
reject the null of no effect at any conventional significance level**,
even though the published result could. This is not a clean replication
success. It's much closer to what CLAUDE.md predicted going in --
"expect most papers not to replicate at their published effect size" --
and the fact that the point estimate happens to land near the paper's
while significance collapses is itself the honest finding, not something
to explain away.

The return distribution is also notably right-skewed: median (-0.25%) is
*negative* while the mean (+0.517%) is positive, driven by a small number
of extreme months (best: Feb 2021 +35.6%, Jul 2026 +27.1%; worst: Jun
2026 -11.6%). Checked whether these extreme months are a thin-coverage
artifact (e.g. 2-3 tickers dominating an otherwise-empty portfolio) --
**they are not**: Feb 2021 and Jul 2026 both had 83-88 tickers per leg,
in line with every other month (typical range 84-88). The skew looks
real, not a data-coverage artifact, but has not been investigated
further than that -- open item below.

**Sample result**: `mean_monthly_return_pct=0.517, n_months=72,
pct_positive_months=48.6` -- identical mechanism/data to Reproduce, per
design (Alpaca's window is short enough that there's no older period to
reserve for Reproduce separately from a "current" one for Sample; see
`stage_impl.py`'s `sample_stage` docstring).

### Known gaps in this result, stated plainly

- **`verify_stage`'s tolerance-on-mean-only design doesn't check
  significance.** A t-stat/CI-aware comparison would be a real
  improvement -- currently a design gap, not yet fixed.
- **63/503 tickers lack SEC shares-outstanding data** (dual-class
  companies like GOOGL/GOOG likely report under a different XBRL
  concept; a handful of others, e.g. ABT, hit an observed SEC API
  anomaly -- `"units":{"shares":{}}`, an empty dict instead of a
  populated list, reproducible, not transient). These tickers are
  excluded from value-weighting wherever their market cap is missing --
  handled gracefully (`NaN`, not a crash), not silently included as
  zero.
- **The right-skewed return distribution (Feb 2021, Jul 2026 extreme
  months) hasn't been investigated beyond ruling out thin coverage.**
  Worth a closer look before drawing conclusions from the point estimate.
- **Universe survivorship bias is unresolved** (stated above) -- no free
  point-in-time index-membership source found.
- **Read stage's Claude-API automation (`pipeline/read_stage.py`) is
  still unvalidated against a real API call** -- this run used a
  manually-seeded `read_extraction_auto.json` instead. Needs
  `ANTHROPIC_API_KEY`, still the same open item from earlier.

## Interface now dispatches for real; orchestrator built (2026-09-14, later same day)

Owner's follow-up correctly pointed out that a fixed interface plus a
real paper implementation still isn't automation if nothing connects
them. Fixed:

- `pipeline/interface.py`'s `reproduce_stage`/`verify_stage`/`sample_stage`
  now **dispatch** (via `importlib`, since paper folder names have
  hyphens) to `papers/<paper_slug>/reproduce/stage_impl.py` -- same
  delegation pattern `read_stage` already used. Calling a stage for a
  paper without a `stage_impl.py` (e.g. paper #2, still) raises
  `FileNotFoundError` naming exactly what's missing.
- `pipeline/run.py` -- the orchestrator. One command runs Read ->
  Reproduce -> Verify -> Sample for a paper in sequence:
  `python -m pipeline.run papers/paper-01-ssrn-6630998`. `read_stage`
  now also reuses a cached `read_extraction_auto.json` instead of
  re-calling the (paid) Claude API on every orchestrator run.
- 6 new tests (`pipeline/test_interface.py` rewritten to test dispatch
  instead of stub behavior, `pipeline/test_run.py` new) -- all passing,
  31/31 across the whole repo. Confirmed the CLI (`python -m pipeline.run
  papers/paper-01-ssrn-6630998`, no API key set) correctly reaches and
  stops cleanly at the Read stage, proving the orchestrator really does
  call stages in order rather than short-circuiting.

## Not done / open questions

- **Owner decision (2026-09-14): paper #1 is now the priority.** Paper #2
  is parked with its own open question (point-in-time historical "100
  largest US stocks" membership, without survivorship bias -- no free
  source lined up yet, see `papers/paper-02-groot-huij-zhou-2012/reproduce/README.md`)
  until we come back to it.
- Paper #1: industry classification is resolved (see above). Still open:
  monthly return aggregation from Alpaca, market cap / shares outstanding
  for value-weighting (SEC companyfacts endpoint likely has this, not
  yet checked), and then the actual signal + portfolio construction code.
- pandas/numpy/pytest/requests installed and pinned; PDF text extraction
  uses pypdf (poppler/pdftoppm isn't installed locally, Read tool's
  native PDF rendering doesn't work here -- extract to a .txt file next
  to source.pdf, then read that -- see CLAUDE.md).

## Next step

Paper #1: check SEC companyfacts (or another free source) for shares
outstanding / market cap, then build monthly-return aggregation from
Alpaca daily bars, then the industry-adjusted reversal signal and
quintile portfolio construction itself.
