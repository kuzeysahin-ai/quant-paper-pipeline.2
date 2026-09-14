# quant-paper-pipeline

## What this is

A pipeline that takes an academic quant finance paper and puts it through
four stages: **Read** (extract methodology + claimed results) → **Reproduce**
(rebuild the strategy in code) → **Verify** (compare our result against the
paper's published result) → **Sample** (test on current data — does it
still work?).

This is the local-scale version of the workflow Ken Griffin described at
Citadel (an AI agent compressing 6-8 weeks of PhD research into 2-3 hours),
adapted to what one person with a laptop and a free-tier brokerage account
can actually do.

This repo is **Part 1** of a two-part system. **Part 2** is already live and
separate: a daily automated email (macro news + a narrow energy/shipping
equity watch, 5 sources) — proof the owner can ship an end-to-end agentic
system, not part of this repo's scope.

## Goals, in priority order

1. **Learning.** This is an education project first. Do not take a shortcut
   that produces a plausible-looking result at the cost of the owner
   understanding *why* it works or doesn't.
2. **Modest personal income at our own scale.** Not competing with Citadel —
   see "Our real advantage" below for why that's not a consolation prize.
3. **A demonstrable portfolio.** Every run — success or failure — gets
   recorded honestly. Most student/personal projects only show the wins;
   this one doesn't, and that honesty is itself a differentiator.

## Two AI tools, no live connection between them — read this before assuming context

- **Cowork** (cloud sandbox, separate conversation) — used for research and
  planning. Cannot `pip install`, cannot reach real data APIs (org security
  policy blocks it). Good for reading papers and designing, not for running
  the actual pipeline.
- **This environment** (local Claude Code, on the owner's machine) — real
  `pip install`, real persistent filesystem, real Alpaca API access. This is
  where Reproduce/Verify/Sample actually execute.
- **There is no live bridge between the two.** Whatever isn't written down
  in this repo — in `STATUS.md`, in commit messages, in code comments — does
  not exist as far as the other tool is concerned. Update `STATUS.md` at the
  end of any session that changes state. Read it at the start of any session
  before assuming what's already done.

## Why the constraints are non-negotiable

1. **Backtests lie easily.** Look-ahead bias, survivorship bias, overfitting
   all produce results that look great and mean nothing. The owner has
   already hit this firsthand: run #1 hand-transcribed ~1180 numbers from a
   scraped webpage via WebFetch — slow and error-prone, nowhere near the
   reliability a real API guarantees. Skipping rigor here is exactly how
   that kind of silent error gets baked into the pipeline.
2. **This is an automation system, not a one-off analysis.** A shortcut in
   Read repeats itself in every paper processed afterward — sloppiness in
   one small stage compounds across the whole system. Insist on doing each
   stage right the first time.
3. **The "show people" goal depends entirely on honesty.** Hide a
   constraint or oversell a result and it costs credibility the first time
   someone in quant/finance asks a pointed question (they will). Naming
   constraints openly builds trust; hiding them destroys it retroactively.

## Our real advantages (use them deliberately, don't just note them)

- **Alpaca account** — free tier, 2016+ US equity/ETF daily data via IEX,
  200 req/min, a real API. Replaces the WebFetch-scraping approach
  entirely. Same platform will carry paper-trading and eventually small
  live capital later — one integration, not three.
- **Local Claude Code** — real package installs, a persistent filesystem,
  an environment you can run and re-run and actually test in.
- **Git history** — a written record of what was actually done, instead of
  relying on anyone's memory of it.
- **Small scale is a structural edge for some strategies, not just a
  limitation.** Funds managing billions can't profitably run low-capacity
  strategies (small-cap, low-liquidity) — their own trades move the price.
  We can reach what they structurally can't. This should be an active
  **paper-selection filter**, not an afterthought.
- **Owner's own attention.** This isn't a fire-and-forget system; the owner
  reviews and questions each step. That's a real quality control advantage
  — don't design it away by over-automating review out of the loop.

## Our real constraints (design around these, don't discover them late)

- No institutional data: even Alpaca's free tier doesn't go pre-2016, no
  point-in-time restated fundamentals, no tick data. Some papers (old
  period, high-frequency) are just not testable here — screen for this
  *before* picking a paper, not after sinking time into it.
- Limited compute/scale — can't sweep thousands of variations or broad
  universes the way an institutional fund would.
- No portfolio-level risk management yet — each strategy is tested in
  isolation, no "marginal contribution to existing portfolio" analysis.
  Not important now; will matter once real capital is involved.
- Two disconnected AI tools (see above) — mitigated only by disciplined
  use of this file + STATUS.md. Relax that discipline and things get lost.
- One-person operation, no second reviewer / risk committee. Subtle errors
  are more likely to go unnoticed — the owner has already experienced this
  firsthand with run #1's data-collection method.

## How stage expectations should actually run

- **Read** is harder than it looks — needs real structured extraction +
  verification, not a single-pass summary. Won't be fully correct on the
  first attempt; that's normal, not a failure.
- **Reproduce**: paper-specific code is fine for the first 1-2 papers.
  Don't generalize into shared modules until patterns actually repeat
  across 3+ papers — premature generalization is its own mistake.
- **Verify**: expect most papers *not* to replicate at their published
  effect size. Hou/Xue/Zhang found ~65% of 452 published anomalies lose
  significance under tighter tests. A failed Verify is a real scientific
  finding, not a bug to fix.
- **Sample** is far more reliable now with Alpaca's 2016+ data than the
  prior manual Yahoo-scraping approach — but data is still limited (no
  options, no point-in-time fundamentals, no tick). Let that constraint
  shape paper selection up front, not as a late, painful discovery.

## Paper selection criteria (screen before committing time)

- Testable with daily US equity/ETF data from 2016 onward (Alpaca/IEX).
- No dependency on options data, point-in-time fundamentals, or tick data.
- Bonus, actively sought: capacity-constrained / small-cap / low-liquidity
  edge that institutional-scale funds structurally can't run — this is
  where being small is an advantage, not a handicap.

## Stack

Python (real local installs, no sandbox restriction). Alpaca API for data
now, paper trading and later live execution — same integration throughout.
See `STATUS.md` for current environment/dependency state.
