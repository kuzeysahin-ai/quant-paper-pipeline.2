"""
Reproduce stage: de Groot, Huij & Zhou (2012) "smart" short-term reversal
portfolio construction (Section 4.2 of the paper).

Implements ONLY the strategy mechanics described in
papers/paper-02-groot-huij-zhou-2012/read_notes.md. Deliberately
paper-specific code, not a generalized framework -- see CLAUDE.md's note
on deferring generalization until 3+ papers exist.

NOT included here: which stocks make up the "100 largest" universe over
time, or any real market data. That's the Sample stage's job, and it has
an open survivorship-bias question attached -- see this folder's README.md
before wiring this up to Alpaca data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def past_return(prices: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Trailing `window`-trading-day simple return, per column (ticker),
    as of each row (date). `prices` must be a date-indexed DataFrame of
    (adjusted) close prices, one column per ticker, ascending date order.
    """
    return prices / prices.shift(window) - 1.0


def cross_sectional_percentile_rank(signal_row: pd.Series) -> pd.Series:
    """Percentile rank (0 = lowest signal that day, 1 = highest) across
    tickers with a non-null signal on a single date. Tickers with no
    signal that day (e.g. not yet listed, missing data) stay NaN.
    """
    return signal_row.rank(pct=True, na_option="keep")


def quintile_target_size(universe_size: int, n_groups: int = 5) -> int:
    """Positions per leg. Paper: 100-stock universe / 5 quintiles = 20 per
    leg -- NOT 10 (Quantpedia's page states deciles; the paper doesn't --
    see read_notes.md's Discrepancies table)."""
    return universe_size // n_groups


class SmartReversalSimulator:
    """
    Day-by-day simulation of the paper's "smart" portfolio construction:
    a stock is not exited the moment it leaves the extreme quintile -- it
    is held until it crosses the median rank, then replaced by the most
    extreme eligible stock not already held.

    Two design decisions the paper doesn't fully spell out for the
    "smart" variant specifically, made explicit here rather than silently
    assumed:

    1. Entry ranking uses the signal from `entry_skip_days` sessions
       before the entry date (paper: "we skip one day after each ranking
       before we construct portfolios" -- stated for the standard
       construction in Section 4.1; applied here to entries in the smart
       variant too, for methodological consistency).
    2. The ongoing exit check (has a held stock crossed the median?) uses
       the CURRENT day's rank, unskipped -- the purpose of the skip is to
       avoid bid-ask bounce at entry, not to delay noticing that an
       already-held position has reverted.
    """

    def __init__(
        self,
        prices: pd.DataFrame,
        window: int = 5,
        n_groups: int = 5,
        entry_skip_days: int = 1,
    ):
        self.prices = prices
        self.window = window
        self.n_groups = n_groups
        self.entry_skip_days = entry_skip_days
        self.signal = past_return(prices, window)
        self.ranks = self.signal.apply(cross_sectional_percentile_rank, axis=1)
        self.entry_ranks = self.ranks.shift(entry_skip_days)

    def run(self) -> pd.DataFrame:
        """
        Returns a DataFrame indexed by date with:
          long_return, short_return, long_short_return -- equal-weighted,
            gross (no benchmark subtraction, no trading costs applied)
          n_long, n_short   -- position counts, for sanity checking
          turnover_events   -- number of enter/exit events that day
        """
        dates = self.prices.index
        universe_size = self.prices.shape[1]
        target_n = quintile_target_size(universe_size, self.n_groups)
        daily_returns = self.prices.pct_change()

        long_held: set[str] = set()
        short_held: set[str] = set()
        records = []

        for i, date in enumerate(dates):
            if i == 0:
                records.append(self._empty_record(date))
                continue

            current_rank_row = self.ranks.loc[date]
            entry_rank_row = self.entry_ranks.loc[date]
            ret_row = daily_returns.loc[date]
            turnover_events = 0

            # --- exit check on existing holdings (current-day rank) ---
            for ticker in list(long_held):
                r = current_rank_row.get(ticker, np.nan)
                if pd.isna(r) or r > 0.5:
                    long_held.discard(ticker)
                    turnover_events += 1
            for ticker in list(short_held):
                r = current_rank_row.get(ticker, np.nan)
                if pd.isna(r) or r < 0.5:
                    short_held.discard(ticker)
                    turnover_events += 1

            # --- refill from today's entry-eligible ranking ---
            candidates_long = entry_rank_row.dropna().sort_values(ascending=True)
            for ticker in candidates_long.index:
                if len(long_held) >= target_n:
                    break
                if ticker in long_held or ticker in short_held:
                    continue
                long_held.add(ticker)
                turnover_events += 1

            candidates_short = entry_rank_row.dropna().sort_values(ascending=False)
            for ticker in candidates_short.index:
                if len(short_held) >= target_n:
                    break
                if ticker in short_held or ticker in long_held:
                    continue
                short_held.add(ticker)
                turnover_events += 1

            long_ret = ret_row.reindex(long_held).mean() if long_held else np.nan
            short_ret = ret_row.reindex(short_held).mean() if short_held else np.nan
            ls_ret = (0.0 if pd.isna(long_ret) else long_ret) - (0.0 if pd.isna(short_ret) else short_ret)

            records.append(
                {
                    "date": date,
                    "long_return": long_ret,
                    "short_return": short_ret,
                    "long_short_return": ls_ret,
                    "n_long": len(long_held),
                    "n_short": len(short_held),
                    "turnover_events": turnover_events,
                }
            )

        return pd.DataFrame.from_records(records).set_index("date")

    @staticmethod
    def _empty_record(date):
        return {
            "date": date,
            "long_return": np.nan,
            "short_return": np.nan,
            "long_short_return": np.nan,
            "n_long": 0,
            "n_short": 0,
            "turnover_events": 0,
        }
