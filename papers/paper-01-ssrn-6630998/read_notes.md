# Read stage: Stosik & Zaremba (2026)

**Title:** Short-Term Reversal Persists Globally -- If Properly Measured
**Authors:** Jan Stosik (Poznań University of Economics and Business), Adam
Zaremba (Montpellier Business School / Poznań University / Monash)
**Version read:** April 22, 2026 SSRN working-paper PDF, supplied directly
by the owner (SSRN blocked automated access -- see STATUS.md)
**Source file:** `papers/paper-01-ssrn-6630998/source.pdf` (16 pages,
Economics Letters format, tables fully present as text -- no placeholder
issue this time)

## Central claim

Short-term reversal looks like it has weakened or vanished in modern,
liquid markets (cited: McLean & Pontiff 2016; Chordia et al. 2014; Chen &
Velikov 2023) -- but that's a measurement artifact, not real decay. Raw
past-return reversal signals mix a firm-specific component (which
reverses) with an industry-wide component (which persists/trends). These
two effects partly cancel out in the raw signal. Strip out the industry
component and the reversal effect is still large and significant.

## Data

- Monthly stock-level panel, **64 countries, Jan 1990 - Dec 2023**.
- US: CRSP. International: Compustat. All returns expressed in USD.
- Filters: common stocks on main exchanges only; excludes missing
  returns, price ≤ $1, missing industry code, nano-caps; requires ≥10
  stocks per country-month.
- Sample size: 7,206-21,698 stocks/month, avg 14,193, 5,790,595 total
  stock-month observations.
- **Sample extends to Dec 2023 -- this overlaps Alpaca's 2016+ coverage**
  (unlike paper #2, whose sample stops in 2009). A same-period Verify is
  at least theoretically possible here, though only for the 2016-2023
  tail of their "second subperiod" (2007-2023), not their full window.

## Methodology -- three signals, same portfolio mechanics

All three signals are computed **monthly**, within each country
separately, then sorted into **quintiles**. Long the bottom quintile
(worst relative performers), short the top quintile. Both equal- and
value-weighted portfolio variants are computed; **headline/Table 1-3
results use value-weighted**.

1. **Standard reversal**: raw prior-month return, `R_i,t-1`. (The
   classic Jegadeesh 1990 / Lehmann 1990 signal -- monthly frequency, not
   weekly like paper #2.)
2. **Industry-adjusted reversal**: `REV_IN = R_i,t-1 - mean(R_j,t-1)`,
   i.e. a stock's prior-month return minus its industry peers' average
   prior-month return. **This is the paper's main proposed fix and its
   strongest result.**
3. **Regret-based**: `REG = R_i,t-1 - max(R_k,t-1 for k in industry j)`,
   deviation from the *best* performer in the industry (from Arisoy et
   al. 2024). Tested as a comparison, not the primary signal.

No formation/holding-period subtlety like paper #2's "smart" construction
-- this is a plain monthly rebalance, quintile sort, hold one month.
Simpler mechanically; the sophistication here is entirely in the *signal
definition* (industry adjustment), not the portfolio construction rule.

## Actual results (Tables 1-3, transcribed from the paper)

**Global pooled, value-weighted, full sample (Table 1):**

| Signal | R (%/mo) | t-stat | Sharpe | 6-factor α (%/mo) | t-stat |
|---|---|---|---|---|---|
| Standard reversal | 0.05 | 0.24 | 0.04 | 0.18 | 0.66 |
| Industry-adjusted | 0.53 | 5.02 | 0.74 | 0.60 | 4.14 |
| Regret-based (Table 3) | 0.40 | -- | -- | 0.39 | -- |

**23 of 64 markets significant (industry-adjusted) vs. 13 of 64
(standard).**

**United States specifically (the only part we can realistically test):**

| Signal | R (%/mo) | t-stat | Sharpe | α (%/mo) | t-stat |
|---|---|---|---|---|---|
| Standard reversal | -0.01 | -0.05 | -0.01 | 0.06 | 0.29 |
| Industry-adjusted | 0.34 | 2.12 | 0.32 | 0.30 | 1.87 |
| Regret-based | 0.27 | 1.38 | 0.24 | spanning α 0.15 (t=0.63) vs industry-adj. |

**US industry-adjusted reversal is statistically significant on its own
(t=2.12) but the alpha after risk-adjustment is borderline (t=1.87) --
weaker than the pooled global result.** This matters: the effect we'd
actually be testing (US-only, since that's what Alpaca covers) is the
paper's *weakest* major-market result, not its strongest. UK (t=5.37) and
Japan (t=4.63) are far stronger but out of reach with a US-equities data
source.

**Subperiods (global pooled, not US-specific -- Table 2):**

| Period | Industry-adj. R | t-stat | Standard R | t-stat |
|---|---|---|---|---|
| 1990-2006 | 0.67 | 3.92 | 0.15 | 0.46 |
| 2007-2023 | 0.40 | 3.15 | -0.05 | -0.18 |

Effect weakens over time but stays significant in the recent subperiod
(global pooled). No US-only subperiod breakdown is reported in the main
tables -- we only know the US full-sample (1990-2023) number.

**Regret vs. industry-adjusted (Table 3, spanning regression):** regret's
alpha shrinks from 0.39% to a spanning intercept of 0.25% (t=1.34,
pooled) once industry-adjusted reversal is controlled for -- i.e. regret
doesn't add independent information globally. For the US specifically:
regret spanning α = 0.15% (t=0.63, insignificant) with β on
industry-adjusted reversal = 0.34 (t=4.56, R²=0.10) -- consistent with
the global conclusion. **We don't need to build the regret signal
separately; it's subsumed by industry-adjusted reversal.**

## Consequence for our pipeline, this paper

- **Reproduce target**: industry-adjusted reversal (signal #2), US
  equities only, value-weighted quintiles, monthly rebalance. This is the
  paper's main claim, testable (in principle) with data we can get, and
  we can skip the regret signal per the spanning-regression finding above.
- **Blocking issue before Reproduce can start for real: industry
  classification data.** The signal requires grouping stocks by industry
  each month to compute peer-relative returns. Alpaca is a market
  data/brokerage API -- it does not provide GICS/SIC industry
  classifications. This needs a separate data source (free options to
  investigate: sector/industry fields on index-provider sites, static
  SIC codes, or a coarse sector proxy via sector ETF membership) before
  any code gets written. **This is the same category of problem as
  paper #2's survivorship-bias/universe question -- an open design
  decision, not something to quietly work around.**
- **Verify**: partially possible, unlike paper #2. Alpaca's 2016+ window
  falls entirely inside the paper's "second subperiod" (2007-2023,
  industry-adjusted global R=0.40%/mo, t=3.15) but we only have the US
  full-sample number (0.34%/mo, t=2.12) to compare against, not a
  matching US-only, 2016-2023-only figure. Any comparison we make will be
  approximate by construction -- worth stating plainly rather than
  implying a precise match is possible.
- **Universe**: paper uses the full investable US common-stock universe
  (CRSP-based, no cap-size restriction beyond excluding nano-caps).
  Alpaca's free tier covers all listed US equities, not just large-caps
  -- this is actually a better universe match than paper #2's
  100-largest-only test, though liquidity/tradability of the smallest
  names is its own concern for a real strategy (academic paper doesn't
  need to worry about execution; we would).
