"""
Quintile, value-weighted long-short portfolio construction, per Stosik &
Zaremba (2026): long the bottom quintile of the signal (strongest
relative underperformers), short the top quintile (strongest relative
outperformers), value-weighted within each leg, monthly rebalance.
Headline/Table 1-3 results in the paper use value-weighting -- see
read_notes.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def quintile_long_short_tickers(
    signal: pd.Series, market_cap: pd.Series, n_groups: int = 5
) -> tuple[set[str], set[str]]:
    """
    One month's signal + market cap (aligned by ticker) -> (long, short)
    ticker sets. Long = bottom quintile of signal (worst relative
    performers), short = top quintile (best relative performers).
    Tickers missing a signal or a market cap value are excluded from
    ranking entirely -- not just from weighting.
    """
    valid = signal.dropna().index.intersection(market_cap.dropna().index)
    s = signal.loc[valid]
    if len(s) < n_groups:
        return set(), set()

    ranks = s.rank(pct=True)
    long_tickers = set(ranks[ranks <= 1 / n_groups].index)
    short_tickers = set(ranks[ranks > (n_groups - 1) / n_groups].index)
    return long_tickers, short_tickers


def value_weighted_return(
    tickers: set[str], period_returns: pd.Series, market_cap: pd.Series
) -> float:
    """
    Value-weighted return of `tickers` over `period_returns`, weighted by
    `market_cap` (as of formation, i.e. the month the tickers were
    selected -- not the realization month). NaN if no ticker in the set
    has both a return and a market cap for this period.
    """
    usable = [
        t
        for t in tickers
        if t in period_returns.index
        and pd.notna(period_returns[t])
        and t in market_cap.index
        and pd.notna(market_cap[t])
    ]
    if not usable:
        return float("nan")

    weights = market_cap.loc[usable]
    weights = weights / weights.sum()
    return float((weights * period_returns.loc[usable]).sum())


def monthly_long_short_returns(
    signal: pd.DataFrame, returns: pd.DataFrame, market_cap: pd.DataFrame, n_groups: int = 5
) -> pd.DataFrame:
    """
    Full backtest loop: for each formation month t (all but the last),
    select long/short tickers from signal.loc[t] + market_cap.loc[t],
    then realize the return over month t+1 (returns.loc[t+1]) -- i.e.
    signal and portfolio weights are both formed on data known at the
    start of the holding month, never using the holding month's own
    return.

    Returns a DataFrame indexed by the HOLDING month (t+1), with columns
    long_return, short_return, long_short_return, n_long, n_short.
    """
    dates = signal.index
    records = []
    for i in range(len(dates) - 1):
        t, t_next = dates[i], dates[i + 1]

        long_tickers, short_tickers = quintile_long_short_tickers(
            signal.loc[t], market_cap.loc[t], n_groups=n_groups
        )

        if not long_tickers and not short_tickers:
            # No usable data at all this formation month (e.g. a data
            # source gap) -- this is a MISSING observation, not a real
            # "long and short cancelled out to zero" data point. Recording
            # it as 0.0 would silently inflate the sample size and pull
            # the mean/hit-rate toward zero with fake flat months. Found
            # via a real bug: an Alpaca data-coverage gap (see
            # scripts/build_paper01_data.py's module docstring) produced
            # 33 months like this in an early run, before this fix.
            long_ret = short_ret = ls_ret = float("nan")
        else:
            long_ret = value_weighted_return(long_tickers, returns.loc[t_next], market_cap.loc[t])
            short_ret = value_weighted_return(short_tickers, returns.loc[t_next], market_cap.loc[t])
            # One leg (not both) coming back empty/NaN here is a narrower,
            # more defensible case -- e.g. every ticker selected into one
            # leg happens to be missing its realization-month return --
            # and is still treated as a 0% contribution from that leg
            # while the other leg's real return still counts.
            ls_ret = (0.0 if pd.isna(long_ret) else long_ret) - (
                0.0 if pd.isna(short_ret) else short_ret
            )

        records.append(
            {
                "date": t_next,
                "long_return": long_ret,
                "short_return": short_ret,
                "long_short_return": ls_ret,
                "n_long": len(long_tickers),
                "n_short": len(short_tickers),
            }
        )

    return pd.DataFrame.from_records(records).set_index("date")
