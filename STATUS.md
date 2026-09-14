# STATUS

The single source of truth bridging Cowork (planning) and local Claude Code
(execution) — see CLAUDE.md for why this matters. Update this at the end of
any session that changes state. Read it first, before assuming what's done.

## Current phase

**Read stage in progress.** Two papers targeted, one blocked, one done.

- **Paper #1**: Stosik & Zaremba (2026), "Short-Term Reversal Persists
  Globally -- If Properly Measured," SSRN 6630998 / Economics Letters.
  **BLOCKED**: SSRN returns 403 to all automated fetch attempts
  (Cloudflare bot challenge) -- confirmed this blocks the whole domain,
  not just this paper. ScienceDirect (the journal) also 403s. No open
  mirror found (checked Zaremba's personal site, ResearchGate, Google
  Scholar results -- all point back to SSRN/ScienceDirect). **Needs the
  owner to manually download via their own browser** and place the PDF at
  `papers/paper-01-ssrn-6630998/source.pdf`.
- **Paper #2**: de Groot, Huij & Zhou (2012), "Another Look at Trading
  Costs and Short-Term Reversal Profits," JBF 36:371-382 -- the primary
  source behind Quantpedia's "Short Term Reversal Effect in Stocks" page
  (the owner's second target). **Read complete** -- full text obtained
  from the Erasmus University open repository (SSRN mirror also blocked
  for this one). Full write-up: `papers/paper-02-groot-huij-zhou-2012/read_notes.md`.
  **Important finding**: Quantpedia's methodology description does not
  match the actual paper (wrong formation-period rule, wrong position
  count) -- see that file's "Discrepancies" section before building
  anything off the Quantpedia page alone.
  **Structural limitation discovered**: paper's sample ends Dec 2009,
  zero overlap with Alpaca's 2016+ coverage -- a same-period Verify
  against the published numbers is not possible for this paper. Plan is
  Read -> Reproduce -> Sample (skip formal Verify), per the read_notes.

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

- Paper #1 PDF still needed from owner (SSRN blocked, see above).
- Repro/Verify/Sample code structure not designed yet -- per CLAUDE.md,
  deliberately deferring generalization until 3+ papers are done; first
  paper's code will be paper-specific.
- Owner hasn't yet said whether to proceed with Reproduce on paper #2
  now, or wait until paper #1's PDF is in hand and read both before
  writing any code.

## Next step

Waiting on: (1) owner's decision on whether to start Reproduce for paper
#2 now vs. wait for paper #1, (2) paper #1's PDF (manual download,
SSRN blocked for automated access -- add to CLAUDE.md as a known
constraint: assume SSRN links will need manual retrieval going forward).
