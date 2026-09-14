"""
Industry-adjusted reversal signal, per Stosik & Zaremba (2026), eq. (1)
(see ../read_notes.md):

    REV_IN_{i,t} = R_{i,t} - mean(R_{j,t} for j in industry(i), j != i)

i.e. a stock's return in a given month minus the *leave-one-out* mean
return of its industry peers that same month (the paper says "peers,"
which this reads as excluding the stock itself -- not explicit in the
paper, so recorded as an assumption in ReproduceResult.assumptions
rather than silently baked in).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def leave_one_out_industry_mean(returns_row: pd.Series, industry_map: pd.Series) -> pd.Series:
    """
    For a single month's cross-section of returns, each ticker's industry
    peer mean EXCLUDING itself. Tickers with no return, no industry
    label, or as the sole member of their industry that month get NaN.
    """
    df = pd.DataFrame({"ret": returns_row, "industry": industry_map})
    df = df.dropna(subset=["ret", "industry"])

    industry_sum = df.groupby("industry")["ret"].transform("sum")
    industry_n = df.groupby("industry")["ret"].transform("count")
    with np.errstate(invalid="ignore", divide="ignore"):
        loo_mean = (industry_sum - df["ret"]) / (industry_n - 1)
    loo_mean = loo_mean.where(industry_n > 1)  # no peers -> NaN, not 0

    return loo_mean.reindex(returns_row.index)


def industry_adjusted_reversal_signal(returns: pd.DataFrame, industry_map: pd.Series) -> pd.DataFrame:
    """
    `returns`: monthly returns, date-indexed, one column per ticker.
    `industry_map`: ticker -> industry label (e.g. FF12 group), static
    for the whole panel -- a simplification worth flagging (a stock's
    actual industry can change over a multi-year sample; not modeled).

    Returns a same-shaped DataFrame of REV_IN values, one row per month.
    """
    peer_means = returns.apply(
        lambda row: leave_one_out_industry_mean(row, industry_map), axis=1
    )
    return returns - peer_means
