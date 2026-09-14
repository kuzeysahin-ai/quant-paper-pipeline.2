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
  **Blocker before Reproduce**: needs industry classification data
  (GICS/SIC or similar) for US stocks -- Alpaca doesn't provide this,
  no source lined up yet. Same category of open question as paper #2's
  universe problem below.
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

## Not done / open questions

- **Two open data-source questions block real Reproduce/Sample work on
  both papers, and they're the same category of problem:**
  1. Paper #2: point-in-time historical "100 largest US stocks"
     membership, without survivorship bias. No free source lined up.
  2. Paper #1: industry classification (GICS/SIC) for US stocks. No
     free source lined up. Alpaca provides neither.
  Both need to be resolved -- or a documented, honest simplification
  chosen -- before either paper can move past mechanism-only code.
- pandas/numpy/pytest installed and pinned; PDF text extraction now uses
  pypdf (poppler/pdftoppm isn't installed locally, Read tool's native PDF
  rendering doesn't work here -- worth remembering for future papers:
  extract to a .txt file next to source.pdf, then read that).

## Next step

Resolve the two data-source questions above (owner input likely needed --
neither has an obvious free answer yet). Once at least one is resolved,
finish wiring that paper's Reproduce stage to real Alpaca/other data and
move to Sample.
