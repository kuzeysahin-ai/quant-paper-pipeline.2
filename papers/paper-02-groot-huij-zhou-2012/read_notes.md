# Read stage: de Groot, Huij & Zhou (2011/2012)

**Title:** Another Look at Trading Costs and Short-Term Reversal Profits
**Authors:** Wilma de Groot, Joop Huij (Robeco Quantitative Strategies /
Rotterdam School of Management, Erasmus University), Weili Zhou
**Published:** Journal of Banking & Finance 36 (2012), 371-382. DOI:
10.1016/j.jbankfin.2011.07.015
**Source used:** Erasmus University repository, open access, full 46-page
accepted manuscript -- https://repub.eur.nl/pub/25718/AnotherLook_2011.pdf
(SSRN and ScienceDirect both blocked automated access; see STATUS.md)

## Why this paper (link to target #2)

This is the primary source Quantpedia's "Short Term Reversal Effect in
Stocks" page cites. Quantpedia's page is a *secondary* summary -- reading
the actual paper was necessary to check it, not optional. **Result: the
Quantpedia summary does not match the paper's actual methodology.** See
"Discrepancies" below before using Quantpedia's description for anything.

## Central claim

The standard short-term reversal anomaly (loser stocks outperform winner
stocks over the following days/weeks) looks unprofitable net of trading
costs in prior literature (Avramov, Chordia & Goyal 2006) because that
literature evaluates it on a broad universe including small/illiquid
stocks and uses a high-turnover portfolio construction. Restricting the
universe to large-cap stocks, and using a lower-turnover "smart" portfolio
construction rule, this paper finds the strategy remains profitable net of
realistic trading costs.

## Data

- US: 1,500 largest stocks in the Citigroup US Broad Market Index, Jan
  1990 - Dec 2009. Also tested on 500-largest and 100-largest subsets.
- Europe: 1,000 largest stocks in the Citigroup European BMI, Jan 1995 -
  Dec 2009 (600-largest and 100-largest subsets also tested).
- Source: FactSet Global Prices (daily total returns, market cap, volume).
- Deliberately excludes micro-caps to avoid microstructure noise being
  mistaken for the effect.
- **Important: sample ends Dec 2009 -- entirely outside Alpaca's 2016+
  coverage. No period overlap exists for a same-period Verify. See
  "Consequence for our pipeline" below.**

## Methodology -- exactly as tested (not as Quantpedia describes it)

**Signal:** past 5-trading-day (one calendar week) return. Both the long
leg and the short leg use the *same* formation window -- there is no
week-vs-month split between the two legs.

**Two portfolio construction variants, both tested on the same universes:**

1. **"Standard"**: daily sort into quintiles (mutually exclusive, equal
   count) on past-week return. Long the bottom quintile (losers), short
   the top quintile (winners). Skip one day after ranking before entering
   (avoids bid-ask bounce). Equal-weighted within each leg. **Rebalanced
   daily** -- at every rebalance, exit any stock no longer in the extreme
   quintile and replace with whatever newly qualifies.
2. **"Smart"** (the paper's contribution): same ranking and entry, but a
   stock is *not* exited the moment it leaves the extreme quintile --
   it's held until it crosses the **median (50th percentile)**, then
   replaced. Same position count as "standard," but turnover roughly
   halves (677%/week -> 325%/week for the 1,500-stock universe) because
   average holding period extends to ~6 days instead of ~3.

**On a 100-stock universe, a quintile is 20 stocks per leg (20 long / 20
short), not 10 -- this is a direct contradiction of Quantpedia's "10 long
/ 10 short" claim.**

**Trading costs**, modeled two ways (not simulated by us -- see below):
Keim & Madhavan (1997) academic regression model, and a proprietary
Nomura Securities model (spread + volume + trade size + volatility
based), assuming $1M trade size per stock (deflated backward at 10%/year
from a 2009 base).

## Actual results (Tables 4 & 5 -- transcribed directly from the paper, not estimated)

All returns are **per week**, in basis points, long-short portfolio vs.
equal-weighted universe average.

| Universe | Construction | Gross | Net (Keim-Madhavan) | Net (Nomura) | t-stat (Nomura) | Turnover/week |
|---|---|---|---|---|---|---|
| 1,500 largest US | Standard | 61.7 | -66.1 | -103.7 | -14.5 | 677% |
| 1,500 largest US | Smart | 59.8 | -1.5 | -17.6 | -2.6 | 325% |
| 500 largest US | Standard | 71.9 | 66.4 | -3.0 | -0.4 | 688% |
| 500 largest US | Smart | 65.0 | 62.3 | 30.5 | 4.1 | 326% |
| **100 largest US** | Standard | 84.2 | 82.5 | **31.5** | 3.7 | 711% |
| **100 largest US** | **Smart** | 77.9 | 77.1 | **53.1** | 6.4 | 337% |

**The paper's headline "30 to 50 bps/week net of costs" claim refers
specifically to the 500- and 100-largest-stock universes under realistic
(Nomura) trading costs -- the 1,500-stock universe never turns net
positive under either cost model.** Europe (Table 6) shows the same
pattern but weaker: only the 100-largest/smart European portfolio is net
positive (21.6 bps/week); 1,000- and 600-largest are net negative even
with the smart construction.

Subperiod checks (Table 8, not fully transcribed here): the 100-largest
smart result is *stronger* in the most recent decade of their sample
(2000-2009: 59.0 bps/week) than over the full period, and excluding the
dotcom/credit-crisis years doesn't change the conclusion. No sign of the
effect fading within their sample -- but their sample still ends in 2009.

## Discrepancies vs. the Quantpedia summary -- do not use Quantpedia's version uncorrected

| Quantpedia says | Paper actually says |
|---|---|
| Long 10 stocks on prior-**week** return, short 10 stocks on prior-**month** return | Both legs use the same prior-**week** signal |
| 10 long / 10 short (deciles) | 20 long / 20 short on the 100-stock universe (quintiles) |
| Backtest period 1990-2009 | Correct |
| Annualized return 16.25%, Sharpe 1.09 | Roughly consistent with the **standard** (not smart) 100-largest/Nomura-net result (31.5 bps/week -> ~17.6% annualized compounding weekly) -- Quantpedia's number does not match the "smart" variant's 53.1 bps/week (~33% annualized), so Quantpedia appears to be citing the standard construction's return while describing a different (and internally inconsistent, week-vs-month) position rule |

Net: Quantpedia's page is a useful pointer to the paper and roughly right
on the headline magnitude, but its stated *mechanics* are not what the
paper tested. If we build to Quantpedia's description we would not be
reproducing this paper.

## Consequence for our pipeline, this paper

- **Reproduce**: build the "smart," 100-largest-US-stocks variant exactly
  as described above (quintile on prior-week return, exit at median
  crossing, equal-weighted). This is the paper's strongest, most
  economically significant result and the most directly comparable to
  what Quantpedia is pointing at.
- **Verify (as originally scoped -- same-period comparison)**: **not
  possible.** The paper's sample (1990-2009) has zero overlap with
  Alpaca's free-tier coverage (2016+). We cannot compare our result to
  their published number on the same data.
- **What we can do instead**: skip straight to **Sample** -- run the same
  strategy logic on 2016+ data and see whether the effect is present at
  all in the modern, more-liquid, more-efficient market. A weakened or
  absent effect here would not contradict the paper (markets could have
  become more efficient since 2009, or the effect could still be real but
  smaller) but a *strong* modern effect would be a meaningful, honestly
  earned finding.
- **Trading costs**: we won't have Nomura's proprietary model. We can
  either report gross returns transparently as gross, or approximate net
  returns with a simple flat cost-per-trade assumption clearly labeled as
  an approximation, not a replication of their cost model.
