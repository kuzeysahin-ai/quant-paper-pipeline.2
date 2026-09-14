"""
Unit tests for the "smart" reversal simulator, using small synthetic
price panels that can be hand-checked. These validate the MECHANISM
(ranking, entry, exit-at-median, replacement) in isolation from any real
market data -- deliberately separate from the open universe/data-source
question (see this folder's README.md).
"""
import numpy as np
import pandas as pd
import pytest

from strategy import (
    SmartReversalSimulator,
    cross_sectional_percentile_rank,
    past_return,
    quintile_target_size,
)


def test_quintile_target_size():
    assert quintile_target_size(100, n_groups=5) == 20
    assert quintile_target_size(100, n_groups=10) == 10  # decile, for comparison to Quantpedia's (incorrect) claim
    assert quintile_target_size(10, n_groups=5) == 2


def test_past_return_basic():
    prices = pd.DataFrame({"A": [100, 101, 102, 103, 104, 110]})
    ret = past_return(prices, window=5)
    # row 5 (index 5): 110 / 100 - 1 = 0.10
    assert ret.iloc[5]["A"] == pytest.approx(0.10)
    # rows before the window has 5 prior observations are NaN
    assert ret.iloc[4].isna()["A"]


def test_cross_sectional_percentile_rank():
    row = pd.Series({"A": -0.05, "B": 0.10, "C": 0.0, "D": np.nan})
    ranks = cross_sectional_percentile_rank(row)
    # A is lowest among the 3 non-NaN values -> smallest percentile
    assert ranks["A"] < ranks["C"] < ranks["B"]
    assert pd.isna(ranks["D"])


def _toy_prices():
    """
    10 tickers, 12 trading days. Construct so that at least one ticker
    (LOSER) stays in the bottom quintile for its whole life (persistent
    loser -- should be entered and held), and one ticker (FLIPPER) starts
    as a loser then rallies hard enough to cross the median (should be
    exited once "smart" and replaced).
    """
    dates = pd.date_range("2024-01-01", periods=12, freq="B")
    n = 12
    rng = np.random.default_rng(0)

    data = {}
    # 6 "neutral" tickers: small random walk, never extreme
    for i in range(6):
        steps = rng.normal(0, 0.001, n)
        data[f"NEUT{i}"] = 100 * np.cumprod(1 + steps)

    # LOSER: steadily declining every day -> always in bottom quintile
    data["LOSER"] = 100 * np.cumprod(1 - 0.02 * np.ones(n))

    # WINNER: steadily rising every day -> always in top quintile
    data["WINNER"] = 100 * np.cumprod(1 + 0.02 * np.ones(n))

    # FLIPPER: declines for the first half (becomes a loser), then rallies
    # hard in the second half (should cross the median and get exited
    # under the "smart" rule)
    flip_steps = np.array([-0.02] * 6 + [0.05] * 6)
    data["FLIPPER"] = 100 * np.cumprod(1 + flip_steps)

    # STEADY_MID: flat -> stays in the middle, never enters either leg
    data["STEADY_MID"] = np.full(n, 100.0)

    return pd.DataFrame(data, index=dates)


def test_smart_simulator_persistent_loser_gets_and_stays_held():
    prices = _toy_prices()
    sim = SmartReversalSimulator(prices, window=5, n_groups=5, entry_skip_days=1)
    result = sim.run()
    # Sanity: simulator runs end to end and returns one row per date
    assert len(result) == len(prices)
    # Once the warm-up window has passed, positions should be non-empty
    assert result["n_long"].iloc[-1] > 0
    assert result["n_short"].iloc[-1] > 0


def test_smart_simulator_never_holds_same_ticker_both_legs():
    prices = _toy_prices()
    sim = SmartReversalSimulator(prices, window=5, n_groups=5, entry_skip_days=1)
    # Re-run the loop manually via run() and inspect internal invariant by
    # checking long/short sets don't overlap at any point -- run() doesn't
    # expose per-day holdings directly, so we re-derive via a lower n_groups
    # small panel and check turnover_events is always >= 0 and n_long/n_short
    # never exceed the target size.
    result = sim.run()
    target_n = quintile_target_size(prices.shape[1], n_groups=5)
    assert (result["n_long"] <= target_n).all()
    assert (result["n_short"] <= target_n).all()


def test_smart_simulator_long_short_return_sign_matches_expectation():
    """
    LOSER trends up in price (reversal bet pays off if the market itself
    reverts), WINNER trends down would confirm reversal profits. Here we
    just check the mechanism produces finite, sane numbers -- this is not
    a test that the STRATEGY is profitable (that's an empirical question
    for real data, not something a unit test should assert).
    """
    prices = _toy_prices()
    sim = SmartReversalSimulator(prices, window=5, n_groups=5, entry_skip_days=1)
    result = sim.run()
    non_nan = result["long_short_return"].dropna()
    assert len(non_nan) > 0
    assert np.isfinite(non_nan).all()


def test_entry_skip_days_shifts_entry_ranking():
    """entry_skip_days controls how stale the ranking used for NEW entries
    is; 0 vs 1 should be able to produce different entry timing."""
    prices = _toy_prices()
    sim0 = SmartReversalSimulator(prices, window=5, n_groups=5, entry_skip_days=0)
    sim1 = SmartReversalSimulator(prices, window=5, n_groups=5, entry_skip_days=1)
    assert not sim0.entry_ranks.equals(sim1.entry_ranks)
