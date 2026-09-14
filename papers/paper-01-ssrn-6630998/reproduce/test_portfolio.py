import numpy as np
import pandas as pd
import pytest

from portfolio import monthly_long_short_returns, quintile_long_short_tickers, value_weighted_return


def test_quintile_long_short_tickers_bottom_and_top():
    # 10 tickers -> quintile = 2 per leg
    signal = pd.Series({f"T{i}": i for i in range(10)})  # T0=0 (worst) ... T9=9 (best)
    market_cap = pd.Series({f"T{i}": 1.0 for i in range(10)})
    long_t, short_t = quintile_long_short_tickers(signal, market_cap, n_groups=5)
    assert long_t == {"T0", "T1"}
    assert short_t == {"T8", "T9"}


def test_quintile_excludes_missing_market_cap():
    signal = pd.Series({"A": 0, "B": 1, "C": 2, "D": 3, "E": 4})
    market_cap = pd.Series({"A": 1.0, "C": 1.0, "D": 1.0, "E": 1.0})  # B missing
    long_t, short_t = quintile_long_short_tickers(signal, market_cap, n_groups=5)
    assert "B" not in long_t | short_t


def test_value_weighted_return_basic():
    tickers = {"A", "B"}
    returns = pd.Series({"A": 0.10, "B": 0.20})
    market_cap = pd.Series({"A": 100.0, "B": 300.0})
    # weights: A=0.25, B=0.75 -> 0.25*0.10 + 0.75*0.20 = 0.175
    assert value_weighted_return(tickers, returns, market_cap) == pytest.approx(0.175)


def test_value_weighted_return_nan_when_nothing_usable():
    assert pd.isna(value_weighted_return({"X"}, pd.Series({"Y": 0.1}), pd.Series({"Y": 1.0})))


def test_monthly_long_short_returns_end_to_end_persistent_loser_and_winner():
    dates = pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"])
    # 10 tickers, strictly distinct signal values every month (T0 lowest
    # .. T9 highest) so ranking is unambiguous -- with 8 tied at the same
    # value, pandas' average-rank tie-breaking pushes them all to the
    # same percentile and none land cleanly in either quintile.
    row = {f"T{i}": float(i) for i in range(10)}
    signal = pd.DataFrame([row, row, row], index=dates)
    returns = signal.copy()  # reuse shape; values don't need to match signal
    market_cap = pd.DataFrame(1.0, index=dates, columns=signal.columns)

    result = monthly_long_short_returns(signal, returns, market_cap, n_groups=5)

    assert list(result.index) == list(dates[1:])
    assert (result["n_long"] == 2).all()
    assert (result["n_short"] == 2).all()


def test_monthly_long_short_returns_missing_month_is_nan_not_zero():
    """A formation month with no usable signal/market-cap data at all
    (both legs empty) must produce a NaN observation, not a fake 0.0%
    return -- recording 0.0 would silently inflate the sample size and
    pull the mean/hit-rate toward zero. Caught via a real bug: an Alpaca
    data-coverage gap produced 33 months like this before this fix (see
    STATUS.md)."""
    dates = pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"])
    # Only 3 tickers total -- always below n_groups=5, so every month's
    # quintile selection is empty regardless of data.
    signal = pd.DataFrame({"A": [1.0, 2.0, 3.0], "B": [2.0, 3.0, 4.0], "C": [3.0, 4.0, 5.0]}, index=dates)
    returns = signal.copy()
    market_cap = pd.DataFrame(1.0, index=dates, columns=signal.columns)

    result = monthly_long_short_returns(signal, returns, market_cap, n_groups=5)

    assert (result["n_long"] == 0).all()
    assert (result["n_short"] == 0).all()
    assert result["long_short_return"].isna().all()
    assert result["long_return"].isna().all()
    assert result["short_return"].isna().all()


def test_monthly_long_short_returns_one_empty_leg_still_counts_other_leg():
    """Distinct from the both-empty case: if the long leg's tickers were
    selected fine but their realization-month RETURN is missing while
    the short leg's is not, the long leg contributes 0% (not NaN) while
    the short leg's real return still counts -- this is the narrower,
    still-valid use of the old zero-fill behavior."""
    dates = pd.to_datetime(["2020-01-31", "2020-02-29"])
    signal = pd.DataFrame({f"T{i}": [float(i), float(i)] for i in range(10)}, index=dates)
    returns = signal.copy()
    market_cap = pd.DataFrame(1.0, index=dates, columns=signal.columns)
    # Selected fine at formation (dates[0], fully valid); missing only
    # their REALIZATION-month (dates[1]) return.
    returns.loc[dates[1], ["T0", "T1"]] = np.nan

    result = monthly_long_short_returns(signal, returns, market_cap, n_groups=5)
    row = result.loc[dates[1]]
    assert row["n_long"] == 2  # still selected -- missing data is about realization, not selection
    assert pd.isna(row["long_return"])  # no usable realized return for either long ticker
    assert not pd.isna(row["short_return"])  # short leg (T8,T9) has real data
    assert row["long_short_return"] == pytest.approx(0.0 - row["short_return"])
