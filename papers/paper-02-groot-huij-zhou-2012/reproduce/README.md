# Reproduce stage: paper #2

## What's here

`strategy.py` -- the "smart" reversal portfolio construction mechanism
(Section 4.2 of the paper): percentile-rank signal, entry into the
extreme quintile, hold until the position crosses the median rank, then
replace. Paper-specific code, not a generalized framework (per CLAUDE.md).

`test_strategy.py` -- 7 unit tests on small synthetic price panels,
validating the mechanism in isolation: ranking correctness, entry sizing
(quintile = universe/5, confirmed 20 not 10 -- see read_notes.md),
persistent losers get held, the exit-at-median rule fires, no ticker is
ever held long and short simultaneously, entry_skip_days actually shifts
the entry ranking. **All 7 pass.**

Run tests:
```bash
cd papers/paper-02-groot-huij-zhou-2012/reproduce
../../../.venv/Scripts/python.exe -m pytest -v
```

## What's deliberately NOT here yet -- open before this touches real data

**Universe selection / survivorship bias.** The paper tests the "100
largest US stocks" *as constituents changed over 1990-2009*. We don't
have point-in-time historical index membership from Alpaca (or any free
source lined up yet). The tempting shortcut -- take today's 100 largest
US stocks and apply them retroactively to a multi-year backtest -- is
exactly the kind of look-ahead/survivorship bias CLAUDE.md calls out as
the thing that makes backtests "look great and mean nothing." Options to
resolve before Sample stage runs on real data:

1. Use a very recent, short window (e.g. trailing ~1-2 years) where
   today's largest-100 list is a reasonable approximation of the
   historical list too -- shrinks the bias but doesn't eliminate it, and
   gives less statistical power.
2. Find a free point-in-time historical constituents source (index
   provider data is usually paywalled; may not exist for free).
3. Proceed with today's-universe-applied-retroactively, but report the
   survivorship bias risk explicitly alongside any result -- honest
   about the limitation rather than silently absorbing it into the
   number. Consistent with CLAUDE.md's "show failures too" principle,
   but weaker evidence than options 1 or 2.

**Not decided yet -- needs the owner's input before Sample stage starts.**

**Trading costs.** The paper's net-of-cost numbers use a proprietary
Nomura Securities model we don't have. Options: report gross returns
plainly labeled as gross, or apply a simple flat cost-per-trade
approximation labeled as an approximation. Not yet built.
