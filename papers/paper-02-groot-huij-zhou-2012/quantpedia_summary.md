# Quantpedia summary (secondary source, fetched 2026-09-14)

Raw fetch from https://quantpedia.com/strategies/short-term-reversal-in-stocks
via WebFetch, kept verbatim for the record before being cross-checked against
the primary source. **Do not treat this as verified** -- see
`read_notes.md` for the discrepancies found against the actual paper.

## Strategy Name
Short Term Reversal Effect in Stocks

## Core Description
This strategy exploits the phenomenon where stocks with poor recent performance
generate positive abnormal returns in the following period, while recent
winners earn negative abnormal returns. The key insight is that profitability
requires focusing on large-capitalization stocks to minimize transaction costs
that would otherwise eliminate gains.

## Source Academic Papers
**Primary Source:**
- Authors: Groot, Huij, Zhou
- Title: Another Look at Trading Costs and Short-Term Reversal Profits
- Year: ~2012
- URL: http://papers.ssrn.com/sol3/papers.cfm?abstract_id=1605049

## Exact Methodology (as stated by Quantpedia)
- **Universe:** The 100 largest companies by market capitalization
- **Formation Period:** Previous week AND previous month performance measurement
- **Position Construction:** Long 10 stocks with lowest performance in prior
  week; Short 10 stocks with greatest performance in prior month
- **Rebalancing:** Weekly
- **Weighting:** Equal-weighted (10 positions each side, ~5% per position)

## Performance Statistics (as stated by Quantpedia)
| Metric | Value |
|---|---|
| Annualized Return | 16.25% |
| Sharpe Ratio | 1.09 |
| Estimated Volatility | 14.94% |
| Maximum Drawdown | -52.94% (not explicitly in source paper per Quantpedia) |
| Backtest Period | 1990-2009 |
| Weekly Net Return | 0.29% |
