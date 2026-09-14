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
